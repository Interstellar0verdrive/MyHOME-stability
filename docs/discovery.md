# Discovery

How the integration finds devices on the bus that are not yet in `myhome.yaml`,
and what it does (and does not) do with them.

Since 0.2.0, discovery **never writes to `myhome.yaml`**. Suggestions for devices
seen on the bus but not yet configured are written to `myhome_discovered.yaml`,
next to your `myhome.yaml` (same folder, i.e. the path from the **Configuration
file path** option, or your Home Assistant config directory). Review that file
and copy the entries you want into `myhome.yaml` yourself, then reload the
integration.

- Start with `myhome.start_discovery`, stop early with `myhome.stop_discovery`
  (see [Services](services-and-events.md#services)); a run otherwise stops itself
  after 60 seconds. Both flush whatever was collected so far to the file.
- A device already present in `myhome.yaml` (matched on WHO/WHERE) is not
  suggested again.
- Progress fires `myhome_device_discovered` per device and
  `myhome_discovery_completed` when the run ends (see
  [Events → Device discovery events](services-and-events.md#device-discovery-events)).

For debug-log examples of a discovery run, and what to check when no devices are
found or suggestions are missing, see
[Troubleshooting → Device discovery issues](troubleshooting.md#device-discovery-issues).
