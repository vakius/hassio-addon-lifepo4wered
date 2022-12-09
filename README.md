# hassio-addon-lifepo4wered


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
