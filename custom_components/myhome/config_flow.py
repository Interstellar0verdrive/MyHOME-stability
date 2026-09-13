"""Config flow, options flow and re-authentication for MyHOME gateways."""

from __future__ import annotations

import asyncio
import contextlib
import ipaddress
import os
import re
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlparse

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import (
    SOURCE_REAUTH,
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import (
    CONF_FRIENDLY_NAME,
    CONF_HOST,
    CONF_ID,
    CONF_MAC,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PORT,
)
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
from homeassistant.helpers.service_info.ssdp import SsdpServiceInfo
from OWNd.connection import OWNGateway, OWNSession
from OWNd.discovery import find_gateways, get_port

from .calibration_flow import (
    IDLE_TIMEOUT_SEC,
    CalibrationManagementMixin,
    GuidedCalibrationMixin,
)
from .calibration_store import CalibrationStore
from .const import (
    CONF_ADDRESS,
    CONF_COMMAND_TIMEOUT_SEC,
    CONF_DEFAULT_KEEPALIVE_MINUTES,
    CONF_DEVICE_TYPE,
    CONF_FILE_PATH,
    CONF_FIRMWARE,
    CONF_GENERATE_EVENTS,
    CONF_IDLE_WATCHDOG_SEC,
    CONF_MANUFACTURER,
    CONF_MANUFACTURER_URL,
    CONF_OWN_PASSWORD,
    CONF_PROBE_WINDOW_SEC,
    CONF_QUEUE_TTL_SEC,
    CONF_SSDP_LOCATION,
    CONF_SSDP_ST,
    CONF_UDN,
    CONF_WORKER_COUNT,
    CONFIG_ENTRY_MINOR_VERSION,
    CONFIG_ENTRY_VERSION,
    DEFAULT_COMMAND_TIMEOUT_SEC,
    DEFAULT_CONFIG_FILE,
    DEFAULT_IDLE_WATCHDOG_SEC,
    DEFAULT_KEEPALIVE_MINUTES,
    DEFAULT_MANUFACTURER,
    DEFAULT_PROBE_WINDOW_SEC,
    DEFAULT_QUEUE_TTL_SEC,
    DOMAIN,
    GATEWAY_TEST_TIMEOUT_SEC,
    LOGGER,
    MAX_COMMAND_WORKERS,
    clamp_worker_count,
)
from .validate import format_mac

# Form field names (kept for translation compatibility).
FIELD_SERIAL = "serial"
FIELD_SERIAL_NUMBER = "serialNumber"
FIELD_MODEL_NAME = "modelName"
MANUAL_ENTRY = "00:00:00:00:00:00"

DEFAULT_PORT = 20000
DISCOVERY_TIMEOUT_SEC = 10

# OWNd test_connection() failure messages that are not password related -> abort reasons.
_ABORT_REASONS = {
    "connection_refused": "cannot_connect",
    "negotiation_refused": "negotiation_refused",
    "negociation_error": "negotiation_error",
    "negotiation_failed": "negotiation_failed",
}

_HOSTNAME_RE = re.compile(
    r"^(?=.{1,253}$)[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
    r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
)

PORT_VALIDATOR = vol.All(vol.Coerce(int), vol.Range(min=1, max=65535))
PASSWORD_SELECTOR = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))

# Session tunables exposed in the options flow (0.3.0, G1-D): option key, default
# (= the value hard-coded in 0.2.x, so leaving them alone changes nothing), range and
# unit.  gateway.py / sensor.py read them from ``entry.options`` with the same
# defaults; ``MyHomeOptionsFlowHandler`` reloads the entry when any of them changes.
TUNABLE_OPTIONS: tuple[tuple[str, int, int, int, str], ...] = (
    (CONF_IDLE_WATCHDOG_SEC, DEFAULT_IDLE_WATCHDOG_SEC, 60, 3600, "s"),
    (CONF_PROBE_WINDOW_SEC, DEFAULT_PROBE_WINDOW_SEC, 5, 300, "s"),
    (CONF_COMMAND_TIMEOUT_SEC, DEFAULT_COMMAND_TIMEOUT_SEC, 2, 60, "s"),
    (CONF_QUEUE_TTL_SEC, DEFAULT_QUEUE_TTL_SEC, 10, 600, "s"),
    (CONF_DEFAULT_KEEPALIVE_MINUTES, DEFAULT_KEEPALIVE_MINUTES, 0, 255, "min"),
)


