"""Exception-raising wrappers around the OWNd 0.7.48 session classes (Contract B).

OWNd's sessions never raise: ``connect()`` returns ``None`` after five refused
attempts or ``{"Success": False, ...}`` on a negotiation/password error, and
``send()`` / ``get_next()`` swallow every exception and return ``None``.  The
gateway handler therefore could not tell "the gateway is rebooting" from "a frame
arrived" (audit gw-01, gw-02, gw-04, gw-05, gw-13, gw-16).

The classes below subclass ``OWNSession`` so the negotiation / password code stays
OWNd's (the package is pinned and untouched) but:

- :meth:`OWNChannel.open` makes ONE connection attempt under a timeout, verifies the
  negotiation result, enables TCP keepalive on the socket and raises
  :class:`AuthenticationError` / :class:`SessionError` / ``OSError`` /
  ``TimeoutError`` on failure.  Retry and backoff belong to the caller.
- :meth:`OWNChannel.read_frame` (and ``get_next``) raise on every transport failure;
  only frames the OWNd parser cannot understand come back as their raw text.
- :meth:`OWNCommandChannel.send_command` writes one command and reads EVERY reply
  frame until the gateway's ACK/NACK (under a timeout), so multi-frame status and
  energy replies never desynchronise the session and reach the caller.
- :meth:`OWNChannel.close` never raises and is safe before ``open()`` and twice.
"""

from __future__ import annotations

import asyncio
import logging
import socket
from dataclasses import dataclass, field

from OWNd.connection import OWNGateway, OWNSession
from OWNd.message import OWNMessage, OWNSignaling

# OWNd ``_negotiate()`` messages that mean "the password is wrong or missing".
AUTH_FAILURE_MESSAGES: tuple[str, ...] = ("password_error", "password_required", "password_retry")

# TCP keepalive tuning (seconds / probes): a dead peer is detected after
# KEEPALIVE_IDLE + KEEPALIVE_INTERVAL * KEEPALIVE_COUNT = 60 s instead of the
# kernel default of ~2 hours.
KEEPALIVE_IDLE_SEC = 30
KEEPALIVE_INTERVAL_SEC = 10
KEEPALIVE_COUNT = 3


class SessionError(ConnectionError):
    """The OpenWebNet session is broken or could not be established."""


class AuthenticationError(SessionError):
    """The gateway rejected the password (or requires one)."""

    def __init__(self, reason: str) -> None:
        super().__init__(f"authentication failed ({reason})")
        self.reason = reason


@dataclass(slots=True)
class CommandResult:
    """Outcome of one command sent on a command session."""

    acknowledged: bool
    replies: list[OWNMessage] = field(default_factory=list)


def enable_tcp_keepalive(
    writer: asyncio.StreamWriter,
    idle: int = KEEPALIVE_IDLE_SEC,
    interval: int = KEEPALIVE_INTERVAL_SEC,
    count: int = KEEPALIVE_COUNT,
) -> bool:
    """Enable TCP keepalive on the writer's socket; return True when it was set.

    ``TCP_KEEPIDLE`` exists on Linux (HAOS), macOS spells it ``TCP_KEEPALIVE``;
    every option is applied only where the platform provides it.
    """
    sock = writer.get_extra_info("socket")
    if sock is None:
        return False
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        idle_option = getattr(socket, "TCP_KEEPIDLE", None) or getattr(socket, "TCP_KEEPALIVE", None)
        if idle_option is not None:
            sock.setsockopt(socket.IPPROTO_TCP, idle_option, idle)
        if hasattr(socket, "TCP_KEEPINTVL"):
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, interval)
        if hasattr(socket, "TCP_KEEPCNT"):
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, count)
    except OSError:
        return False
    return True


def parse_frame(text: str, logger: logging.Logger, log_id: str) -> OWNMessage | str:
    """Parse one raw frame; return the raw text when OWNd cannot parse it.

    ``OWNMessage.parse`` returns ``None`` or the raw string for unknown frames and
    can even raise (``IndexError`` on a short WHO=13 frame or a CEN+ frame without
    ``#n`` - verified on OWNd 0.7.48).  None of that is a transport failure.
    """
    try:
        parsed = OWNMessage.parse(text)
    except Exception as err:  # noqa: BLE001 - OWNd parser bug on a malformed frame
        logger.debug("%s OWNd could not parse frame `%s`: %s", log_id, text, err)
        return text
    return parsed if isinstance(parsed, OWNMessage) else text


