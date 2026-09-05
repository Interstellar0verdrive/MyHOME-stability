"""MyHOME (BTicino / Legrand OpenWebNet) integration - config entry lifecycle.

Contract D (see .audit-2026-09/CONTRACTS.md):
- ``async_setup_entry``: load + validate ``myhome.yaml`` (ConfigEntryError on any
  error, missing file -> created empty + WARNING), migrate legacy entry data, test
  the gateway (ConfigEntryNotReady / ConfigEntryAuthFailed), create the gateway
  device (strings only) and publish its registry id on the handler, forward the
  platforms, THEN start the listening/sending loops as tracked background tasks,
  prune stale registry entries from the validated config (user-disabled entities
  survive) and register the services once per Home Assistant instance.
- ``async_unload_entry``: stop discovery -> close the gateway handler -> unload
  platforms -> drop ``hass.data[DOMAIN][mac]``; services are removed only when the
  last entry is gone.

``hass.data[DOMAIN]`` holds ONLY per-gateway dicts keyed by MAC address
(``CONF_PLATFORMS`` -> platform -> device key -> device config, plus ``CONF_ENTITY``
-> gateway handler).  Nothing else may live there (core-03 / cf-05).
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any

import voluptuous as vol
import yaml

from OWNd.message import OWNCommand, OWNGatewayCommand

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR
from homeassistant.components.button import DOMAIN as BUTTON
from homeassistant.components.climate import DOMAIN as CLIMATE
from homeassistant.components.cover import DOMAIN as COVER
from homeassistant.components.light import DOMAIN as LIGHT
from homeassistant.components.sensor import DOMAIN as SENSOR, SensorDeviceClass
from homeassistant.components.switch import DOMAIN as SWITCH
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_FRIENDLY_NAME, CONF_MAC
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryError,
    ConfigEntryNotReady,
    HomeAssistantError,
    ServiceValidationError,
)
from homeassistant.helpers import (
    config_validation as cv,
    device_registry as dr,
    entity_registry as er,
    issue_registry as ir,
)
from homeassistant.helpers.typing import ConfigType

from .const import (
    ATTR_GATEWAY,
    ATTR_MESSAGE,
    CONF_DEVICE_CLASS,
    CONF_DEVICE_TYPE,
    CONF_ENTITIES,
    CONF_ENTITY,
    CONF_FILE_PATH,
    CONF_FIRMWARE,
    CONF_GENERATE_EVENTS,
    CONF_MANUFACTURER,
    CONF_MANUFACTURER_URL,
    CONF_PLATFORMS,
    CONF_SSDP_LOCATION,
    CONF_SSDP_ST,
    CONF_UDN,
    CONF_WORKER_COUNT,
    CONFIG_ENTRY_MINOR_VERSION,
    CONFIG_ENTRY_VERSION,
    DEFAULT_CONFIG_FILE,
    DEFAULT_MANUFACTURER,
    DOMAIN,
    GATEWAY_DIAG_SUFFIXES,
    GATEWAY_TEST_TIMEOUT_SEC,
    ISSUE_NO_DEVICES_FOR_GATEWAY,
    ISSUE_UNKNOWN_KEYS,
    ISSUE_YAML_INVALID,
    LOGGER,
    SERVICE_SEND_MESSAGE,
    SERVICE_START_DISCOVERY,
    SERVICE_STOP_DISCOVERY,
    SERVICE_SYNC_TIME,
)
from .gateway import MyHOMEGatewayHandler
from .validate import collect_unknown_keys, config_schema, format_mac

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

# Every platform is always forwarded: each platform module returns early when the
# validated config has no devices for it.  This keeps unload symmetric and
# independent from hass.data.
PLATFORMS: list[str] = [LIGHT, SWITCH, COVER, CLIMATE, BINARY_SENSOR, SENSOR, BUTTON]

# OWNd test_connection() messages that mean "the password is wrong/missing".
_AUTH_FAILURE_MESSAGES = ("password_error", "password_required", "password_retry")

# Entry-data keys that the pre-0.2.0 manual config flow stored as 1-tuples (persisted
# as JSON lists).  ``async_migrate_entry`` unwraps them; ``_as_str`` is the last line
# of defence for the device registry (strings only, D1 / core-06).
_LEGACY_LIST_KEYS = (
    CONF_MANUFACTURER,
    CONF_MANUFACTURER_URL,
    CONF_FIRMWARE,  # <- OWNGateway.model_number
    CONF_SSDP_LOCATION,
    CONF_SSDP_ST,
    CONF_DEVICE_TYPE,
    CONF_FRIENDLY_NAME,
    CONF_UDN,
)

SERVICE_GATEWAY_SCHEMA = vol.Schema({vol.Optional(ATTR_GATEWAY): cv.string})
SERVICE_SEND_MESSAGE_SCHEMA = SERVICE_GATEWAY_SCHEMA.extend({vol.Required(ATTR_MESSAGE): cv.string})


# --------------------------------------------------------------------------- helpers
def _unwrap(value: Any) -> Any:
    """Return the single element of a 1-element list/tuple, the value otherwise."""
    if isinstance(value, (list, tuple)) and len(value) == 1:
        return value[0]
    return value


def normalise_entry_data(data: Mapping[str, Any]) -> dict[str, Any]:
    """Unwrap legacy 1-element lists in config entry data (core-06 / cf-03)."""
    return {key: (_unwrap(value) if key in _LEGACY_LIST_KEYS else value) for key, value in data.items()}


def _as_str(value: Any) -> str | None:
    """Coerce a registry attribute to ``str | None`` (never a list)."""
    value = _unwrap(value)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _read_yaml_file(path: str) -> Any:
    """Executor job: parse the YAML configuration file (may raise)."""
    with open(path, encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _create_empty_config_file(path: str) -> None:
    """Executor job: create a commented, empty myhome.yaml."""
    with open(path, "x", encoding="utf-8") as handle:
        handle.write(
            "# MyHOME configuration\n"
            "# See https://github.com/Interstellar0verdrive/MyHOME-stability-next for the format.\n"
            "# gateway:\n"
            "#   mac: 00:03:50:00:00:00\n"
            "#   light:\n"
            "#     my_light:\n"
            "#       where: '11'\n"
            "#       name: My light\n"
        )


# --------------------------------------------------------------------------- repairs
def issue_id(entry: ConfigEntry, issue: str) -> str:
    """Issue registry id of ``issue`` for ``entry`` (one gateway may fail alone)."""
    return f"{entry.entry_id}_{issue}"


@callback
def _async_raise_issue(
    hass: HomeAssistant,
    entry: ConfigEntry,
    issue: str,
    placeholders: dict[str, str],
    *,
    severity: ir.IssueSeverity,
    is_persistent: bool = False,
) -> None:
    """Create (or refresh) a repair issue for this config entry.

    ``is_persistent`` marks an issue the user must not simply dismiss (it survives a
    restart and comes back until the cause is fixed); the dismissable warnings are
    re-created on every load anyway.
    """
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id(entry, issue),
        is_fixable=False,
        is_persistent=is_persistent,
        severity=severity,
        translation_key=issue,
        translation_placeholders=placeholders,
    )


@callback
def _async_clear_issue(hass: HomeAssistant, entry: ConfigEntry, issue: str) -> None:
    """Delete a repair issue once its cause is gone (no-op when it does not exist)."""
    ir.async_delete_issue(hass, DOMAIN, issue_id(entry, issue))


@callback
def _async_report_unknown_keys(
    hass: HomeAssistant, entry: ConfigEntry, path: str, unknown: list[tuple[str, str, str | None]]
) -> None:
    """Raise/clear ISSUE_UNKNOWN_KEYS from what validate.py collected."""
    if not unknown:
        _async_clear_issue(hass, entry, ISSUE_UNKNOWN_KEYS)
        return
    # De-duplicate on (path, key): the same key may be reported by nested schemas.
    seen: dict[tuple[str, str], str | None] = {}
    for key_path, key, hint in unknown:
        seen.setdefault((key_path, key), hint)
    lines = sorted(
        f"{key_path}.{key}" + (f" (did you mean '{hint}'?)" if hint else "") for (key_path, key), hint in seen.items()
    )
    _async_raise_issue(
        hass,
        entry,
        ISSUE_UNKNOWN_KEYS,
        {"path": path, "count": str(len(lines)), "keys": "\n".join(f"- {line}" for line in lines)},
        severity=ir.IssueSeverity.WARNING,
    )


async def _async_load_gateway_config(hass: HomeAssistant, entry: ConfigEntry, path: str, mac: str) -> dict[str, Any]:
    """Load, validate and return the Contract A config of gateway ``mac``.

    Raises ``ConfigEntryError`` with a human readable message on YAML or schema
    errors (shown on the integrations page, core-08) and, since 0.3.0, raises the
    matching repair issue; every issue is cleared again as soon as a later load no
    longer hits its cause.  A missing file is created empty (WARNING) and an
    empty/absent gateway section yields zero devices with a WARNING, never a crash.
    """

    def _fail(message: str) -> ConfigEntryError:
        _async_raise_issue(
            hass,
            entry,
            ISSUE_YAML_INVALID,
            {"path": path, "message": message},
            severity=ir.IssueSeverity.ERROR,
            is_persistent=True,
        )
        return ConfigEntryError(f"{path}: {message}")

    try:
        parsed = await hass.async_add_executor_job(_read_yaml_file, path)
    except FileNotFoundError:
        LOGGER.warning(
            "Configuration file %s not found: creating an empty one. Add your devices to it and reload the integration.",
            path,
        )
        try:
            await hass.async_add_executor_job(_create_empty_config_file, path)
        except OSError as err:
            raise _fail(f"cannot create the configuration file ({err})") from err
        parsed = None
    except OSError as err:
        raise _fail(f"cannot read the configuration file ({err})") from err
    except yaml.YAMLError as err:
        raise _fail(f"the file is not valid YAML ({err})") from err

    if parsed is None:
        parsed = {}
    if not isinstance(parsed, dict):
        raise _fail(f"the file must contain a mapping (gateway: ...), found {type(parsed).__name__}")

    try:
        with collect_unknown_keys() as unknown_keys:
            validated = config_schema(parsed)
    except vol.Invalid as err:
        raise _fail(str(err)) from err

    # The file parsed and validated: any previous "broken configuration" repair is stale.
    _async_clear_issue(hass, entry, ISSUE_YAML_INVALID)
    _async_report_unknown_keys(hass, entry, path, unknown_keys)

    gateway_config = validated.get(mac)
    if gateway_config is None:
        others = ", ".join(sorted(k for k in validated if k != mac)) or "none"
        LOGGER.warning(
            "Gateway %s has no section in %s (gateways found in the file: %s): no device will be created",
            mac,
            path,
            others,
        )
        _async_raise_issue(
            hass,
            entry,
            ISSUE_NO_DEVICES_FOR_GATEWAY,
            {"mac": mac, "path": path, "others": others},
            severity=ir.IssueSeverity.WARNING,
        )
        gateway_config = {CONF_PLATFORMS: {}}
    else:
        _async_clear_issue(hass, entry, ISSUE_NO_DEVICES_FOR_GATEWAY)
    gateway_config.setdefault(CONF_PLATFORMS, {})
    return gateway_config


def expected_unique_ids(mac: str, platforms: Mapping[str, Mapping[str, Mapping[str, Any]]]) -> set[str]:
    """Unique ids the platforms create for the validated config (registry pruning).

    Kept in sync with the platform modules:
    - light / switch / cover / climate: ``{mac}-{device_key}``
    - button: ``{mac}-{device_key}-disable`` and ``-enable``
    - binary_sensor: ``{mac}-{device_key}-{class}``
    - sensor: power/energy -> one id per pre-seeded ``entities`` slot
      (``-power``, ``-daily-energy``, ``-monthly-energy``, ``-total-energy``);
      temperature / illuminance -> ``{mac}-{device_key}-{class}``.
    - the five gateway diagnostic entities (0.3.0), which exist for every gateway
      and have no YAML counterpart: ``{mac}-{suffix}`` for GATEWAY_DIAG_SUFFIXES.
    """
    expected: set[str] = {f"{mac}-{suffix}" for suffix in GATEWAY_DIAG_SUFFIXES}
    for platform, devices in platforms.items():
        for device_key, device in devices.items():
            base = f"{mac}-{device_key}"
            if platform in (LIGHT, SWITCH, COVER, CLIMATE):
                expected.add(base)
            elif platform == BUTTON:
                expected.add(f"{base}-disable")
                expected.add(f"{base}-enable")
            elif platform == BINARY_SENSOR:
                expected.add(f"{base}-{device.get(CONF_DEVICE_CLASS)}")
            elif platform == SENSOR:
                sensor_class = device.get(CONF_DEVICE_CLASS)
                if sensor_class in (SensorDeviceClass.POWER, SensorDeviceClass.ENERGY):
                    for slot in device.get(CONF_ENTITIES, {}):
                        expected.add(f"{base}-{slot}")
                else:
                    expected.add(f"{base}-{sensor_class}")
            else:
                expected.add(base)
    return expected


def _configured_device_identifiers(mac: str, platforms: Mapping[str, Mapping[str, Any]]) -> set[tuple[str, str]]:
    """Device registry identifiers of every configured device plus the gateway."""
    identifiers = {(DOMAIN, mac)}
    for devices in platforms.values():
        identifiers.update((DOMAIN, f"{mac}-{device_key}") for device_key in devices)
    return identifiers


@callback
def _async_prune_registries(hass: HomeAssistant, entry: ConfigEntry, mac: str, gateway_device_id: str) -> None:
    """Remove registry entities/devices that are no longer in myhome.yaml (core-05).

    The expected set comes from the validated configuration, so entities the user
    disabled in the UI are kept; the gateway device is never touched.
    """
    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)
    platforms = hass.data[DOMAIN][mac][CONF_PLATFORMS]
    expected = expected_unique_ids(mac, platforms)

    for entity_entry in er.async_entries_for_config_entry(entity_registry, entry.entry_id):
        if entity_entry.unique_id in expected:
            continue
        LOGGER.info("Removing %s (%s): no longer in the configuration", entity_entry.entity_id, entity_entry.unique_id)
        entity_registry.async_remove(entity_entry.entity_id)

    for device_entry in dr.async_entries_for_config_entry(device_registry, entry.entry_id):
        if device_entry.id == gateway_device_id:
            continue
        if er.async_entries_for_device(entity_registry, device_entry.id, include_disabled_entities=True):
            continue
        LOGGER.info("Removing device %s: no entity left", device_entry.name)
        device_registry.async_remove_device(device_entry.id)


async def _async_cancel_workers(handler: MyHOMEGatewayHandler) -> None:
    """Cancel and await the loop tasks started by async_setup_entry.

    Contract B makes ``close_listener`` authoritative (F3); until then, and as a
    belt-and-braces measure afterwards, make sure nothing runs against a torn-down
    ``hass.data`` (core-10).
    """
    tasks = [task for task in (handler.listening_worker, *handler.sending_workers) if task is not None]
    handler.listening_worker = None
    handler.sending_workers = []
    for task in tasks:
        if not task.done():
            task.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


# --------------------------------------------------------------------------- setup
async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the integration (config entries only; YAML is rejected by CONFIG_SCHEMA)."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate legacy config entries (version 1 -> 2: unwrap list-valued data)."""
    if entry.version > CONFIG_ENTRY_VERSION:
        # Downgrade of the integration: refuse rather than corrupt.
        return False
    if entry.version == 1:
        new_data = normalise_entry_data(entry.data)
        hass.config_entries.async_update_entry(
            entry,
            data=new_data,
            version=CONFIG_ENTRY_VERSION,
            minor_version=CONFIG_ENTRY_MINOR_VERSION,
        )
        LOGGER.info("Migrated MyHOME config entry %s to version %s", entry.title, CONFIG_ENTRY_VERSION)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a MyHOME gateway from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Migrating the config entry's unique_id if it was not formatted to the hass standard
    if entry.unique_id and entry.unique_id != dr.format_mac(entry.unique_id):
        hass.config_entries.async_update_entry(entry, unique_id=dr.format_mac(entry.unique_id))
        LOGGER.info("Normalised config entry unique_id to %s", entry.unique_id)

    mac: str = entry.data[CONF_MAC]
    config_file_path = str(entry.options.get(CONF_FILE_PATH) or hass.config.path(DEFAULT_CONFIG_FILE))
    generate_events = bool(entry.options.get(CONF_GENERATE_EVENTS, False))
    worker_count = max(1, int(entry.options.get(CONF_WORKER_COUNT, 1)))

    gateway_config = await _async_load_gateway_config(hass, entry, config_file_path, mac)
    # Fresh per-gateway dict: never merge into leftovers of a previous setup.
    hass.data[DOMAIN][mac] = gateway_config

    # The handler reads its energy defaults from hass.data[DOMAIN][mac] -> create it after.
    handler = MyHOMEGatewayHandler(hass=hass, config_entry=entry, generate_events=generate_events)
    hass.data[DOMAIN][mac][CONF_ENTITY] = handler

    try:
        async with asyncio.timeout(GATEWAY_TEST_TIMEOUT_SEC):
            test_result = await handler.test()
    except (OSError, TimeoutError) as err:
        hass.data[DOMAIN].pop(mac, None)
        raise ConfigEntryNotReady(
            f"Gateway {handler.gateway.host}:{handler.gateway.port} cannot be reached ({type(err).__name__}), check its address"
        ) from err

    if not test_result:
        # OWNd returns None after three refused connections.
        hass.data[DOMAIN].pop(mac, None)
        raise ConfigEntryNotReady(f"Gateway {handler.gateway.host}:{handler.gateway.port} refused the connection")
    if not test_result.get("Success"):
        message = test_result.get("Message")
        hass.data[DOMAIN].pop(mac, None)
        if message in _AUTH_FAILURE_MESSAGES:
            # HA starts the reauth flow (with the entry id) and raises a repair issue.
            raise ConfigEntryAuthFailed(f"Gateway {handler.gateway.host} rejected the password ({message})")
        raise ConfigEntryNotReady(f"Gateway {handler.gateway.host} test failed: {message}")

    device_registry = dr.async_get(hass)
    gateway_device = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, mac)},
        identifiers={(DOMAIN, handler.unique_id)},
        manufacturer=_as_str(handler.manufacturer) or DEFAULT_MANUFACTURER,
        name=handler.name,
        model=_as_str(handler.model),
        sw_version=_as_str(handler.firmware),
    )
    # Contract B/C: entities link to the gateway with via_device_id.
    handler.device_id = gateway_device.id

    # Make sure the sessions are closed even when setup fails half way (core-10).
    entry.async_on_unload(handler.close_listener)

    unknown_platforms = [p for p in hass.data[DOMAIN][mac][CONF_PLATFORMS] if p not in PLATFORMS]
    if unknown_platforms:
        LOGGER.warning("Ignoring unknown platform keys in %s: %s", config_file_path, unknown_platforms)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Loops start AFTER the entities exist so no frame is dispatched into a half-built map.
    handler.initialize_discovery_service()
    handler.listening_worker = entry.async_create_background_task(
        hass, handler.listening_loop(), name=f"myhome_{mac}_listening_worker"
    )
    for worker_id in range(worker_count):
        handler.sending_workers.append(
            entry.async_create_background_task(
                hass, handler.sending_loop(worker_id), name=f"myhome_{mac}_sending_worker_{worker_id}"
            )
        )

    _async_prune_registries(hass, entry, mac, gateway_device.id)
    _async_register_services(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry: discovery -> gateway sessions -> platforms -> data."""
    mac: str = entry.data[CONF_MAC]
    gateway_data: dict[str, Any] = hass.data.get(DOMAIN, {}).get(mac, {})
    handler: MyHOMEGatewayHandler | None = gateway_data.get(CONF_ENTITY)

    if handler is not None:
        await handler.stop_device_discovery()
        await handler.close_listener()
        await _async_cancel_workers(handler)

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not unload_ok:
        return False

    hass.data.get(DOMAIN, {}).pop(mac, None)

    still_loaded = [e for e in hass.config_entries.async_loaded_entries(DOMAIN) if e.entry_id != entry.entry_id]
    if not still_loaded:
        _async_unregister_services(hass)
    return True


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Drop the repair issues of a gateway that is being removed."""
    for issue in (ISSUE_YAML_INVALID, ISSUE_UNKNOWN_KEYS, ISSUE_NO_DEVICES_FOR_GATEWAY):
        _async_clear_issue(hass, entry, issue)


async def async_remove_config_entry_device(hass: HomeAssistant, entry: ConfigEntry, device_entry: dr.DeviceEntry) -> bool:
    """Allow deleting a device from the UI when it is no longer in myhome.yaml."""
    mac: str = entry.data[CONF_MAC]
    platforms = hass.data.get(DOMAIN, {}).get(mac, {}).get(CONF_PLATFORMS, {})
    configured = _configured_device_identifiers(mac, platforms)
    return not any(identifier in configured for identifier in device_entry.identifiers)


# --------------------------------------------------------------------------- services
def _async_resolve_handler(hass: HomeAssistant, call: ServiceCall) -> MyHOMEGatewayHandler:
    """Return the gateway handler targeted by a service call.

    ``gateway`` is optional only when exactly one gateway is loaded (core-03/07).
    """
    loaded = {mac: data[CONF_ENTITY] for mac, data in hass.data.get(DOMAIN, {}).items() if CONF_ENTITY in data}
    gateway = call.data.get(ATTR_GATEWAY)
    if gateway is None:
        if len(loaded) == 1:
            return next(iter(loaded.values()))
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="gateway_required",
            translation_placeholders={"count": str(len(loaded))},
        )
    mac = format_mac(gateway)
    if mac is None:
        raise ServiceValidationError(
            translation_domain=DOMAIN, translation_key="invalid_gateway", translation_placeholders={"gateway": str(gateway)}
        )
    if mac not in loaded:
        raise ServiceValidationError(
            translation_domain=DOMAIN, translation_key="gateway_not_found", translation_placeholders={"gateway": mac}
        )
    return loaded[mac]


