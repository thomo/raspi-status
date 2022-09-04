# fetchsensors

## Prerequisites
(Used with Raspbian Buster, Bullseye)

- sudo apt-get install python3-paho-mqtt 
- sudo apt-get install python3-smbus
- sudo pip3 install htu21df

## Customize

Make adaptions in `sensors.json` 

- the sensor data 
  - id (1-wire id or i2c addr), location, measurement correction (simple +/- value)
  - in case of a i2c multiplexer, the channel
- MQTT topic
- MQTT host
- sensor read interval 

## Run fetchsensors.py 

```
$ ./fetchsensors.py -h
usage: fetchsensors.py [-h] [-c config_file] [--dry]

Fetch and publish sensor values

optional arguments:
  -h, --help      show this help message and exit
  -c config_file  use config file, default is /etc/sensors.json
  --dry           dry run - do not publish values
```

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
