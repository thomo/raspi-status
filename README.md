# fetchsensors

## Prerequisites

- sudo pip3 install Adafruit-SSD1306
- sudo apt-get install python3-paho-mqtt 

## Run fetchsensors.py as daemon

```
sudo cp ~/projects/fetchsensors/fetchsensors.py /usr/local/bin
sudo chmod +x /usr/local/bin/fetchsensors.py

sudo cp ~/projects/fetchsensors/fetchsensors.service /etc/systemd/system/

sudo systemctl start fetchsensors
sudo systemctl status fetchsensors
```

# updateoled.py

## Prerequisites

- sudo apt-get install python3-dateutil 
- sudo apt-get install python3-tz
- sudo apt-get install jq

## Run updateoled.py as daemon

