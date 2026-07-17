import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..",
                                "hassio-addon-lifepo4wered"))

import lifepo4wered_monitor as mon


class ParseOutputTest(unittest.TestCase):
    def test_parses_sample_output(self):
        values = mon.parse_cli_output(mon.SAMPLE_OUTPUT)
        self.assertEqual(values["VIN"], 4709)
        self.assertEqual(values["VBAT"], 3233)
        self.assertEqual(values["IOUT"], 1355)
        self.assertEqual(values["PI_RUNNING"], 1)
        self.assertEqual(len(values), 36)

    def test_skips_malformed_lines(self):
        values = mon.parse_cli_output("VIN = 5000\ngarbage line\nVBAT = abc\n")
        self.assertEqual(values, {"VIN": 5000})

    def test_handles_negative_values(self):
        values = mon.parse_cli_output("IOUT_OFFSET = -12\n")
        self.assertEqual(values["IOUT_OFFSET"], -12)


class DiscoveryTest(unittest.TestCase):
    def setUp(self):
        self.messages = dict(mon.discovery_messages(
            discovery_prefix="homeassistant",
            state_topic="lifepo4wered/state",
            availability_topic="lifepo4wered/availability",
        ))

    def test_main_voltage_sensor(self):
        topic = "homeassistant/sensor/lifepo4wered/vin/config"
        self.assertIn(topic, self.messages)
        cfg = self.messages[topic]
        self.assertEqual(cfg["device_class"], "voltage")
        self.assertEqual(cfg["unit_of_measurement"], "V")
        self.assertEqual(cfg["state_class"], "measurement")
        self.assertIn("value_json.VIN", cfg["value_template"])
        self.assertNotIn("entity_category", cfg)

    def test_current_sensor(self):
        cfg = self.messages["homeassistant/sensor/lifepo4wered/iout/config"]
        self.assertEqual(cfg["device_class"], "current")
        self.assertEqual(cfg["unit_of_measurement"], "A")

    def test_external_power_binary_sensor(self):
        topic = "homeassistant/binary_sensor/lifepo4wered/external_power/config"
        self.assertIn(topic, self.messages)
        cfg = self.messages[topic]
        self.assertEqual(cfg["device_class"], "power")
        self.assertIn("VIN_THRESHOLD", cfg["value_template"])

    def test_diagnostic_entities_are_categorized(self):
        cfg = self.messages["homeassistant/sensor/lifepo4wered/vbat_shdn/config"]
        self.assertEqual(cfg["entity_category"], "diagnostic")
        self.assertEqual(cfg["unit_of_measurement"], "V")

    def test_skipped_registers_have_no_entity(self):
        for key in ("i2c_reg_ver", "dco_rsel", "vbat_offset", "cfg_write"):
            self.assertNotIn(
                "homeassistant/sensor/lifepo4wered/%s/config" % key,
                self.messages)

    def test_common_fields(self):
        for topic, cfg in self.messages.items():
            self.assertEqual(cfg["state_topic"], "lifepo4wered/state")
            self.assertEqual(cfg["availability_topic"],
                             "lifepo4wered/availability")
            self.assertTrue(cfg["unique_id"].startswith("lifepo4wered_"),
                            topic)
            self.assertEqual(cfg["device"]["identifiers"], ["lifepo4wered_pi"])
            json.dumps(cfg)  # must be serializable

    def test_unique_ids_are_unique(self):
        ids = [cfg["unique_id"] for cfg in self.messages.values()]
        self.assertEqual(len(ids), len(set(ids)))


class ReadValuesTest(unittest.TestCase):
    def test_fake_mode(self):
        os.environ["LIFEPO4WERED_FAKE"] = "1"
        try:
            values = mon.read_values()
        finally:
            del os.environ["LIFEPO4WERED_FAKE"]
        self.assertEqual(values["VOUT"], 4993)


if __name__ == "__main__":
    unittest.main()
