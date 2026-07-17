FROM alpine:latest as build
WORKDIR /tmp
RUN apk add linux-headers i2c-tools-dev make g++ git && \
    git clone https://github.com/xorbit/LiFePO4wered-Pi.git && \
    cd LiFePO4wered-Pi && \
    make all USE_SYSTEMD=0 PREFIX=/usr

FROM homeassistant/aarch64-base:latest
ENV LANG C.UTF-8

WORKDIR /
RUN apk add --no-cache python3 py3-paho-mqtt
COPY --from=build /tmp/LiFePO4wered-Pi/build/liblifepo4wered.so /usr/lib/liblifepo4wered.so
COPY --from=build /tmp/LiFePO4wered-Pi/build/lifepo4wered-cli /usr/bin/lifepo4wered-cli
COPY --from=build /tmp/LiFePO4wered-Pi/build/lifepo4wered-daemon /usr/sbin/lifepo4wered-daemon
COPY lifepo4wered_monitor.py /usr/bin/lifepo4wered_monitor.py
COPY run.sh /run.sh
RUN chmod a+x /run.sh
CMD ["/run.sh"]

LABEL io.hass.version="VERSION" io.hass.type="addon" io.hass.arch="aarch64"
