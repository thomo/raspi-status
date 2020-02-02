# fetchsensors

## Prerequisites
(Used with Raspbian Buster)

- sudo apt-get install python3-paho-mqtt 
- sudo apt-get install python3-smbus

## Customize

Make adaptions in `sensors.json` 

- the sensor data - id (1-wire id or i2c addr), location, measurement correction (simple +/- value)
- MQTT topic
- MQTT host
- sensor read interval 

## Run fetchsensors.py as daemon

```
sudo cp ~/projects/raspi-status/fetchsensors.py /usr/local/bin
sudo chmod +x /usr/local/bin/fetchsensors.py

sudo cp ~/projects/raspi-status/fetchsensors.service /etc/systemd/system/

sudo systemctl start fetchsensors
sudo systemctl status fetchsensors
```

(If something is changed in the service files reload systemd `systemctl daemon-reload`.)

# updateoled.py

## Prerequisites

- sudo pip3 install Adafruit-SSD1306
- sudo apt-get install python3-dateutil 
- sudo apt-get install python3-tz
- sudo apt-get install jq

## Run updateoled.py as daemon

```
sudo cp ~/projects/raspi-status/updateoled.py /usr/local/bin
sudo chmod +x /usr/local/bin/updateoled.py

sudo cp ~/projects/raspi-status/updateoled.service /etc/systemd/system/

sudo systemctl start updateoled
sudo systemctl status updateoled
```

(If something is changed in the service files reload systemd `systemctl daemon-reload`.)
