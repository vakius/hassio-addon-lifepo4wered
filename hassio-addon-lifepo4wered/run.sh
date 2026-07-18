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
lifepo4wered-daemon -f &
DAEMON_PID=$!

# The daemon interprets SIGTERM as "system is shutting down" and tells
# the UPS to cut power (PI_RUNNING=0). By default we SIGKILL it instead
# so stopping the addon leaves the Pi powered; signal_ups_on_stop=true
# restores the daemon's native behavior (UPS cuts power after the stop).
on_stop() {
    if bashio::config.true 'signal_ups_on_stop'; then
        bashio::log.warning \
            "Addon stopping; signaling UPS - power will be cut in seconds"
        kill -TERM "$DAEMON_PID" 2>/dev/null
        wait "$DAEMON_PID"
    else
        bashio::log.info "Addon stopping; daemon killed without signaling UPS"
        kill -9 "$DAEMON_PID" 2>/dev/null
    fi
    exit 0
}
trap on_stop TERM INT

wait "$DAEMON_PID"

# The daemon exited on its own: either the UPS commanded a shutdown
# (button press, low battery, auto shutdown after power loss) or the
# daemon crashed. Its own shutdown trigger (init 0) is useless inside
# a container, so perform a clean host shutdown via the Supervisor.
if [ "$(lifepo4wered-cli get PI_RUNNING 2>/dev/null)" = "0" ]; then
    bashio::log.warning "UPS commanded shutdown; shutting down the host"
    bashio::host.shutdown
    exit 0
fi

bashio::log.error "lifepo4wered-daemon exited unexpectedly"
exit 1
