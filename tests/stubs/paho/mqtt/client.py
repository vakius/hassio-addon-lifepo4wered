"""Minimal paho-mqtt stand-in for end-to-end smoke tests without a broker.

Every publish is appended to the file named by $STUB_MQTT_LOG as
"<topic>\t<payload>".
"""

import os


class CallbackAPIVersion:
    VERSION1 = 1
    VERSION2 = 2


class Client:
    def __init__(self, *args, **kwargs):
        self.on_connect = None
        self._log = open(os.environ["STUB_MQTT_LOG"], "a")

    def username_pw_set(self, username, password=None):
        pass

    def will_set(self, topic, payload=None, qos=0, retain=False):
        pass

    def connect(self, host, port=1883, keepalive=60):
        pass

    def loop_start(self):
        if self.on_connect:
            self.on_connect(self, None, {}, 0, None)

    def loop_stop(self):
        pass

    def disconnect(self):
        self._log.close()

    def publish(self, topic, payload=None, qos=0, retain=False):
        self._log.write("%s\t%s\n" % (topic, payload))
        self._log.flush()
