#!/usr/bin/with-contenv bashio

export POLL_INTERVAL="$(bashio::config 'poll_interval')"

# Manual MQTT settings from addon options win; otherwise use the broker
# provided by the Supervisor (e.g. the Mosquitto addon).
if bashio::config.has_value 'mqtt_host'; then
    export MQTT_HOST="$(bashio::config 'mqtt_host')"
    if bashio::config.has_value 'mqtt_port'; then
        export MQTT_PORT="$(bashio::config 'mqtt_port')"
    fi
    if bashio::config.has_value 'mqtt_user'; then
        export MQTT_USER="$(bashio::config 'mqtt_user')"
    fi
    if bashio::config.has_value 'mqtt_password'; then
        export MQTT_PASSWORD="$(bashio::config 'mqtt_password')"
    fi
elif bashio::services.available "mqtt"; then
    export MQTT_HOST="$(bashio::services mqtt 'host')"
    export MQTT_PORT="$(bashio::services mqtt 'port')"
    export MQTT_USER="$(bashio::services mqtt 'username')"
    export MQTT_PASSWORD="$(bashio::services mqtt 'password')"
else
    bashio::log.warning \
        "No MQTT broker configured and no mqtt service available;" \
        "trying localhost:1883"
fi

bashio::log.info "Starting lifepo4wered-daemon"
lifepo4wered-daemon -f &

bashio::log.info "Starting MQTT monitor (poll interval: ${POLL_INTERVAL}s)"
exec python3 /usr/bin/lifepo4wered_monitor.py
