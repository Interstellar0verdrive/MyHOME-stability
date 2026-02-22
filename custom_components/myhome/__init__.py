""" MyHOME integration enhanced with OpenHAB-style patterns. """

import aiofiles
import yaml

from OWNd.message import OWNCommand, OWNGatewayCommand

from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import (
    device_registry as dr,
    entity_registry as er,
    config_validation as cv,
)
from homeassistant.const import CONF_MAC

from .const import (
    ATTR_GATEWAY,
    ATTR_MESSAGE,
    CONF_PLATFORMS,
    CONF_ENTITY,
    CONF_ENTITIES,
    CONF_GATEWAY,
    CONF_WORKER_COUNT,
    CONF_FILE_PATH,
    CONF_GENERATE_EVENTS,
    DOMAIN,
    LOGGER,
    ALL_DEVICE_SUPPORTED_TYPES,
    DEVICE_TYPE_TO_PLATFORM,
)
from .validate import config_schema, format_mac
from .gateway import MyHOMEGatewayHandler
from .device_factory import MyHOMEDeviceFactory
from .config_flow_discovery import async_setup_discovery

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
PLATFORMS = ["light", "switch", "cover", "climate", "binary_sensor", "sensor", "button"]

async def async_setup(hass, config):
    """Set up the MyHOME component."""
    hass.data[DOMAIN] = {}

    if DOMAIN not in config:
        return True

    LOGGER.error("configuration.yaml not supported for this component!")

    return False


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    mac = entry.data[CONF_MAC]

    if mac not in hass.data[DOMAIN]:
        hass.data[DOMAIN][mac] = {}

    # Safety: ensure dict
    if not isinstance(hass.data[DOMAIN].get(mac), dict):
        hass.data[DOMAIN][mac] = {}

    _config_file_path = (
        str(entry.options[CONF_FILE_PATH])
        if CONF_FILE_PATH in entry.options
        else "/config/myhome.yaml"
    )
    _generate_events = (
        entry.options[CONF_GENERATE_EVENTS] if CONF_GENERATE_EVENTS in entry.options else False
    )

    try:
        async with aiofiles.open(_config_file_path, mode="r") as yaml_file:
            yaml_content = await yaml_file.read()
            parsed_yaml = yaml.safe_load(yaml_content)

            # Handle empty or invalid YAML content
            if parsed_yaml is None or not isinstance(parsed_yaml, dict):
                LOGGER.info(
                    "Configuration file '%s' is empty or invalid, using empty configuration",
                    _config_file_path,
                )
                _validated_config = {}
            else:
                # Filter out 'service' key if present (not part of device config)
                if "service" in parsed_yaml:
                    LOGGER.info(
                        "Filtering out 'service' key from configuration - not supported in device config"
                    )
                    parsed_yaml = {k: v for k, v in parsed_yaml.items() if k != "service"}

                _validated_config = config_schema(parsed_yaml)

    except FileNotFoundError:
        LOGGER.info(
            "Configuration file '%s' not found, creating empty configuration file",
            _config_file_path,
        )
        try:
            async with aiofiles.open(_config_file_path, mode="w") as yaml_file:
                await yaml_file.write(
                    "# MyHOME Configuration\n# Add your gateway configurations here\n"
                )
            _validated_config = {}
        except (OSError, PermissionError) as e:
            LOGGER.error("Failed to create configuration file '%s': %s", _config_file_path, e)
            return False

    # Persist the validated YAML root config for later use (defaults/overrides, etc.)
    hass.data[DOMAIN][mac]["yaml_config"] = _validated_config

    # Check for config under "gateway" key first, then MAC address for backward compatibility
    gateway_config = None
    if "gateway" in _validated_config:
        gateway_config = _validated_config["gateway"]
    elif mac in _validated_config:
        gateway_config = _validated_config[mac]

    if gateway_config:
        # IMPORTANT: merge into existing per-MAC dict instead of overwriting it
        if not isinstance(hass.data[DOMAIN].get(mac), dict):
            hass.data[DOMAIN][mac] = {}

        hass.data[DOMAIN][mac].update(gateway_config)

        # Ensure platforms key exists
        hass.data[DOMAIN][mac].setdefault(CONF_PLATFORMS, {})
    else:
        # Initialize empty configuration for this gateway - will be populated via config flow
        LOGGER.info(
            "Gateway %s not found in configuration file, initializing with empty configuration",
            mac,
        )
        hass.data[DOMAIN][mac].setdefault(CONF_PLATFORMS, {})

    # Migrating the config entry's unique_id if it was not formated to the recommended hass standard
    if entry.unique_id != dr.format_mac(entry.unique_id):
        hass.config_entries.async_update_entry(entry, unique_id=dr.format_mac(entry.unique_id))
        LOGGER.warning("Migrating config entry unique_id to %s", entry.unique_id)

    hass.data[DOMAIN][mac][CONF_ENTITY] = MyHOMEGatewayHandler(
        hass=hass, config_entry=entry, generate_events=_generate_events
    )

    try:
        tests_results = await hass.data[DOMAIN][mac][CONF_ENTITY].test()
    except OSError as ose:
        _gateway_handler = hass.data[DOMAIN][mac][CONF_ENTITY]
        _host = _gateway_handler.gateway.host
        del hass.data[DOMAIN][mac][CONF_ENTITY]
        raise ConfigEntryNotReady(
            f"Gateway cannot be reached at {_host}, make sure its address is correct."
        ) from ose

    if not tests_results["Success"]:
        if tests_results["Message"] in ("password_error", "password_required"):
            entry.async_create_task(
                hass.config_entries.flow.async_init(
                    DOMAIN,
                    context={"source": SOURCE_REAUTH},
                    data=entry.data,
                )
            )
        del hass.data[DOMAIN][mac][CONF_ENTITY]
        return False

    _command_worker_count = int(entry.options[CONF_WORKER_COUNT]) if CONF_WORKER_COUNT in entry.options else 1

    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)

    gateway_device_entry = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, mac)},
        identifiers={(DOMAIN, hass.data[DOMAIN][mac][CONF_ENTITY].unique_id)},
        manufacturer=hass.data[DOMAIN][mac][CONF_ENTITY].manufacturer,
        name=hass.data[DOMAIN][mac][CONF_ENTITY].name,
        model=hass.data[DOMAIN][mac][CONF_ENTITY].model,
        sw_version=hass.data[DOMAIN][mac][CONF_ENTITY].firmware,
    )

    # Only forward supported HA platforms. Ignore YAML keys that are not platforms (e.g. sensor_defaults).
    configured_platforms = list(hass.data[DOMAIN][mac].get(CONF_PLATFORMS, {}).keys())

    supported_platforms = [p for p in configured_platforms if p in PLATFORMS]
    ignored_platforms = [p for p in configured_platforms if p not in PLATFORMS]

    if ignored_platforms:
        LOGGER.warning(
            "Ignoring unknown platform keys in YAML: %s. Only these platforms are supported: %s",
            ignored_platforms,
            PLATFORMS,
        )

    await hass.config_entries.async_forward_entry_setups(entry, supported_platforms)

    # Setup discovery config flow following OpenHAB patterns
    async_setup_discovery(hass)

    # Initialize discovery service following OpenHAB patterns
    hass.data[DOMAIN][mac][CONF_ENTITY].initialize_discovery_service()

    hass.data[DOMAIN][mac][CONF_ENTITY].listening_worker = entry.async_create_background_task(
        hass,
        hass.data[DOMAIN][mac][CONF_ENTITY].listening_loop(),
        name="myhome_listening_worker",
    )

    for i in range(_command_worker_count):
        hass.data[DOMAIN][mac][CONF_ENTITY].sending_workers.append(
            entry.async_create_background_task(
                hass,
                hass.data[DOMAIN][mac][CONF_ENTITY].sending_loop(i),
                name=f"myhome_sending_worker_{i}",
            )
        )

    # Pruning lose entities and devices from the registry
    entity_entries = er.async_entries_for_config_entry(entity_registry, entry.entry_id)

    entities_to_be_removed = []
    devices_to_be_removed = [
        device_entry.id
        for device_entry in device_registry.devices.values()
        if entry.entry_id in device_entry.config_entries
    ]

    configured_entities = []

    for _platform in hass.data[DOMAIN][mac][CONF_PLATFORMS].keys():
        for _device in hass.data[DOMAIN][mac][CONF_PLATFORMS][_platform].keys():
            for _entity_name in hass.data[DOMAIN][mac][CONF_PLATFORMS][_platform][_device][CONF_ENTITIES]:
                if _entity_name != _platform:
                    configured_entities.append(f"{mac}-{_device}-{_entity_name}")
                else:
                    configured_entities.append(f"{mac}-{_device}")

    for entity_entry in entity_entries:
        if entity_entry.unique_id in configured_entities:
            if entity_entry.device_id in devices_to_be_removed:
                devices_to_be_removed.remove(entity_entry.device_id)
            continue
        entities_to_be_removed.append(entity_entry.entity_id)

    for enity_id in entities_to_be_removed:
        entity_registry.async_remove(enity_id)

    if gateway_device_entry.id in devices_to_be_removed:
        devices_to_be_removed.remove(gateway_device_entry.id)

    for device_id in devices_to_be_removed:
        if len(er.async_entries_for_device(entity_registry, device_id, include_disabled_entities=True)) == 0:
            device_registry.async_remove_device(device_id)

    # Defining the services
    async def handle_sync_time(call):
        gateway = call.data.get(ATTR_GATEWAY, None)
        if gateway is None:
            gateway = list(hass.data[DOMAIN].keys())[0]
        else:
            _mac = format_mac(gateway)
            if _mac is None:
                LOGGER.error(
                    "Invalid gateway mac `%s`, could not send time synchronisation message.",
                    gateway,
                )
                return False
            gateway = _mac

        timezone = hass.config.as_dict()["time_zone"]
        if gateway in hass.data[DOMAIN]:
            await hass.data[DOMAIN][gateway][CONF_ENTITY].send(
                OWNGatewayCommand.set_datetime_to_now(timezone)
            )
        else:
            LOGGER.error(
                "Gateway `%s` not found, could not send time synchronisation message.",
                gateway,
            )
            return False

    hass.services.async_register(DOMAIN, "sync_time", handle_sync_time)

    async def handle_send_message(call):
        gateway = call.data.get(ATTR_GATEWAY, None)
        message = call.data.get(ATTR_MESSAGE, None)

        if gateway is None:
            gateway = list(hass.data[DOMAIN].keys())[0]
        else:
            _mac = format_mac(gateway)
            if _mac is None:
                LOGGER.error("Invalid gateway mac `%s`, could not send message `%s`.", gateway, message)
                return False
            gateway = _mac

        LOGGER.debug("Handling message `%s` to be sent to `%s`", message, gateway)

        if gateway in hass.data[DOMAIN]:
            if message is not None:
                own_message = OWNCommand.parse(message)
                if own_message is not None:
                    if own_message.is_valid:
                        LOGGER.debug(
                            "%s Sending valid OpenWebNet Message: `%s`",
                            hass.data[DOMAIN][gateway][CONF_ENTITY].log_id,
                            own_message,
                        )
                        await hass.data[DOMAIN][gateway][CONF_ENTITY].send(own_message)
                else:
                    LOGGER.error("Could not parse message `%s`, not sending it.", message)
                    return False
        else:
            LOGGER.error("Gateway `%s` not found, could not send message `%s`.", gateway, message)
            return False

    hass.services.async_register(DOMAIN, "send_message", handle_send_message)

    # Register discovery service following OpenHAB patterns
    async def handle_start_discovery(call):
        gateway = call.data.get(ATTR_GATEWAY, None)
        if gateway is None:
            gateway = list(hass.data[DOMAIN].keys())[0]
        else:
            _mac = format_mac(gateway)
            if _mac is None:
                LOGGER.error("Invalid gateway mac `%s`, could not start discovery.", gateway)
                return False
            gateway = _mac

        if gateway in hass.data[DOMAIN]:
            await hass.data[DOMAIN][gateway][CONF_ENTITY].start_device_discovery()
            LOGGER.info("Started device discovery on gateway %s", gateway)
        else:
            LOGGER.error("Gateway `%s` not found, could not start discovery.", gateway)
            return False

    hass.services.async_register(DOMAIN, "start_discovery", handle_start_discovery)

    async def handle_stop_discovery(call):
        gateway = call.data.get(ATTR_GATEWAY, None)
        if gateway is None:
            gateway = list(hass.data[DOMAIN].keys())[0]
        else:
            _mac = format_mac(gateway)
            if _mac is None:
                LOGGER.error("Invalid gateway mac `%s`, could not stop discovery.", gateway)
                return False
            gateway = _mac

        if gateway in hass.data[DOMAIN]:
            await hass.data[DOMAIN][gateway][CONF_ENTITY].stop_device_discovery()
            LOGGER.info("Stopped device discovery on gateway %s", gateway)
        else:
            LOGGER.error("Gateway `%s` not found, could not stop discovery.", gateway)
            return False

    hass.services.async_register(DOMAIN, "stop_discovery", handle_stop_discovery)

    return True


async def async_unload_entry(hass, entry):
    """Unload a config entry."""

    LOGGER.info("Unloading MyHome entry.")

    mac = entry.data[CONF_MAC]
    configured_platforms = list(hass.data[DOMAIN].get(mac, {}).get(CONF_PLATFORMS, {}).keys())
    supported_platforms = [p for p in configured_platforms if p in PLATFORMS]

    await hass.config_entries.async_unload_platforms(entry, supported_platforms)

    hass.services.async_remove(DOMAIN, "sync_time")
    hass.services.async_remove(DOMAIN, "send_message")
    hass.services.async_remove(DOMAIN, "start_discovery")
    hass.services.async_remove(DOMAIN, "stop_discovery")

    gateway_handler = hass.data[DOMAIN][entry.data[CONF_MAC]].pop(CONF_ENTITY)
    del hass.data[DOMAIN][entry.data[CONF_MAC]]

    return await gateway_handler.close_listener()