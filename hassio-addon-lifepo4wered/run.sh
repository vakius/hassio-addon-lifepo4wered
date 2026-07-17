#!/usr/bin/with-contenv bashio

# The daemon must contact the UPS within PI_BOOT_TO seconds of power-on,
# otherwise the UPS assumes the boot failed and cuts power. It is therefore
# the main process, started before any MQTT/Supervisor API calls, and the
# monitor runs on the side where its failures can never take the daemon down.

setup_mqtt_env() {
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
}

(
    setup_mqtt_env
    bashio::log.info "Starting MQTT monitor (poll interval: ${POLL_INTERVAL}s)"
    while true; do
        python3 /usr/bin/lifepo4wered_monitor.py || true
        bashio::log.warning "MQTT monitor exited; restarting in 30s"
        sleep 30
    done
) &

bashio::log.info "Starting lifepo4wered-daemon"
exec lifepo4wered-daemon -f