def _number_selector(minimum: int, maximum: int, unit: str) -> NumberSelector:
    """Integer box selector with a unit label (the flow coerces the float back to int)."""
    return NumberSelector(
        NumberSelectorConfig(min=minimum, max=maximum, step=1, mode=NumberSelectorMode.BOX, unit_of_measurement=unit)
    )


def validate_host(value: Any) -> str:
    """Return a normalised IPv4/IPv6 address or hostname, raise ValueError otherwise."""
    text = str(value).strip()
    if not text:
        raise ValueError("empty host")
    try:
        return str(ipaddress.ip_address(text))
    except ValueError:
        pass
    # Digits and dots only is a broken IPv4 address, not a hostname.
    if _HOSTNAME_RE.match(text) and not re.fullmatch(r"[0-9.]+", text):
        return text
    raise ValueError(f"invalid host {text!r}")


def gateway_from_entry_data(data: Mapping[str, Any]) -> OWNGateway:
    """Build an OWNGateway from config entry data (same mapping as gateway.py)."""
    return OWNGateway(
        {
            "address": data[CONF_HOST],
            "port": data[CONF_PORT],
            "password": data.get(CONF_PASSWORD),
            "ssdp_location": data.get(CONF_SSDP_LOCATION),
            "ssdp_st": data.get(CONF_SSDP_ST),
            "deviceType": data.get(CONF_DEVICE_TYPE),
            "friendlyName": data.get(CONF_FRIENDLY_NAME),
            "manufacturer": data.get(CONF_MANUFACTURER) or DEFAULT_MANUFACTURER,
            "manufacturerURL": data.get(CONF_MANUFACTURER_URL),
            "modelName": data.get(CONF_NAME) or "Unknown model",
            "modelNumber": data.get(CONF_FIRMWARE),
            "serialNumber": data[CONF_MAC],
            "UDN": data.get(CONF_UDN),
        }
    )


def entry_data_from_gateway(gateway: OWNGateway) -> dict[str, Any]:
    """Config entry data for a verified gateway (plain values only, cf-03)."""
    mac = format_mac(gateway.serial)
    return {
        CONF_ID: mac,
        CONF_HOST: gateway.address,
        CONF_PORT: int(gateway.port),
        CONF_PASSWORD: gateway.password,
        CONF_SSDP_LOCATION: gateway.ssdp_location,
        CONF_SSDP_ST: gateway.ssdp_st,
        CONF_DEVICE_TYPE: gateway.device_type,
        CONF_FRIENDLY_NAME: gateway.friendly_name,
        CONF_MANUFACTURER: gateway.manufacturer or DEFAULT_MANUFACTURER,
        CONF_MANUFACTURER_URL: gateway.manufacturer_url,
        CONF_NAME: gateway.model_name,
        CONF_FIRMWARE: gateway.model_number,
        CONF_MAC: mac,
        CONF_UDN: gateway.udn,
    }


class MyHomeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a MyHOME config flow."""

    VERSION = CONFIG_ENTRY_VERSION
    MINOR_VERSION = CONFIG_ENTRY_MINOR_VERSION

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> MyHomeOptionsFlowHandler:
        """Get the options flow for this handler."""
        return MyHomeOptionsFlowHandler()

    def __init__(self) -> None:
        """Initialize the MyHOME flow."""
        self.gateway_handler: OWNGateway | None = None
        self.discovered_gateways: dict[str, dict[str, Any]] = {}
        self._source_step: str | None = None  # "user" | "custom" | "ssdp" | "reauth"
        self._custom_input: dict[str, Any] = {}
        self._ssdp_info: dict[str, Any] = {}

    # ------------------------------------------------------------------ helpers
    def _placeholders(self) -> dict[str, str]:
        gateway = self.gateway_handler
        return {
            CONF_HOST: str(gateway.host) if gateway else "",
            CONF_NAME: str(gateway.model_name) if gateway else "",
            CONF_MAC: str(gateway.serial) if gateway else "",
        }

    def _update_context(self) -> None:
        self.context["title_placeholders"] = self._placeholders()

    async def _async_discover(self) -> list[dict[str, Any]]:
        """Run OWNd SSDP discovery; never raise (cf-16)."""
        try:
            async with asyncio.timeout(DISCOVERY_TIMEOUT_SEC):
                return list(await find_gateways())
        except (TimeoutError, OSError, aiohttp.ClientError, IndexError, KeyError, ValueError) as err:
            LOGGER.debug("Gateway discovery failed: %s", err)
            return []

    # ------------------------------------------------------------------ user
    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Pick a discovered gateway or go to manual entry."""
        if user_input is not None:
            serial = user_input[FIELD_SERIAL]
            if serial == MANUAL_ENTRY:
                return await self.async_step_custom()
            # The form's dropdown is built from ``self.discovered_gateways`` itself, so
            # Home Assistant's schema validation already refuses a serial that is not
            # in it: no "gateway vanished" branch is reachable here.
            info = self.discovered_gateways[serial]
            mac = format_mac(info.get(FIELD_SERIAL_NUMBER))
            await self.async_set_unique_id(mac, raise_on_progress=False)
            self._abort_if_unique_id_configured(updates={CONF_HOST: info.get("address")})
            self.gateway_handler = OWNGateway(dict(info))
            self._source_step = "user"
            self._update_context()
            if self.gateway_handler.port is None:
                return await self.async_step_port()
            return await self.async_step_test_connection()

        already_configured = self._async_current_ids(include_ignore=False)
        local_gateways = [
            gateway
            for gateway in await self._async_discover()
            if (mac := format_mac(gateway.get(FIELD_SERIAL_NUMBER))) is not None and mac not in already_configured
        ]
        self.discovered_gateways = {gateway[FIELD_SERIAL_NUMBER]: gateway for gateway in local_gateways}

        choices = {
            **{
                gateway[FIELD_SERIAL_NUMBER]: (
                    f"{gateway.get(FIELD_MODEL_NAME, 'MyHOME')} Gateway ({gateway.get('address')})"
                )
                for gateway in local_gateways
            },
            MANUAL_ENTRY: "Custom",
        }
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(FIELD_SERIAL): vol.In(choices)}),
        )

    # ------------------------------------------------------------------ manual
    async def async_step_custom(
        self, user_input: dict[str, Any] | None = None, errors: dict[str, str] | None = None
    ) -> ConfigFlowResult:
        """Handle manual gateway setup."""
        errors = dict(errors or {})  # never a shared mutable default (cf-04)

        if user_input is not None and not errors:
            host: str | None = None
            try:
                host = validate_host(user_input[CONF_ADDRESS])
            except ValueError:
                errors[CONF_ADDRESS] = "invalid_host"
            mac = format_mac(user_input[FIELD_SERIAL_NUMBER])
            if mac is None:
                errors[FIELD_SERIAL_NUMBER] = "invalid_mac"

            if not errors:
                self._custom_input = dict(user_input)
                port = int(user_input[CONF_PORT])
                await self.async_set_unique_id(mac, raise_on_progress=False)
                self._abort_if_unique_id_configured(updates={CONF_HOST: host, CONF_PORT: port})
                self.gateway_handler = OWNGateway(
                    {
                        "address": host,
                        "port": port,
                        FIELD_SERIAL_NUMBER: mac,
                        FIELD_MODEL_NAME: str(user_input[FIELD_MODEL_NAME]).strip() or "Unknown model",
                        # Plain values: the old flow stored 1-tuples here (cf-03 / core-06).
                        "ssdp_location": None,
                        "ssdp_st": None,
                        "deviceType": None,
                        "friendlyName": None,
                        "manufacturer": DEFAULT_MANUFACTURER,
                        "manufacturerURL": "http://www.bticino.it",
                        "modelNumber": None,
                        "UDN": None,
                    }
                )
                self._source_step = "custom"
                self._update_context()
                return await self.async_step_test_connection()

        suggestions = user_input or self._custom_input
        return self.async_show_form(
            step_id="custom",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_ADDRESS,
                        # The factory default of a BTicino gateway, not any real installation.
                        description={"suggested_value": suggestions.get(CONF_ADDRESS, "192.168.1.35")},
                    ): str,
                    vol.Required(
                        CONF_PORT,
                        description={"suggested_value": suggestions.get(CONF_PORT, DEFAULT_PORT)},
                    ): PORT_VALIDATOR,
                    vol.Required(
                        FIELD_SERIAL_NUMBER,
                        description={"suggested_value": suggestions.get(FIELD_SERIAL_NUMBER, "00:03:50:00:00:00")},
                    ): str,
                    vol.Required(
                        FIELD_MODEL_NAME,
                        description={"suggested_value": suggestions.get(FIELD_MODEL_NAME, "F454")},
                    ): str,
                }
            ),
            errors=errors,
        )

    # ------------------------------------------------------------------ reauth
    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        """Perform reauth upon an authentication error (started by ConfigEntryAuthFailed)."""
        entry = self._get_reauth_entry()
        self.gateway_handler = gateway_from_entry_data(entry.data)
        self._source_step = "reauth"
        self._update_context()
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Ask for the new password."""
        return await self.async_step_password(user_input)

    # ------------------------------------------------------------------ connection test
    async def async_step_test_connection(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Test the gateway (dummy negotiation) and finish or ask for more data."""
        gateway = self.gateway_handler
        assert gateway is not None
        self._update_context()

        try:
            async with asyncio.timeout(GATEWAY_TEST_TIMEOUT_SEC):
                result = await OWNSession(gateway=gateway, logger=LOGGER).test_connection()
        except (OSError, TimeoutError) as err:
            LOGGER.debug("Connection test to %s failed: %s", gateway.host, err)
            result = None
        except ValueError:
            # Legacy OPEN (nonce) authentication needs a numeric password (cf-13).
            return await self.async_step_password(errors={CONF_OWN_PASSWORD: "password_numeric"})

        if not result:
            # OWNd returns None after three refused connections.
            return await self._async_cannot_connect()

        if result.get("Success"):
            return self._async_finish(gateway)

        message = result.get("Message")
        if message == "password_required":
            return await self.async_step_password()
        if message in ("password_error", "password_retry"):
            return await self.async_step_password(errors={CONF_OWN_PASSWORD: message})
        return self.async_abort(reason=_ABORT_REASONS.get(message, "unknown"))

    async def _async_cannot_connect(self) -> ConfigFlowResult:
        """Route a connectivity failure back to the form the user can fix (cf-07)."""
        if self._source_step == "custom":
            return await self.async_step_custom(errors={"base": "cannot_connect"})
        if self._source_step == "reauth":
            return await self.async_step_password(errors={"base": "cannot_connect"})
        return self.async_abort(reason="cannot_connect")

    @callback
    def _async_finish(self, gateway: OWNGateway) -> ConfigFlowResult:
        """Create the entry, or update + reload the entry being re-authenticated."""
        if self.source == SOURCE_REAUTH:
            return self.async_update_reload_and_abort(
                self._get_reauth_entry(), data_updates={CONF_PASSWORD: gateway.password}
            )
        return self.async_create_entry(
            title=f"{gateway.model_name} Gateway",
            data=entry_data_from_gateway(gateway),
            options={CONF_WORKER_COUNT: 1},
        )

    # ------------------------------------------------------------------ port
    async def async_step_port(
        self, user_input: dict[str, Any] | None = None, errors: dict[str, str] | None = None
    ) -> ConfigFlowResult:
        """The gateway port could not be discovered: ask the user."""
        errors = dict(errors or {})
        if user_input is not None:
            assert self.gateway_handler is not None
            self.gateway_handler.port = int(user_input[CONF_PORT])
            return await self.async_step_test_connection()

        return self.async_show_form(
            step_id="port",
            data_schema=vol.Schema(
                {vol.Required(CONF_PORT, description={"suggested_value": DEFAULT_PORT}): PORT_VALIDATOR}
            ),
            description_placeholders=self._placeholders(),
            errors=errors,
        )

    # ------------------------------------------------------------------ password
    async def async_step_password(
        self, user_input: dict[str, Any] | None = None, errors: dict[str, str] | None = None
    ) -> ConfigFlowResult:
        """Ask for the gateway password (also used as the reauth_confirm form)."""
        errors = dict(errors or {})
        if user_input is not None:
            assert self.gateway_handler is not None
            self.gateway_handler.password = str(user_input[CONF_OWN_PASSWORD]).strip()
            return await self.async_step_test_connection()

        return self.async_show_form(
            step_id="reauth_confirm" if self.source == SOURCE_REAUTH else "password",
            data_schema=vol.Schema({vol.Required(CONF_OWN_PASSWORD): PASSWORD_SELECTOR}),
            description_placeholders=self._placeholders(),
            errors=errors,
        )

    # ------------------------------------------------------------------ ssdp
    async def async_step_ssdp(self, discovery_info: SsdpServiceInfo) -> ConfigFlowResult:
        """Handle a gateway announced by the SSDP component."""
        info = dict(discovery_info.upnp)  # never mutate the shared mapping (cf-08)
        mac = format_mac(info.get(FIELD_SERIAL_NUMBER))
        if mac is None:
            return self.async_abort(reason="no_serial")

        host = discovery_info.ssdp_headers.get("_host")
        if not host and discovery_info.ssdp_location:
            host = urlparse(discovery_info.ssdp_location).hostname

        await self.async_set_unique_id(mac)
        # Only the host may legitimately change; the port is never forced (cf-08).
        self._abort_if_unique_id_configured(updates={CONF_HOST: host} if host else None)

        info.update(
            {
                "ssdp_st": discovery_info.ssdp_st,
                "ssdp_location": discovery_info.ssdp_location,
                "address": host,
                "port": None,
            }
        )
        self._ssdp_info = info
        self.gateway_handler = OWNGateway(dict(info))
        self._source_step = "ssdp"
        self._update_context()
        LOGGER.info("Found new MyHOME gateway %s at %s", info.get(FIELD_MODEL_NAME), host)
        return await self.async_step_ssdp_confirm()

    async def async_step_ssdp_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Let the user confirm the discovered gateway (cf-14)."""
        if user_input is None:
            return self.async_show_form(step_id="ssdp_confirm", description_placeholders=self._placeholders())

        info = dict(self._ssdp_info)
        port = None
        if info.get("ssdp_location"):
            try:
                async with asyncio.timeout(DISCOVERY_TIMEOUT_SEC):
                    port = await get_port(info["ssdp_location"])
            except (TimeoutError, OSError, aiohttp.ClientError, IndexError, KeyError, ValueError) as err:
                LOGGER.debug("Could not read the OpenWebNet port from %s: %s", info["ssdp_location"], err)
        info["port"] = int(port) if port else None
        self.gateway_handler = OWNGateway(info)
        if self.gateway_handler.port is None:
            return await self.async_step_port()
        return await self.async_step_test_connection()


class MyHomeOptionsFlowHandler(GuidedCalibrationMixin, CalibrationManagementMixin, OptionsFlow):
    """Everything the user can change about a gateway, behind one "Configura" button.

    Up to 0.5.0's first draft this dialog was a single form of connection settings, and
    the guided cover calibration lived behind "Aggiungi" as a pair of config subentries.
    That put stray rows on the integration page, made Home Assistant file every device
    under "devices not belonging to a subentry", and left the stored numbers with
    nowhere to be looked at. So the dialog now opens on a menu:

    * **Calibra una tapparella** - the guided measurement (`GuidedCalibrationMixin`).
      Hidden outright when this gateway has no basic cover, because the tool would have
      nothing to offer and an empty list is not an explanation.
    * **Profili e tapparelle** and **Calibrazioni** - what is stored, who follows it,
      and how to correct or remove it (`CalibrationManagementMixin`).
    * **Gateway e connessione** - the form this dialog used to be.

    The entry is reloaded **once**, when the dialog closes, and only if something was
    actually changed: a cover reads its travel model in its constructor, so a stored
    calibration only reaches the shutter through a reload - and a reload per screen
    would be a disconnect and reconnect per screen.
    """

    def __init__(self) -> None:
        """No store yet: `async_step_init` is the first thing that can await one."""
        # Only ever a fall-back: `_store` reads the *live* store of the entry and
        # `_async_store` fetches it again before every write, so that a dialog left
        # open across a reload cannot serialise a snapshot of the old one over the file
        # (0.5.0 v2 review, BUG-3).
        self._store_ref: CalibrationStore | None = None
        self._changed = False
        # Whether this dialog has asked to be told when the entry is unloaded.
        self._unload_watched = False
        # The management screens' pointers.
        self._profile_name: str | None = None
        self._cover_unique_id: str | None = None
        self._pending_assignments: dict[str, tuple[str | None, float | None]] = {}
        self._missing_heights: list[str] = []
        self._deleted: str = ""
        self._deleted_covers: list[str] = []
        self._saved_cover: str = ""
        self._saved_profile: str = ""
        self._saved_path: str = ""
        # The `cancelled` screen names the shutter, and `async_step_cancel_flow` has
        # thrown the conversation away by the time that screen is shown.
        self._cancelled_cover: str = ""
        # ...and the guided conversation's.
        self._session: Any = None
        self._watchdog: Any = None
        self._idle_timeout: float = IDLE_TIMEOUT_SEC
        self._reset_calibration()

    # ------------------------------------------------------------------ the menu
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """The first screen: what this dialog can do, and what it will not do by itself."""
        await self._async_store()
        options = []
        if self._covers():
            options.append("calibrate")
        options += ["profiles_covers", "calibrations", "gateway", "finish"]
        return self.async_show_menu(
            step_id="init",
            menu_options=options,
            description_placeholders={"gateway": self.config_entry.title},
        )

    async def async_step_finish(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Close the dialog, rebuilding the gateway when something was stored."""
        return self._async_done()

    @callback
    def _async_done(self, options: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Close the dialog.

        `async_create_entry` on an options flow writes the options and closes it;
        passing back the options unchanged is how a dialog that only touched the
        calibration store closes without pretending the options moved. The reload is
        not here but in `async_remove`, which Home Assistant calls however the dialog
        was left - including the X, which is how half of these screens are left.
        """
        return self.async_create_entry(
            title="", data=options if options is not None else dict(self.config_entry.options)
        )

    @callback
    def async_remove(self) -> None:
        """Rebuild the gateway if anything was stored, whatever way the dialog was left.

        Once, at the end, and only if something changed: a cover reads its travel model
        in its constructor, so a stored calibration reaches the shutter through a
        reload and through nothing else - and a reload on a real gateway is a
        disconnect and a reconnect, very likely while the shutter is still moving from
        the last measurement.

        `async_remove` rather than the "Chiudi" step because there are several ways out
        of a menu this deep, the browser's X among them, and a calibration that only
        took effect when the user happened to leave by the front door would be a
        calibration nobody believes in.
        """
        # The cover this conversation was driving, if any: it is the thing that may
        # still be writing a stop, and `_reset_calibration` is not called on this path.
        cover = getattr(self, "_cover", None)
        super().async_remove()
        if self._changed and self.config_entry.state.recoverable:
            self._changed = False
            self.hass.async_create_task(
                self._async_reload_after_the_tidying_up(cover),
                "myhome options reload",
                eager_start=False,
            )

    async def _async_reload_after_the_tidying_up(self, cover: Any = None) -> None:
        """Reload, but not before a movement that was cut short has written its stop.

        `FlowManager._async_remove_flow_progress` cancels the progress task and then
        calls `async_remove`, so the `finally` that shields the stop of a run in flight
        (`cover._async_calib_timed_run`) has not run yet when we get here. Reloading
        synchronously could close the gateway sessions first, and the one stop the
        runner goes to some trouble to write would be swallowed while the shutter ran
        on to its end stop (0.5.0 v2 review, RISK-4).

        What is awaited is the run itself: the cover clears an event for the whole of a
        guided run and sets it again from whatever ends it, the shielded stop included
        (`MyHOMECover.async_calib_settled`). Two turns of the event loop used to stand
        in for that, which was a guess about how many awaits the stop costs and which
        nothing could pin - mutation M11 of the final review survived it.
        """
        if cover is not None:
            with contextlib.suppress(Exception):
                await cover.async_calib_settled()
        if self.config_entry.state.recoverable:
            self.hass.config_entries.async_schedule_reload(self.config_entry.entry_id)

    # ------------------------------------------------------------------ the gateway
    async def async_step_gateway(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Where the gateway is, how it is spoken to, and where the file lives."""
        entry = self.config_entry
        errors: dict[str, str] = {}
        options = {
            CONF_WORKER_COUNT: 1,
            CONF_FILE_PATH: self.hass.config.path(DEFAULT_CONFIG_FILE),
            CONF_GENERATE_EVENTS: False,
            # Unset tunables are pre-filled with the value 0.2.x used internally.
            **{key: default for key, default, *_ in TUNABLE_OPTIONS},
            **entry.options,
        }

        if user_input is not None:
            host: str | None = None
            try:
                host = validate_host(user_input[CONF_ADDRESS])
            except ValueError:
                errors[CONF_ADDRESS] = "invalid_host"
            file_path = str(user_input[CONF_FILE_PATH]).strip()
            if not await self.hass.async_add_executor_job(os.path.isfile, file_path):
                errors[CONF_FILE_PATH] = "invalid_config_path"

            if not errors:
                new_data = {
                    **entry.data,
                    CONF_HOST: host,
                    CONF_PORT: int(user_input[CONF_PORT]),
                    # "no password" must stay None, not "".  The field is Required and
                    # pre-filled with "", so simply opening this dialog and pressing
                    # Submit used to rewrite a password-less gateway's None into "" --
                    # and OWNd treats the two differently: None asks for a password
                    # (which triggers our reauth flow), "" hashes the empty string and
                    # comes back as "Invalid password".
                    CONF_PASSWORD: str(user_input[CONF_OWN_PASSWORD]).strip() or None,
                }
                new_options = {
                    CONF_WORKER_COUNT: int(user_input[CONF_WORKER_COUNT]),
                    CONF_FILE_PATH: file_path,
                    CONF_GENERATE_EVENTS: bool(user_input[CONF_GENERATE_EVENTS]),
                    # NumberSelector yields floats; the consumers expect ints.
                    **{key: int(user_input[key]) for key, *_ in TUNABLE_OPTIONS},
                }
                if self.hass.config_entries.async_update_entry(entry, data=new_data):
                    self._changed = True
                if new_options != dict(entry.options):
                    self._changed = True
                # The gateway settings are written by closing the dialog, because that
                # is the only moment Home Assistant lets an options flow write them.
                return self._async_done(new_options)

        suggestions = user_input or {}
        return self.async_show_form(
            step_id="gateway",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_ADDRESS,
                        description={"suggested_value": suggestions.get(CONF_ADDRESS, entry.data[CONF_HOST])},
                    ): str,
                    vol.Required(
                        CONF_PORT,
                        description={"suggested_value": suggestions.get(CONF_PORT, entry.data[CONF_PORT])},
                    ): PORT_VALIDATOR,
                    vol.Required(
                        CONF_OWN_PASSWORD,
                        # ``or ""``: a gateway configured without a password stores None.
                        description={
                            "suggested_value": suggestions.get(CONF_OWN_PASSWORD, entry.data.get(CONF_PASSWORD) or "")
                        },
                    ): PASSWORD_SELECTOR,
                    vol.Required(
                        CONF_FILE_PATH,
                        description={
                            "suggested_value": suggestions.get(CONF_FILE_PATH, options[CONF_FILE_PATH])
                        },
                    ): str,
                    # MAX_COMMAND_WORKERS is the single source of truth for this range:
                    # ``__init__.async_setup_entry`` clamps to it, so a wider form only
                    # let the user save a number the integration silently ignored for
                    # ever -- and read it back unchanged at every visit.
                    # The pre-filled value is clamped as well, and not only validated:
                    # an entry saved under the old 1-10 form still holds 5-10, and a
                    # dialog that opens on a number its own schema refuses cannot be
                    # submitted at all -- not even by a user who came here to change the
                    # IP address.  Opening on the clamped value shows the number the
                    # integration has been running all along, and the first save writes
                    # it down.
                    vol.Required(
                        CONF_WORKER_COUNT,
                        description={
                            "suggested_value": clamp_worker_count(
                                suggestions.get(CONF_WORKER_COUNT, options[CONF_WORKER_COUNT])
                            )
                        },
                    ): vol.All(vol.Coerce(int), vol.Range(min=1, max=MAX_COMMAND_WORKERS)),
                    vol.Required(
                        CONF_GENERATE_EVENTS,
                        description={
                            "suggested_value": suggestions.get(CONF_GENERATE_EVENTS, options[CONF_GENERATE_EVENTS])
                        },
                    ): bool,
                    **{
                        vol.Required(
                            key, description={"suggested_value": suggestions.get(key, options[key])}
                        ): _number_selector(minimum, maximum, unit)
                        for key, _default, minimum, maximum, unit in TUNABLE_OPTIONS
                    },
                }
            ),
            errors=errors,
        )