async def _async_send_or_raise(handler: MyHOMEGatewayHandler, message: OWNCommand) -> None:
    """Queue a command; Contract B lets ``send`` return False when the queue is closed/full."""
    if await handler.send(message) is False:
        raise HomeAssistantError(
            translation_domain=DOMAIN, translation_key="send_failed", translation_placeholders={"message": str(message)}
        )


@callback
def _async_register_services(hass: HomeAssistant) -> None:
    """Register the domain services once per Home Assistant instance."""
    if hass.services.has_service(DOMAIN, SERVICE_SYNC_TIME):
        return

    async def handle_sync_time(call: ServiceCall) -> None:
        handler = _async_resolve_handler(hass, call)
        await _async_send_or_raise(handler, OWNGatewayCommand.set_datetime_to_now(hass.config.time_zone))

    async def handle_send_message(call: ServiceCall) -> None:
        handler = _async_resolve_handler(hass, call)
        raw = call.data[ATTR_MESSAGE]
        message = OWNCommand.parse(raw)
        if message is None or not message.is_valid:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="invalid_message", translation_placeholders={"message": str(raw)}
            )
        LOGGER.debug("%s Sending OpenWebNet message `%s` (service call)", handler.log_id, message)
        await _async_send_or_raise(handler, message)

    async def handle_start_discovery(call: ServiceCall) -> None:
        handler = _async_resolve_handler(hass, call)
        await handler.start_device_discovery()

    async def handle_stop_discovery(call: ServiceCall) -> None:
        handler = _async_resolve_handler(hass, call)
        await handler.stop_device_discovery()

    hass.services.async_register(DOMAIN, SERVICE_SYNC_TIME, handle_sync_time, schema=SERVICE_GATEWAY_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_SEND_MESSAGE, handle_send_message, schema=SERVICE_SEND_MESSAGE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_START_DISCOVERY, handle_start_discovery, schema=SERVICE_GATEWAY_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_STOP_DISCOVERY, handle_stop_discovery, schema=SERVICE_GATEWAY_SCHEMA)


@callback
def _async_unregister_services(hass: HomeAssistant) -> None:
    """Remove the domain services (called when the last entry unloads)."""
    for service in (SERVICE_SYNC_TIME, SERVICE_SEND_MESSAGE, SERVICE_START_DISCOVERY, SERVICE_STOP_DISCOVERY):
        if hass.services.has_service(DOMAIN, service):
            hass.services.async_remove(DOMAIN, service)
