# LiFePO4wered MQTT Monitor — Design

Date: 2026-07-18. Approved by vaku in conversation.

## Goal

Publish LiFePO4wered/Pi+ UPS stats from the Home Assistant OS addon to MQTT,
with Home Assistant autodiscovery, so the UPS shows up as a device with sensors.

## Approach

A single Python script (`lifepo4wered_monitor.py`) inside the existing addon
container. It shells out to `lifepo4wered-cli get` (already built into the
image), parses the `KEY = value` output, and publishes to MQTT via `paho-mqtt`.
Bindings via ctypes/PyPI were considered and rejected: the CLI is already
present and one subprocess call reads everything at once.

## Behavior

- Poll every `POLL_INTERVAL` seconds (default 30).
- One retained JSON state payload per cycle on `lifepo4wered/state`; all
  entities read it with `value_template` — one MQTT message per cycle.
- Discovery configs (retained) on `<DISCOVERY_PREFIX>/<component>/lifepo4wered/<key>/config`,
  republished on every (re)connect. All entities belong to one HA device
  ("LiFePO4wered/Pi+", manufacturer Silicognition LLC).
- Main sensors: VIN, VBAT, VOUT (mV → V, device_class `voltage`),
  IOUT (mA → A, device_class `current`).
- Binary sensor "External power" (device_class `power`):
  `VIN >= VIN_THRESHOLD` → ON.
- Diagnostic entities (`entity_category: diagnostic`): threshold/config
  registers (VBAT_MIN, VBAT_SHDN, VBAT_BOOT, VOUT_MAX, VIN_THRESHOLD scaled to
  V; timers, watchdog, AUTO_BOOT, LED_STATE, TOUCH_STATE, PI_RUNNING raw;
  RTC_TIME as timestamp).
- Skipped: identity/calibration registers (I2C_REG_VER, I2C_ADDRESS, DCO_*,
  TOUCH_CAP_CYCLES/THRESHOLD/HYSTERESIS, *_OFFSET, CFG_WRITE, RTC_WAKE_TIME,
  WAKE_TIME).
- Availability: MQTT LWT on `lifepo4wered/availability` (`online`/`offline`).
  CLI failure (I2C hiccup): log, publish `offline`, retry next cycle.
- Config via env vars: MQTT_HOST, MQTT_PORT, MQTT_USER, MQTT_PASSWORD,
  POLL_INTERVAL, DISCOVERY_PREFIX, MQTT_TOPIC_PREFIX.
- `LIFEPO4WERED_FAKE=1` uses embedded sample output instead of the CLI, for
  testing off the Pi.

## Addon integration

- Dockerfile: add `python3` + `py3-paho-mqtt` (Alpine packages), copy script
  and `run.sh`, `CMD ["/run.sh"]`.
- `run.sh` (bashio): `lifepo4wered-daemon -f` is the exec'd main process,
  started immediately — it must contact the UPS within PI_BOOT_TO seconds of
  power-on or the UPS cuts power, so nothing (Supervisor API calls included)
  may delay it and monitor failures must never take it down. The monitor runs
  in a background subshell that pulls MQTT host/port/user/password from the
  Supervisor services API (works out of the box with the Mosquitto addon,
  addon options can override) and restarts the monitor with 30 s backoff if
  it exits.
- `config.json`: add `"services": ["mqtt:need"]`, addon options
  (`poll_interval`, optional MQTT overrides), bump version.

## Error handling

- paho built-in reconnect for broker drops; discovery republished on connect.
- 10 s subprocess timeout on the CLI; malformed lines skipped with a warning.
- Script compatible with paho-mqtt 1.x and 2.x callback APIs.

## Testing

- Unit tests (stdlib `unittest`) for output parsing and discovery payload
  generation, runnable on any machine without paho or a broker.
- Fake mode for end-to-end runs against a real broker off the Pi.
