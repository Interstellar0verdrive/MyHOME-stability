# MyHOME Integration for Home Assistant

A comprehensive Home Assistant integration for BTicino/Legrand MyHOME home automation systems, enhanced with OpenHAB-inspired patterns for better device management and auto-discovery.

> **Note:** This is an enhanced fork of the original [MyHOME integration](https://github.com/anotherjulien/MyHOME) with additional features including auto-discovery, OpenHAB-inspired architecture, and improved device management.

## Features

- **Complete Device Support**: Lights, switches, covers, climate, sensors, buttons, and alarms
- **Auto-Discovery**: Automatically detect and configure MyHOME devices
- **OpenHAB-Inspired Architecture**: Robust, modular design based on proven patterns
- **Factory Pattern**: Organized device handlers for each category
- **Real-Time Communication**: Async OpenWebNet protocol implementation
- **Modern Home Assistant Integration**: Follows current HA patterns and standards

## Supported Devices

| Device Type | Platform | Description |
|-------------|----------|-------------|
| **Lighting** | `light` | Dimmable lights, ON/OFF switches, light groups |
| **Automation** | `cover` | Shutters, blinds, roller covers |
| **Climate** | `climate` | Thermoregulation zones, temperature sensors |
| **Energy** | `sensor` | Power meters, energy monitoring |
| **Scenarios** | `button` | CEN/CEN+ scenario controls |
| **Auxiliary** | `switch` | Generic auxiliary devices |
| **Alarm** | `alarm_control_panel`, `binary_sensor` | Security systems |
| **Contacts** | `binary_sensor` | Dry contacts, motion sensors |

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click the "+" button
4. Search for "MyHOME"
5. Install the integration
6. Restart Home Assistant

### Manual Installation

1. Download the latest release
2. Copy the `custom_components/myhome` folder to your Home Assistant `custom_components` directory
3. Restart Home Assistant

## Configuration

### Gateway Setup

#### Automatic Discovery (Recommended)

Most MyHOME gateways support automatic discovery via SSDP:

1. Go to **Settings** → **Devices & Services**
2. Click **"+ ADD INTEGRATION"**
3. Search for **"MyHOME"**
4. Select your discovered gateway
5. Enter the gateway password if required
6. Click **"Submit"**

#### Manual Gateway Configuration

If your gateway isn't auto-discovered:

1. Go to **Settings** → **Devices & Services**
2. Click **"+ ADD INTEGRATION"**
3. Search for **"MyHOME"**
4. Select **"Configure manually"**
5. Enter gateway details:
   - **Host**: Gateway IP address
   - **Port**: Gateway port (default: 20000)
   - **Password**: Gateway password (if required)
   - **Name**: Friendly name for the gateway

### Device Configuration

The integration supports two configuration methods:

#### Method 1: Auto-Discovery (Recommended)

Use the built-in auto-discovery to find and configure devices automatically.

**Important:** Auto-discovery is activated via Home Assistant services, NOT via YAML configuration.

**Step 1: Prepare Configuration File**

Create an empty or basic `/config/myhome.yaml` file:

```yaml
# MyHOME Configuration
# Add your gateway configurations here
# (discovered devices will be automatically added)
```

**Step 2: Start Discovery**

Use Home Assistant **Developer Tools → Services** to call:

```yaml
service: myhome.start_discovery
data:
  gateway: "00:03:50:XX:XX:XX"  # Your gateway MAC address
```

**OR** create an automation to start discovery:

```yaml
automation:
  - alias: "Start MyHOME Discovery"
    trigger:
      platform: homeassistant
      event: start
    action:
      service: myhome.start_discovery
      data:
        gateway: "00:03:50:XX:XX:XX"
```

**Discovery Process:**
1. Call the `myhome.start_discovery` service with your gateway MAC
2. The integration sends discovery commands to scan for devices (`*#1*0##`, `*#2*0##`, etc.)
3. Device responses come back as events and are processed by the discovery service
4. Discovered devices are automatically added to `/config/myhome.yaml`
5. The integration reloads and new entities appear in Home Assistant
6. Check logs for discovery progress and any issues

**Common Discovery Issues:**

❌ **Wrong**: Putting service calls in YAML config:
```yaml
# DON'T DO THIS - This goes in myhome.yaml config file
service: myhome.start_discovery
data:
  mac: '00:03:50:XX:XX:XX'
```

✅ **Correct**: Call service through Home Assistant:
```yaml
# Use Developer Tools → Services or automation
service: myhome.start_discovery
data:
  gateway: '00:03:50:XX:XX:XX'
```

**Discovery Warning Messages:**
- `"Could not send message *#18*0##"` - Energy management subsystem not available
- `"Could not send message *#9*0##"` - Auxiliary subsystem not available
- These warnings are **normal** if your gateway doesn't support these subsystems
- Discovery will still find devices from supported subsystems (lighting, automation, etc.)

#### Method 2: Manual Configuration (YAML)

For advanced users or custom configurations, create a `myhome.yaml` file:

**File Location:** `/config/myhome.yaml`

```yaml
# Gateway MAC address (from integration setup)
"00:03:50:XX:XX:XX":

  # Lighting devices
  light:
    living_room_main:
      where: "15"
      name: "Living Room Main Light"
      dimmable: true
      icon: "mdi:ceiling-light"

    kitchen_spots:
      where: "25"
      name: "Kitchen Spot Lights"
      dimmable: false
      icon: "mdi:lightbulb-group"

  # Covers/Shutters
  cover:
    bedroom_shutter:
      where: "32"
      name: "Bedroom Shutter"
      device_class: "shutter"
      inverted: false
      advanced: true
      shutter_run: 20

    living_room_blinds:
      where: "41"
      name: "Living Room Blinds"
      device_class: "blind"

  # Climate devices
  climate:
    living_room_thermo:
      where: "1"
      name: "Living Room Thermostat"
      heat: true
      cool: true
      fan: false
      standalone: false

    bedroom_sensor:
      where: "2"
      name: "Bedroom Temperature"
      standalone: true

  # Energy monitoring
  sensor:
    main_power:
      where: "51"
      name: "Main Power Meter"
      device_class: "power"
      unit_of_measurement: "W"
      refresh_period: 30

  # Scenario buttons
  button:
    scene_controller:
      where: "25"
      name: "Scene Controller"
      buttons: "1,2,3,4"
      short_press: "pushbutton_short_press"
      long_press: "pushbutton_long_press"

  # Binary sensors
  binary_sensor:
    front_door:
      where: "399"
      name: "Front Door Contact"
      device_class: "door"
      inverted: false

  # Switches
  switch:
    garden_pump:
      where: "35"
      name: "Garden Pump"
      device_class: "switch"
      icon: "mdi:water-pump"
```

## Device Configuration Parameters

### Common Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `where` | string | Yes | OpenWebNet WHERE address |
| `name` | string | Yes | Display name in Home Assistant |
| `icon` | string | No | Material Design icon |
| `device_class` | string | No | Home Assistant device class |

### Lighting-Specific Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `dimmable` | boolean | false | Enable dimming functionality |

### Cover-Specific Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `inverted` | boolean | false | Invert open/close commands |
| `advanced` | boolean | false | Enable advanced shutter control |
| `shutter_run` | integer | 20 | Run time in seconds |

### Climate-Specific Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `heat` | boolean | true | Heating support |
| `cool` | boolean | false | Cooling support |
| `fan` | boolean | false | Fan support |
| `standalone` | boolean | true | Standalone thermostat |

### Sensor-Specific Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `refresh_period` | integer | 30 | Update interval in seconds |
| `unit_of_measurement` | string | - | Measurement unit |

### Button-Specific Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `buttons` | string | "1,2,3,4" | Available button numbers |

## Services

The integration provides several services for device control and discovery:

### Discovery Services

#### `myhome.start_discovery`
Start automatic device discovery on a gateway.

```yaml
service: myhome.start_discovery
data:
  gateway: "00:03:50:XX:XX:XX"  # Optional
```

#### `myhome.stop_discovery`
Stop active device discovery.

```yaml
service: myhome.stop_discovery
data:
  gateway: "00:03:50:XX:XX:XX"  # Optional
```

### Utility Services

#### `myhome.sync_time`
Synchronize gateway time with Home Assistant.

```yaml
service: myhome.sync_time
data:
  gateway: "00:03:50:XX:XX:XX"  # Optional
```

#### `myhome.send_message`
Send raw OpenWebNet commands to the gateway.

```yaml
service: myhome.send_message
data:
  gateway: "00:03:50:XX:XX:XX"  # Optional
  message: "*1*1*15##"  # Turn on light at address 15
```

## Events

The integration fires several events for automation:

### Device Discovery Events

- `myhome_device_discovered`: Fired when a new device is found
- `myhome_discovery_completed`: Fired when discovery process finishes

### Device Events

- `myhome_cenplus_event`: CEN+ button events
- `myhome_cen_event`: CEN button events
- `myhome_general_light_event`: General lighting commands
- `myhome_area_light_event`: Area lighting commands
- `myhome_group_light_event`: Group lighting commands

### Example Event Automation

```yaml
automation:
  - alias: "Scene Button Pressed"
    trigger:
      platform: event
      event_type: myhome_cenplus_event
      event_data:
        object: 25
        pushbutton: 1
        event: pushbutton_short_press
    action:
      service: scene.turn_on
      target:
        entity_id: scene.evening_lights
```

## Troubleshooting

### Common Issues

#### Gateway Connection Issues

1. **Check network connectivity**: Ensure Home Assistant can reach the gateway IP
2. **Verify gateway password**: Ensure the password is correct
3. **Check firewall settings**: Ensure port 20000 is accessible
4. **Review logs**: Check Home Assistant logs for connection errors

#### Device Discovery Issues

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

**Devices discovered but not added:**
1. **Check `/config/myhome.yaml`** - devices should be automatically added
2. **Verify file permissions** - ensure Home Assistant can write to the config file
3. **Monitor config file writing** - Look for debug logs like:
   - `"Starting config file write process for device..."`
   - `"Reading existing config file..."`
   - `"Writing updated config to file..."`
   - `"Config file write completed successfully"`
   - `"Config file size after write: XXX bytes"`
4. **Check for config write errors** - Look for error logs like:
   - `"Error writing to config file"`
   - `"Failed to add device to config file"`
   - `"Error in config file write process"`
5. **Monitor integration reload** - check logs for config reload errors
6. **Restart integration** manually if auto-reload fails

#### Configuration Issues

1. **Validate YAML syntax**: Ensure `myhome.yaml` has correct formatting
2. **Check device addresses**: Verify WHERE addresses match physical devices
3. **Review device types**: Ensure correct platform assignments
4. **Restart Home Assistant**: Required after `myhome.yaml` changes

### Debug Logging

Enable debug logging to troubleshoot issues:

```yaml
logger:
  default: warning
  logs:
    custom_components.myhome: debug
    OWNd: debug
```

### Configuration Validation

The integration validates configurations and reports issues in the logs. Common validation errors:

- **Missing required fields**: `where` and `name` are mandatory
- **Invalid WHERE addresses**: Must be valid OpenWebNet addresses
- **Duplicate devices**: Same WHERE address used multiple times
- **Invalid device types**: Unsupported device type specified

## Migration from v0.8 and Earlier

If upgrading from version 0.8 or earlier:

1. **Create myhome.yaml**: Move device configurations from `configuration.yaml`
2. **Update device structure**: Follow the new YAML format above
3. **Remove old configuration**: Delete MyHOME entries from `configuration.yaml`
4. **Restart Home Assistant**: Required for new configuration to take effect
5. **Use auto-discovery**: Consider using the new discovery features

### Example Migration

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

## Advanced Configuration

### Multiple Gateways

Support multiple gateways by adding each gateway's MAC address:

```yaml
# First gateway
"00:03:50:AA:BB:CC":
  light:
    kitchen_light:
      where: "15"
      name: "Kitchen Light"

# Second gateway
"00:03:50:DD:EE:FF":
  cover:
    garage_door:
      where: "25"
      name: "Garage Door"
```

### Custom Icons and Device Classes

Customize device appearance and behavior:

```yaml
"00:03:50:XX:XX:XX":
  light:
    accent_lighting:
      where: "45"
      name: "Accent Lighting"
      dimmable: true
      icon: "mdi:led-strip-variant"

  binary_sensor:
    window_sensor:
      where: "301"
      name: "Living Room Window"
      device_class: "window"
      icon: "mdi:window-open"
```

### Energy Monitoring Configuration

Configure power meters with specific refresh rates:

```yaml
"00:03:50:XX:XX:XX":
  sensor:
    total_power:
      where: "51"
      name: "Total Power Consumption"
      device_class: "power"
      unit_of_measurement: "W"
      refresh_period: 10  # Update every 10 seconds
      icon: "mdi:flash"
```

## Support

- **GitHub Issues**: [Report bugs and feature requests](https://github.com/anotherjulien/MyHOME/issues)
- **Wiki**: [Detailed documentation and examples](https://github.com/anotherjulien/MyHOME/wiki)
- **Community Forum**: [Home Assistant Community](https://community.home-assistant.io/)

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the GNU License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- **Original MyHOME Integration**: This work builds upon the excellent foundation provided by [anotherjulien/MyHOME](https://github.com/anotherjulien/MyHOME)
- **OpenHAB OpenWebNet Binding**: Inspiration for discovery patterns and device organization
- **Home Assistant Community**: Continuous feedback and support
- **BTicino/Legrand**: MyHOME protocol and documentation

## Fork Enhancements

This fork adds the following enhancements to the original integration:

### Architecture Improvements
- **OpenHAB-Inspired Patterns**: Modular device handlers following proven OpenHAB patterns
- **Factory Pattern**: Organized device creation and management
- **Enhanced Constants**: Comprehensive device type organization and mapping
- **Better Error Handling**: Improved logging and debugging capabilities

### Auto-Discovery System
- **Device Discovery Service**: Automatic detection of MyHOME devices
- **Real-Time Discovery**: Processes device responses as they arrive
- **Smart Configuration**: Suggests optimal device settings based on type
- **Discovery Services**: `start_discovery` and `stop_discovery` services

### Enhanced Device Support
- **Extended Device Types**: Better categorization following OpenHAB patterns
- **Device Handlers**: Specialized handlers for each device category
- **Improved Validation**: Better configuration validation and error reporting
- **Properties Management**: Standardized device properties and capabilities

### Developer Experience
- **Modern HA Patterns**: Updated to current Home Assistant standards
- **Better Documentation**: Comprehensive setup and configuration guides
- **Debugging Tools**: Enhanced logging and troubleshooting capabilities
- **Extensible Design**: Easy to add support for new device types

While maintaining full compatibility with existing configurations, these enhancements make the integration more robust, user-friendly, and easier to maintain.
