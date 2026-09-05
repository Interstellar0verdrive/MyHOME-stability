# Troubleshooting

Common issues, debug logging, and upgrading from the pre-`myhome.yaml` versions.

## Contents

- [Gateway connection issues](#gateway-connection-issues)
- [Device discovery issues](#device-discovery-issues)
- [Configuration issues](#configuration-issues)
- [Debug logging](#debug-logging)
- [Migration from v0.8 and earlier](#migration-from-v08-and-earlier)

## Gateway connection issues

1. **Check network connectivity**: Ensure Home Assistant can reach the gateway IP
2. **Verify gateway password**: Ensure the password is correct
3. **Check firewall settings**: Ensure port 20000 is accessible
4. **Review logs**: Check Home Assistant logs for connection errors

## Device discovery issues

**"Discovery not active" in logs:**
- Ensure you're calling the service correctly: `service: myhome.start_discovery` with `gateway: "MAC_ADDRESS"`
- Don't put service calls in the YAML config file - use Developer Tools → Services
- Check that the gateway MAC address is correct
- Verify the service call shows `discovery_active: True` in debug logs

**No devices found during discovery:**
1. **Enable debug logging** to see discovery messages:
   ```yaml
   logger:
     logs:
       custom_components.myhome.discovery: debug
       custom_components.myhome.gateway: debug
       custom_components.myhome.config_flow_discovery: debug
   ```
2. **Check discovery status** - Look for logs like:
   - `"Starting MyHOME device discovery on gateway..."`
   - `"Sending discovery command 1/6: *#1*0##"`
   - `"Discovery message received: *1*8*11##"`
   - `"Discovered new device: MyHOME Bus Dimmer 11 at WHERE=11"`
   - `"Starting device configuration suggestion for MyHOME Bus Dimmer 11"`
   - `"Starting config file write process for device MyHOME Bus Dimmer 11"`
   - `"Successfully added device MyHOME Bus Dimmer 11 to configuration file"`
3. **Verify device responses** - Look for incoming messages after discovery commands
4. **Check gateway communication** - Ensure devices are responding to status requests
5. **Manual device test** - Try controlling devices through other MyHOME apps first

**Incorrect device type detection:**
- **Dimmer vs Switch**: Discovery determines device type based on status responses
  - Devices reporting dimming levels (WHAT=2-10, excluding 8) are detected as dimmers
  - Devices reporting only ON/OFF states (WHAT=0,1,8) are detected as switches
  - If a dimmer is incorrectly detected as a switch, manually edit the config and set `dimmable: true`
- **Special states**: WHAT=8 often indicates "temporized ON" or other special states, not dimming capability

**Devices discovered but suggestions missing:**

See [Discovery](discovery.md) — since 0.2.0, suggestions go to `myhome_discovered.yaml`, not `myhome.yaml`.

1. **Check `myhome_discovered.yaml`** exists and has grown after a discovery run.
2. **Verify file permissions** - ensure Home Assistant can write to that folder.
3. Discovery only runs for the duration of `myhome.start_discovery` (default
   60 s) or until `myhome.stop_discovery` is called; both flush whatever was
   collected so far to the file.
4. A device already present in `myhome.yaml` (matched on WHO/WHERE) is not
   suggested again.

## Configuration issues

1. **Validate YAML syntax**: Ensure `myhome.yaml` has correct formatting
2. **Check device addresses**: Verify WHERE addresses match physical devices
3. **Review device types**: Ensure correct platform assignments
4. **Restart Home Assistant**: Required after `myhome.yaml` changes

See [Configuration → Validation errors](configuration.md#validation-errors) for
the exact error messages the integration produces.

## Debug logging

Enable debug logging to troubleshoot issues:

```yaml
logger:
  default: warning
  logs:
    custom_components.myhome: debug
    OWNd: debug
```

> **Note:** For day-to-day use, keep `custom_components.myhome` at `info` (or leave the `logger:` block out entirely) — per-frame bus traffic is only logged at `debug`. Occasional "reconnecting" INFO lines after a gateway hiccup are expected; the integration retries and recovers on its own. Use `debug` only when troubleshooting.

## Migration from v0.8 and earlier

If upgrading from version 0.8 or earlier:

1. **Create myhome.yaml**: Move device configurations from `configuration.yaml`
2. **Update device structure**: Follow the new YAML format below
3. **Remove old configuration**: Delete MyHOME entries from `configuration.yaml`
4. **Restart Home Assistant**: Required for new configuration to take effect
5. **Use auto-discovery**: Consider using the new discovery features

**Old format (configuration.yaml):**
```yaml
myhome:
  gateways:
    - host: 192.168.1.35
      devices:
        light:
          - where: "15"
            name: "Living Room"
            dimmable: true
```

**New format (myhome.yaml):**
```yaml
"00:03:50:XX:XX:XX":
  light:
    living_room:
      where: "15"
      name: "Living Room"
      dimmable: true
```

If you are instead upgrading from a more recent `anotherjulien/MyHOME` or
`artmakh` release (already using `myhome.yaml`), see
[Migrating from the original](migrating-from-original.md) instead.
