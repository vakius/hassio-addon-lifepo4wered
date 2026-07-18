# hassio-addon-lifepo4wered

Home Assistant OS addon for the [LiFePO4wered/Pi+](https://lifepo4wered.com/lifepo4wered-pi+.html)
UPS: runs `lifepo4wered-daemon` and publishes UPS stats to MQTT with Home
Assistant autodiscovery.

## MQTT monitor

`lifepo4wered_monitor.py` polls `lifepo4wered-cli get` (default every 30 s)
and publishes all registers as one JSON payload to `lifepo4wered/state`.
Entities appear automatically under one device, "LiFePO4wered/Pi+":

- **Sensors**: input/battery/output voltage (V), output current (A)
- **Binary sensor** "External power": ON when `VIN >= VIN_THRESHOLD`
  (i.e. OFF means running on battery)
- **Diagnostics**: thresholds, timers, watchdog and state registers
- **Availability**: `lifepo4wered/availability` with MQTT Last Will, so
  entities go *unavailable* if the addon stops

MQTT connection details are taken automatically from the Supervisor when the
Mosquitto addon is installed. Addon options: `poll_interval` (seconds) and
optional `mqtt_host`/`mqtt_port`/`mqtt_user`/`mqtt_password` overrides.

### Testing off the Pi

```
python3 -m unittest discover -s tests            # unit tests, no deps needed
LIFEPO4WERED_FAKE=1 MQTT_HOST=... python3 hassio-addon-lifepo4wered/lifepo4wered_monitor.py
```

`LIFEPO4WERED_FAKE=1` replaces the CLI with embedded sample data.

## Stopping the addon vs. shutting down

The `signal_ups_on_stop` option controls what happens to the daemon when
the addon is stopped:

- **Off (default)** — the daemon is killed (SIGKILL) without notifying the
  UPS, so power stays on. Addon stops, restarts and updates are safe. The
  system clock is not saved to the UPS RTC on stop (it still is on
  UPS-commanded shutdowns), and while the addon is stopped, UPS-side
  features (button shutdown, low-battery clean shutdown) are inactive.
- **On** — the daemon is terminated gracefully (SIGTERM), the native
  LiFePO4wered behavior: it saves the clock to the UPS RTC and reports
  "system shutting down" (`PI_RUNNING = 0`), so the UPS **cuts power to
  the Pi a few seconds after the addon stops**. Only use this if you stop
  the addon exclusively as part of powering the system down.

When the UPS itself commands a shutdown (button press, low battery,
`AUTO_SHDN_TIME` after power loss), the addon performs a clean host
shutdown through the Supervisor, and the UPS cuts power once shutdown
completes.

## Setup notes


https://www.linkedin.com/pulse/creating-your-first-home-assistant-add-on-issac-goldstand

https://lifepo4wered.com/files/LiFePO4wered-Pi+-Product-Brief.pdf

https://github.com/xorbit/LiFePO4wered-Pi/blob/master/Dockerfile


https://raspberrypi.stackexchange.com/questions/90315/how-can-i-get-dev-i2c-devices-to-appear-on-alpine-linux

Uncomment line
```
dtparam=i2c_arm=on
```
in `/mnt/boot/config.txt` or `/boot/config.txt` or `/boot/usercfg.txt`

Load module at host startup
```
echo 'i2c-dev' > /etc/modules-load.d/i2c.conf
```
