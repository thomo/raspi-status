# fetchsensors

Python script that reads sensor data and publishes it via MQTT. Runs as a systemd service.

## Configuration

### Automatic Sensor Detection

Generate a `sensors.json` with all connected sensors:

```bash
./fetchsensors.py --generate
```

This detects all connected I²C and 1-Wire sensors and writes a `sensors.json` including multiplexer channel information where applicable.

### Manual Configuration

Edit `sensors.json` to customise sensor locations, measurement corrections, MQTT settings, and update intervals. See `sensors.example.json` for a full reference.

Key fields:

| Field | Description |
|-------|-------------|
| `mqtt.server` | MQTT broker hostname |
| `mqtt.topic` | Topic to publish sensor readings to |
| `interval` | Seconds between readings |
| `node` | Identifier for this Raspberry Pi |
| `sensors[].location` | Human-readable location label |
| `sensors[].enabled` | `1` to enable, `0` to disable |
| `sensors[].values[].correction` | Offset applied to the raw reading |

Example:

```json
{
    "mqtt": {
        "server": "mqtt.server.any",
        "topic": "sensors/data"
    },
    "interval": 20,
    "node": "raspberrypi",
    "sensors": [
        {
            "id": "28-0301a279dec6",
            "sensor": "DS18B20",
            "enabled": 1,
            "location": "outside",
            "values": [
                {"correction": -1.1, "measurand": "temperature"}
            ]
        },
        {
            "id": 64,
            "channel": 2,
            "sensor": "HTU21",
            "enabled": 1,
            "location": "living_room",
            "values": [
                {"correction": -0.5, "measurand": "temperature"},
                {"correction": 2.0, "measurand": "humidity"}
            ]
        }
    ]
}
```

## Usage

```bash
# Activate the venv first (from repo root)
source ../venv/bin/activate

# Normal operation
./fetchsensors.py

# Use a custom config file
./fetchsensors.py -c /path/to/sensors.json

# Test run without publishing to MQTT
./fetchsensors.py --dry

# Generate sensors.json with detected sensors
./fetchsensors.py --generate
```

## Service Management

The systemd service is installed by `install.sh` from `fetchsensors.service`.

```bash
sudo systemctl start fetchsensors.service
sudo systemctl enable fetchsensors.service
sudo systemctl status fetchsensors.service

# Follow logs
sudo journalctl -u fetchsensors.service -f

# View recent logs
sudo journalctl -u fetchsensors.service -n 50 --no-pager
```

When modifying the service file, redeploy with:

```bash
sudo cp fetchsensors.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl restart fetchsensors.service
```

## Troubleshooting

### Check I²C Devices

```bash
# List I²C buses
i2cdetect -l

# Scan for devices on bus 1
i2cdetect -y 1

# Monitor I²C traffic (requires i2c-tools)
sudo i2cdump -y 1 0x40  # HTU21 at address 0x40
```

### Check 1-Wire Devices

```bash
ls /sys/bus/w1/devices/
```

### Common Issues

- Sensors not detected: verify I²C and 1-Wire interfaces are enabled (`raspi-config`), check wiring and power supply.
- MQTT not publishing: verify `mqtt.server` in `sensors.json`, check network connectivity and broker permissions.
- Run with `--dry` to confirm readings without publishing.

## Development

### Adding a New Sensor Type

1. Update sensor detection logic in `fetchsensors.py`
2. Add an example entry to `sensors.example.json`
3. Update this README

### Testing

Always test with `--dry` first, then verify MQTT messages are published correctly before deploying as a service.
