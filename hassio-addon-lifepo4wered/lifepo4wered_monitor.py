#!/usr/bin/env python3
"""Publish LiFePO4wered/Pi+ UPS stats to MQTT with Home Assistant autodiscovery.

Polls `lifepo4wered-cli get`, publishes the parsed registers as one JSON
payload, and announces entities via MQTT discovery. Configured entirely
through environment variables (see main()).
"""

import json
import logging
import os
import signal
import subprocess
import sys
import time

try:
    import paho.mqtt.client as mqtt
except ImportError:  # allow unit-testing parse/discovery without paho
    mqtt = None

LOG = logging.getLogger("lifepo4wered_monitor")

CLI_COMMAND = ["lifepo4wered-cli", "get"]
CLI_TIMEOUT = 10

# Sample of real `lifepo4wered-cli get` output; used when LIFEPO4WERED_FAKE=1.
SAMPLE_OUTPUT = """\
I2C_REG_VER = 7
I2C_ADDRESS = 67
LED_STATE = 1
TOUCH_STATE = 0
TOUCH_CAP_CYCLES = 0
TOUCH_THRESHOLD = 12
TOUCH_HYSTERESIS = 2
DCO_RSEL = 14
DCO_DCOMOD = 149
VIN = 4709
VBAT = 3233
VOUT = 4993
IOUT = 1355
VBAT_MIN = 2850
VBAT_SHDN = 2950
VBAT_BOOT = 3150
VOUT_MAX = 3500
VIN_THRESHOLD = 4498
IOUT_SHDN_THRESHOLD = 0
VBAT_OFFSET = 103
VOUT_OFFSET = 108
VIN_OFFSET = 99
IOUT_OFFSET = 0
AUTO_BOOT = 4
WAKE_TIME = 0
SHDN_DELAY = 40
AUTO_SHDN_TIME = 15
PI_BOOT_TO = 300
PI_SHDN_TO = 120
RTC_TIME = 1784323638
RTC_WAKE_TIME = 0
WATCHDOG_CFG = 0
WATCHDOG_GRACE = 20
WATCHDOG_TIMER = 20
PI_RUNNING = 1
CFG_WRITE = 0
"""

DEVICE = {
    "identifiers": ["lifepo4wered_pi"],
    "name": "LiFePO4wered/Pi+",
    "manufacturer": "Silicognition LLC",
    "model": "LiFePO4wered/Pi+",
}

# (register, entity name) — millivolt registers shown as V main sensors
MAIN_VOLTAGE = [
    ("VIN", "Input voltage"),
    ("VBAT", "Battery voltage"),
    ("VOUT", "Output voltage"),
]

# millivolt threshold registers, shown as diagnostic V sensors
DIAG_VOLTAGE = [
    ("VBAT_MIN", "Battery minimum voltage"),
    ("VBAT_SHDN", "Battery shutdown voltage"),
    ("VBAT_BOOT", "Battery boot voltage"),
    ("VOUT_MAX", "Output maximum voltage"),
    ("VIN_THRESHOLD", "Input voltage threshold"),
]

# raw-value diagnostic registers (units vary or are unitless flags/timers)
DIAG_RAW = [
    ("AUTO_BOOT", "Auto boot mode"),
    ("SHDN_DELAY", "Shutdown delay"),
    ("AUTO_SHDN_TIME", "Auto shutdown time"),
    ("PI_BOOT_TO", "Pi boot timeout"),
    ("PI_SHDN_TO", "Pi shutdown timeout"),
    ("WATCHDOG_CFG", "Watchdog mode"),
    ("WATCHDOG_GRACE", "Watchdog grace"),
    ("WATCHDOG_TIMER", "Watchdog timer"),
    ("PI_RUNNING", "Pi running flag"),
    ("LED_STATE", "LED state"),
    ("TOUCH_STATE", "Touch state"),
]


def parse_cli_output(text):
    """Parse `KEY = value` lines into a dict; skip anything malformed."""
    values = {}
    for line in text.splitlines():
        key, sep, value = line.partition("=")
        if not sep:
            continue
        try:
            values[key.strip()] = int(value.strip())
        except ValueError:
            LOG.warning("Skipping malformed line: %r", line)
    return values


def read_values():
    """Run the CLI (or use the embedded sample) and return parsed registers."""
    if os.environ.get("LIFEPO4WERED_FAKE"):
        return parse_cli_output(SAMPLE_OUTPUT)
    output = subprocess.run(
        CLI_COMMAND, capture_output=True, text=True,
        timeout=CLI_TIMEOUT, check=True,
    ).stdout
    return parse_cli_output(output)


