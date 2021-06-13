FROM ubuntu:latest as build
WORKDIR /tmp
RUN apt-get update && \
    apt-get -y install build-essential git libsystemd-dev && \
    git clone https://github.com/xorbit/LiFePO4wered-Pi.git && \
    cd LiFePO4wered-Pi && \
    make all USE_SYSTEMD=0 PREFIX=/usr


FROM homeassistant/aarch64-base:latest
ENV LANG C.UTF-8

WORKDIR /
COPY --from=build /tmp/LiFePO4wered-Pi/build/liblifepo4wered.so /usr/lib/liblifepo4wered.so
COPY --from=build /tmp/LiFePO4wered-Pi/build/lifepo4wered-cli /usr/bin/lifepo4wered-cli
COPY --from=build /tmp/LiFePO4wered-Pi/build/lifepo4wered-daemon /usr/sbin/lifepo4wered-daemon
# COPY start.sh /app/start.sh
# ENTRYPOINT ["/app/start.sh"]
CMD lifepo4wered-daemon -f

LABEL io.hass.version="VERSION" io.hass.type="addon" io.hass.arch="aarch64"
