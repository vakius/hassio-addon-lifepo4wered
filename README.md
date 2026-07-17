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
