# Raspberry Pi Status Monitor

A system for collecting sensor data and displaying it on a Raspberry Pi. Sensors are read and published via MQTT; a separate process drives an OLED display with live system and sensor stats.

## Repository Structure

```
raspi-status/
├── fetchsensors/        # Python sensor collector and MQTT publisher
│   ├── fetchsensors.py
│   ├── fetchsensors.service
│   ├── sensors.example.json
│   └── README.md
├── updateoled/          # Python OLED display updater
│   ├── updateoled.py
│   └── updateoled.service
├── sensorprobe/         # Go binary for sensor probing (cross-compiled for Raspberry Pi)
│   ├── src/sensorprobe.go
│   ├── build.sh
│   └── README.md
└── install.sh
```

## How the Parts Work Together

1. **fetchsensors** reads connected sensors (DS18B20, HTU21/Si7021, BME280) on a configurable interval and publishes readings to an MQTT broker. See [fetchsensors/README.md](fetchsensors/README.md) for configuration and usage details.

2. **updateoled** reads system metrics and sensor values and renders them on an SSD1306 OLED display. It runs independently of fetchsensors.

3. **sensorprobe** is a Go binary that can be cross-compiled for the Raspberry Pi and deployed separately. See [sensorprobe/README.md](sensorprobe/README.md) for build and deployment instructions.

Both `fetchsensors` and `updateoled` run as systemd services installed by `install.sh`.

## Prerequisites

### Hardware

- Raspberry Pi (tested on Raspberry Pi OS Bookworm)
- One or more sensors: DS18B20, HTU21, Si7021, or BME280
- SSD1306 OLED display (optional)
- TCA9548A I²C multiplexer (optional, for multiple I²C sensors)

### Software

- [uv](https://docs.astral.sh/uv/) (installed automatically by `install.sh` if not present)

### System Configuration

```bash
# Enable I²C and 1-Wire interfaces
sudo raspi-config
# Interface Options -> I2C -> Yes
# Interface Options -> 1-Wire -> Yes
```

## Installation

```bash
git clone https://github.com/thomo/raspi-status.git
cd raspi-status
sudo ./install.sh
```

The installer will ask for the installation location and the user/group to run services as, then use [uv](https://docs.astral.sh/uv/) to create a virtual environment and install dependencies, and configure the systemd services.

## Service Management

```bash
# Start / enable at boot
sudo systemctl start fetchsensors.service
sudo systemctl start updateoled.service
sudo systemctl enable fetchsensors.service
sudo systemctl enable updateoled.service

# Status and logs
sudo systemctl status fetchsensors.service
sudo journalctl -u fetchsensors.service -f
sudo journalctl -u updateoled.service -f
```

## License

See the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
