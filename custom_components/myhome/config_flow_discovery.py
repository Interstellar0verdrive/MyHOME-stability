"""Turn discovered MyHOME devices into YAML suggestions.

Discovered devices are NEVER written into the user's `myhome.yaml`. They are
collected per config entry and written, in one atomic executor write, to
`myhome_discovered.yaml` (DISCOVERED_CONFIG_FILE) in the directory of the
configured `myhome.yaml`, merged with whatever that file already contains. The user copies the entries they want into
their real configuration file.

The emitted YAML uses the MAC-address-root layout accepted by validate.py
(Contract A) and only keys the schema honours (`who`, `where`/`zone`, `name`,
`class`, `dimmable`, `shutter_run`).
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Mapping
from typing import Any

import yaml
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_BUS_INTERFACE,
    CONF_DEVICE_CLASS,
    CONF_DIMMABLE,
    CONF_FILE_PATH,
    CONF_PLATFORMS,
    CONF_SHUTTER_RUN,
    CONF_WHERE,
    CONF_WHO,
    CONF_ZONE,
    DEVICE_TYPE_BUS_AUTOMATION,
    DEVICE_TYPE_BUS_AUX,
    DEVICE_TYPE_BUS_DIMMER,
    DEVICE_TYPE_BUS_DRY_CONTACT_IR,
    DEVICE_TYPE_BUS_ENERGY_METER,
    DEVICE_TYPE_BUS_ON_OFF_SWITCH,
    DEVICE_TYPE_BUS_THERMO_CU,
    DEVICE_TYPE_BUS_THERMO_SENSOR,
    DEVICE_TYPE_BUS_THERMO_ZONE,
    DISCOVERED_CONFIG_FILE,
    DOMAIN,
    LOGGER,
)
from .validate import INTERFACE_CAPABLE_WHO, device_key

# device_type -> (platform, WHO)
_SUGGESTABLE: dict[str, tuple[str, str]] = {
    DEVICE_TYPE_BUS_ON_OFF_SWITCH: ("light", "1"),
    DEVICE_TYPE_BUS_DIMMER: ("light", "1"),
    DEVICE_TYPE_BUS_AUTOMATION: ("cover", "2"),
    DEVICE_TYPE_BUS_ENERGY_METER: ("sensor", "18"),
    DEVICE_TYPE_BUS_THERMO_ZONE: ("climate", "4"),
    # The thermoregulation central unit. ``discovery.py`` reports its WHERE as
    # ``#0`` (never the bare ``0`` OWNd puts on the frame), which is the only
    # spelling ``validate.Zone`` accepts for it and the one ``climate.py`` builds
    # a central-unit entity from.
    DEVICE_TYPE_BUS_THERMO_CU: ("climate", "4"),
    DEVICE_TYPE_BUS_THERMO_SENSOR: ("sensor", "4"),
    DEVICE_TYPE_BUS_DRY_CONTACT_IR: ("binary_sensor", "25"),
    # WHO 9 is accepted by the binary_sensor schema only (_who("1", "9", "25"));
    # ``switch`` is WHO 1, so the suggestion used to be unusable YAML.
    DEVICE_TYPE_BUS_AUX: ("binary_sensor", "9"),
}


def generate_suggested_config(device_info: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
    """Return `(platform, device_cfg)` for a discovered device, or None when this
    device type is not suggested.

    "Not suggested" is not the same as "not supported": since 0.4.0 a CEN/CEN+
    scenario control *does* have an entity representation (the `event` platform),
    but it is declared under `scenario_control:` rather than under a platform
    section, which this writer cannot emit yet, so a keypad seen during a run is
    counted in `MyHOMEDiscoverySuggestions._skipped` and reported in the
    "must be declared by hand" log line. Alarm devices have no entity support at
    all."""
    device_type = device_info["device_type"]
    if device_type not in _SUGGESTABLE:
        return None
    platform, who = _SUGGESTABLE[device_type]
    where = str(device_info["where"])
    cfg: dict[str, Any] = {CONF_WHO: who}
    if platform == "climate":
        cfg[CONF_ZONE] = where
    else:
        cfg[CONF_WHERE] = where
    # A device behind an F422 local bus interface: ``where`` is its address on the
    # riser (``11``) and the interface says which riser (``3``), so the two keys must
    # travel together or the block addresses the main-bus device of the same number.
    # Only WHO 1, 2 and 15 frames carry an interface, and ``validate.py`` refuses the
    # key on any other WHO, so a value that somehow reached us on, say, a WHO 18
    # meter is dropped rather than written into YAML that will not load.
    interface = device_info.get(CONF_BUS_INTERFACE)
    if interface is not None and who in INTERFACE_CAPABLE_WHO:
        cfg[CONF_BUS_INTERFACE] = str(interface)
    cfg["name"] = device_info["name"]

    if platform == "light":
        cfg[CONF_DIMMABLE] = device_type == DEVICE_TYPE_BUS_DIMMER
    elif platform == "cover":
        cfg[CONF_SHUTTER_RUN] = 20
    elif device_type == DEVICE_TYPE_BUS_ENERGY_METER:
        cfg[CONF_DEVICE_CLASS] = "power"
    elif device_type == DEVICE_TYPE_BUS_THERMO_SENSOR:
        cfg[CONF_DEVICE_CLASS] = "temperature"
    elif device_type == DEVICE_TYPE_BUS_DRY_CONTACT_IR:
        cfg[CONF_DEVICE_CLASS] = "motion"
    return platform, cfg


def is_device_configured(hass: HomeAssistant, mac: str, device_cfg: Mapping[str, Any]) -> bool:
    """True when this device is already declared under ANY loaded platform of the
    gateway (validated config in ``hass.data``).

    The comparison is on the full device key ``validate.device_key`` builds -- the
    same function that keyed the loaded configuration -- so ``1-11`` and
    ``1-11#4#03`` are the two different devices they really are.  Until discovery
    learned to read the F422 interface it only knew ``who``/``where``, and this
    function had to accept a configured ``1-11#4#03`` as an answer to a discovered
    ``1-11``; that made a riser device and a main-bus device suppress each other,
    which is a suggestion silently missing rather than a duplicate one.
    """
    key = device_key(device_cfg)
    platforms = hass.data.get(DOMAIN, {}).get(mac, {}).get(CONF_PLATFORMS, {})
    return any(
        key in devices for devices in platforms.values() if isinstance(devices, dict)
    )


def _merge_and_write(path: str, mac: str, suggestions: dict[str, dict[str, dict[str, Any]]]) -> int:
    """Executor job: merge `suggestions` into the YAML file at `path` and write it
    atomically (temp file + os.replace). Returns the number of NEW entries."""
    existing: dict[str, Any] = {}
    try:
        with open(path, encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle)
            if isinstance(loaded, dict):
                existing = loaded
    except FileNotFoundError:
        pass
    except yaml.YAMLError as err:
        # Never destroy a file we cannot parse: keep it and write a sibling.
        LOGGER.warning("%s is not valid YAML (%s); writing suggestions to %s.new", path, err, path)
        path = f"{path}.new"
        existing = {}

    gateway_cfg = existing.setdefault(mac, {})
    if not isinstance(gateway_cfg, dict):
        gateway_cfg = existing[mac] = {}

    added = 0
    for platform, devices in suggestions.items():
        platform_cfg = gateway_cfg.setdefault(platform, {})
        if not isinstance(platform_cfg, dict):
            platform_cfg = gateway_cfg[platform] = {}
        for key, cfg in devices.items():
            if key not in platform_cfg:
                added += 1
            platform_cfg[key] = cfg

    directory = os.path.dirname(path) or "."
    fd, tmp_path = tempfile.mkstemp(prefix=".myhome_discovered.", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(
                "# Devices discovered by the MyHOME integration.\n"
                "# Copy the entries you want into your myhome.yaml (do not include this file as is\n"
                "# unless you want every discovered device to become an entity).\n"
            )
            yaml.safe_dump(existing, handle, default_flow_style=False, sort_keys=False, allow_unicode=True)
        os.replace(tmp_path, path)
    except BaseException:
        try:  # noqa: SIM105 - contextlib.suppress here would hide the cleanup from a reader
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
    return added


class MyHOMEDiscoverySuggestions:
    """Per-entry collector of YAML suggestions for discovered devices."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        self.hass = hass
        self.config_entry = config_entry
        self._pending: dict[str, dict[str, dict[str, Any]]] = {}
        self._skipped: list[str] = []

    def reset(self) -> None:
        """Forget what an earlier run collected. Called when a run starts.

        This collector lives for the life of the config entry, while
        ``MyHOMEDeviceDiscoveryService._discovered_devices`` is cleared at the start of
        every run: without this, the same keypad was appended to ``_skipped`` again on
        every run and the "must be declared by hand" line counted it once per run.
        That line is the only report a user gets about a CEN/CEN+ control, so "3
        device(s)" for one keypad sent them looking for two devices that do not exist.
        """
        self._pending.clear()
        self._skipped.clear()

    @property
    def path(self) -> str:
        """Target file: DISCOVERED_CONFIG_FILE next to the configured myhome.yaml.

        Honours the ``config_file_path`` option (cf-06) but never targets that file.
        """
        config_file = self.config_entry.options.get(CONF_FILE_PATH)
        directory = os.path.dirname(str(config_file)) if config_file else self.hass.config.config_dir
        return os.path.join(directory or self.hass.config.config_dir, DISCOVERED_CONFIG_FILE)

    @property
    def pending_count(self) -> int:
        return sum(len(devices) for devices in self._pending.values())

    def add(self, device_info: dict[str, Any]) -> bool:
        """Queue a discovered device. Returns True when a suggestion was queued."""
        mac = self.config_entry.data["mac"]
        suggestion = generate_suggested_config(device_info)
        if suggestion is None:
            self._skipped.append(f"{device_info['device_type']}@{device_info['where']}")
            LOGGER.debug("Discovery: no YAML suggestion for %s", device_info["unique_id"])
            return False
        platform, cfg = suggestion
        if is_device_configured(self.hass, mac, cfg):
            LOGGER.debug("Discovery: %s already configured, skipping", device_key(cfg))
            return False
        # The YAML key is cosmetic, but it has to be unique and typeable: derived from
        # the device key so an interfaced device (``1-11#4#03``) cannot collide with
        # the main-bus device of the same address, with the characters YAML would
        # rather not see in a mapping key replaced by "_".
        key = f"discovered_{device_key(cfg)}".replace("-", "_").replace("#", "_")
        self._pending.setdefault(platform, {})[key] = cfg
        return True

    async def async_flush(self) -> None:
        """Write pending suggestions to DISCOVERED_CONFIG_FILE (executor, atomic)."""
        if not self._pending:
            if self._skipped:
                LOGGER.info(
                    "Discovery finished: %d device(s) were not suggested and must be "
                    "declared by hand (%s)",
                    len(self._skipped),
                    ", ".join(self._skipped[:10]),
                )
            return
        mac = self.config_entry.data["mac"]
        pending, self._pending = self._pending, {}
        skipped, self._skipped = self._skipped, []
        try:
            added = await self.hass.async_add_executor_job(_merge_and_write, self.path, mac, pending)
        except OSError as err:
            LOGGER.error("Could not write discovery suggestions to %s: %s", self.path, err)
            return
        LOGGER.info(
            "Discovery finished: %d suggestion(s) (%d new) written to %s - copy the ones you want "
            "into your myhome.yaml. %d device(s) were not suggested and must be declared by hand.",
            sum(len(d) for d in pending.values()),
            added,
            self.path,
            len(skipped),
        )