def discovery_messages(discovery_prefix, state_topic, availability_topic):
    """Yield (topic, config-dict) pairs for every Home Assistant entity."""

    def entity(component, key, name, **extra):
        cfg = {
            "name": name,
            "unique_id": "lifepo4wered_" + key.lower(),
            "state_topic": state_topic,
            "availability_topic": availability_topic,
            "device": DEVICE,
        }
        cfg.update(extra)
        topic = "%s/%s/lifepo4wered/%s/config" % (
            discovery_prefix, component, key.lower())
        return topic, cfg

    def millivolts(key):
        return "{{ (value_json.%s / 1000) | round(3) }}" % key

    for key, name in MAIN_VOLTAGE:
        yield entity(
            "sensor", key, name,
            device_class="voltage",
            unit_of_measurement="V",
            state_class="measurement",
            suggested_display_precision=2,
            value_template=millivolts(key),
        )

    yield entity(
        "sensor", "IOUT", "Output current",
        device_class="current",
        unit_of_measurement="A",
        state_class="measurement",
        suggested_display_precision=2,
        value_template="{{ (value_json.IOUT / 1000) | round(3) }}",
    )

    yield entity(
        "binary_sensor", "EXTERNAL_POWER", "External power",
        device_class="power",
        value_template=(
            "{{ 'ON' if value_json.VIN >= value_json.VIN_THRESHOLD"
            " else 'OFF' }}"),
    )

    for key, name in DIAG_VOLTAGE:
        yield entity(
            "sensor", key, name,
            device_class="voltage",
            unit_of_measurement="V",
            entity_category="diagnostic",
            suggested_display_precision=2,
            value_template=millivolts(key),
        )

    for key, name in DIAG_RAW:
        yield entity(
            "sensor", key, name,
            entity_category="diagnostic",
            value_template="{{ value_json.%s }}" % key,
        )

    yield entity(
        "sensor", "RTC_TIME", "UPS clock",
        device_class="timestamp",
        entity_category="diagnostic",
        value_template="{{ value_json.RTC_TIME | as_datetime }}",
    )


def make_client(host, port, username, password, availability_topic):
    client_kwargs = {"client_id": "lifepo4wered_monitor"}
    try:
        client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            **client_kwargs)
    except AttributeError:  # paho-mqtt 1.x
        client = mqtt.Client(**client_kwargs)
    if username:
        client.username_pw_set(username, password or None)
    client.will_set(availability_topic, "offline", retain=True)
    client.connect(host, port, keepalive=60)
    return client


def main():
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(message)s")

    host = os.environ.get("MQTT_HOST", "localhost")
    port = int(os.environ.get("MQTT_PORT", "1883"))
    username = os.environ.get("MQTT_USER", "")
    password = os.environ.get("MQTT_PASSWORD", "")
    interval = float(os.environ.get("POLL_INTERVAL", "30"))
    discovery_prefix = os.environ.get("DISCOVERY_PREFIX", "homeassistant")
    topic_prefix = os.environ.get("MQTT_TOPIC_PREFIX", "lifepo4wered")

    state_topic = topic_prefix + "/state"
    availability_topic = topic_prefix + "/availability"

    if mqtt is None:
        LOG.error("paho-mqtt is not installed")
        return 1

    def on_connect(client, userdata, flags, reason_code, properties=None):
        LOG.info("Connected to MQTT broker %s:%d", host, port)
        for topic, cfg in discovery_messages(
                discovery_prefix, state_topic, availability_topic):
            client.publish(topic, json.dumps(cfg), retain=True)
        client.publish(availability_topic, "online", retain=True)

    client = make_client(host, port, username, password, availability_topic)
    client.on_connect = on_connect
    client.loop_start()

    running = True

    def stop(signum, frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    online = True
    while running:
        try:
            values = read_values()
        except (subprocess.SubprocessError, OSError) as exc:
            LOG.error("Failed to read UPS state: %s", exc)
            if online:
                client.publish(availability_topic, "offline", retain=True)
                online = False
        else:
            if not online:
                client.publish(availability_topic, "online", retain=True)
                online = True
            client.publish(state_topic, json.dumps(values), retain=True)
            LOG.debug("Published %d values", len(values))
        # sleep in small steps so SIGTERM is handled promptly
        deadline = time.monotonic() + interval
        while running and time.monotonic() < deadline:
            time.sleep(1)

    LOG.info("Shutting down")
    client.publish(availability_topic, "offline", retain=True)
    client.loop_stop()
    client.disconnect()
    return 0


if __name__ == "__main__":
    sys.exit(main())