class OWNChannel(OWNSession):
    """One authenticated OpenWebNet session (event or command) with honest errors."""

    def __init__(self, gateway: OWNGateway, connection_type: str, logger: logging.Logger) -> None:
        super().__init__(gateway=gateway, connection_type=connection_type, logger=logger)
        # OWNSession only *annotates* these; make them real attributes so close()
        # and the readers can test them.
        self._stream_reader: asyncio.StreamReader | None = None
        self._stream_writer: asyncio.StreamWriter | None = None
        self._is_open = False

    @property
    def is_open(self) -> bool:
        """True after a verified negotiation and before the first failure/close."""
        return self._is_open

    @property
    def log_id(self) -> str:
        return self._gateway.log_id

    async def open(self, timeout: float = 10.0) -> None:
        """Connect and negotiate once (no internal retries), verifying the result.

        Raises ``OSError`` (refused / unreachable / reset), ``TimeoutError``,
        :class:`AuthenticationError` for password problems and :class:`SessionError`
        for any other negotiation failure.  The socket is always closed on failure.
        """
        self._logger.debug("%s Opening %s session", self.log_id, self._type)
        try:
            async with asyncio.timeout(timeout):
                self._stream_reader, self._stream_writer = await asyncio.open_connection(
                    self._gateway.address, self._gateway.port
                )
                if not enable_tcp_keepalive(self._stream_writer):
                    self._logger.debug("%s TCP keepalive not available on the %s socket", self.log_id, self._type)
                result = await self._negotiate()
        except asyncio.IncompleteReadError as err:
            await self.close()
            raise SessionError(f"gateway closed the {self._type} session during negotiation") from err
        except asyncio.LimitOverrunError as err:
            await self.close()
            raise SessionError(f"malformed negotiation frame on the {self._type} session") from err
        except (OSError, TimeoutError):
            await self.close()
            raise

        if not result or not result.get("Success"):
            reason = str((result or {}).get("Message") or "unknown")
            await self.close()
            if reason in AUTH_FAILURE_MESSAGES:
                raise AuthenticationError(reason)
            raise SessionError(f"{self._type} session negotiation failed ({reason})")
        self._is_open = True
        self._logger.debug("%s %s session open", self.log_id, self._type.capitalize())

    async def close(self) -> None:
        """Close the socket; never raises, safe before ``open()`` and when repeated."""
        self._is_open = False
        writer, self._stream_writer = self._stream_writer, None
        self._stream_reader = None
        if writer is None:
            return
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:  # noqa: BLE001 - a reset while closing is not an error
            pass
        self._logger.debug("%s %s session closed", self.log_id, self._type.capitalize())

    async def read_frame(self) -> OWNMessage | str:
        """Read one ``##``-terminated frame.

        Raises :class:`SessionError` when the gateway closed the connection (EOF) or
        sent an over-long frame, ``OSError`` on a reset; both mark the channel as
        not open.  Cancelling this coroutine (``asyncio.wait_for``) is safe: the
        stream buffer is preserved.
        """
        reader = self._stream_reader
        if not self._is_open or reader is None:
            raise SessionError(f"{self._type} session is not open")
        try:
            raw = await reader.readuntil(OWNSession.SEPARATOR)
        except asyncio.IncompleteReadError as err:
            self._is_open = False
            raise SessionError(f"{self._type} session closed by the gateway") from err
        except asyncio.LimitOverrunError as err:
            self._is_open = False
            raise SessionError(f"{self._type} session received an over-long frame") from err
        except OSError:
            self._is_open = False
            raise
        return parse_frame(raw.decode(errors="replace"), self._logger, self.log_id)


class OWNEventChannel(OWNChannel):
    """Monitor ("event") session: frames pushed by the gateway."""

    def __init__(self, gateway: OWNGateway, logger: logging.Logger) -> None:
        super().__init__(gateway, "event", logger)

    async def get_next(self) -> OWNMessage | str:
        """Read the next frame; unlike OWNd's version it raises on transport errors."""
        return await self.read_frame()


class OWNCommandChannel(OWNChannel):
    """Command session: one command in, every reply frame out, until ACK/NACK."""

    def __init__(self, gateway: OWNGateway, logger: logging.Logger) -> None:
        super().__init__(gateway, "command", logger)

    async def send_command(self, message: object, timeout: float = 10.0) -> CommandResult:
        """Send ``message`` and read the gateway's reply frames until ACK/NACK.

        Returns a :class:`CommandResult` whose ``replies`` hold every non-signaling
        frame received before the ACK/NACK (status replies, energy totals...).
        Raises ``TimeoutError`` when the ACK/NACK does not arrive in ``timeout``
        seconds (half-open socket), :class:`SessionError` / ``OSError`` on transport
        failures.  After any exception the channel is no longer open: the caller
        must close it and use a fresh one.
        """
        writer = self._stream_writer
        if not self._is_open or writer is None:
            raise SessionError("command session is not open")
        replies: list[OWNMessage] = []
        try:
            async with asyncio.timeout(timeout):
                writer.write(str(message).encode())
                await writer.drain()
                while True:
                    frame = await self.read_frame()
                    if isinstance(frame, OWNSignaling):
                        if frame.is_ack():
                            return CommandResult(True, replies)
                        if frame.is_nack():
                            return CommandResult(False, replies)
                        self._logger.debug("%s Ignoring signaling frame `%s` while waiting for ACK", self.log_id, frame)
                        continue
                    if isinstance(frame, OWNMessage):
                        replies.append(frame)
                    else:
                        self._logger.debug("%s Ignoring unparsable reply `%s` to `%s`", self.log_id, frame, message)
        except (OSError, TimeoutError):
            # A timeout leaves an unknown number of late frames in flight: the
            # session cannot be trusted any more.
            self._is_open = False
            raise
