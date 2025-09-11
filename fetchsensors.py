#!/usr/bin/env python

import os
import re
import time
import sys
import paho.mqtt.client as mqtt
import json
import smbus
import argparse
import subprocess
from pathlib import Path
from htu21 import HTU21

PAYLOAD = ("{},location={},node={},sensor={} value={:.2f}")
ERRLOAD = ("error,location={},node={},sensor={} type=\"{}\",value=\"{}\"")

SENSOR_SI7021 = 'Si7021'
SENSOR_HTU21 = 'HTU21'

isDryRun = False

def hasI2cSensor(sensors):
    for item in sensors:
        if item['i2c']:
            return True
    return False

def check_i2c_address(bus_num, addr):
    """Check if a device exists at the specified I2C address."""
    try:
        print(f"Checking I2C address 0x{addr:02x} on bus {bus_num}")
        # Use i2cdetect command instead of direct read
        result = subprocess.run(['i2cdetect', '-y', str(bus_num)], 
                             capture_output=True, text=True)
        lines = result.stdout.split('\n')
        # Parse i2cdetect output to check if address exists
        for line in lines[1:]:  # Skip header line
            if line:
                parts = line.split(':')
                if len(parts) > 1:
                    cells = parts[1].strip().split()
                    row_base = int(parts[0], 16) if parts[0].strip() else 0
                    for i, cell in enumerate(cells):
                        if cell != '--':
                            cell_addr = row_base + i
                            if cell_addr == addr:
                                return True
        return False
    except Exception as e:
        print(f"Failed to check address 0x{addr:02x} on bus {bus_num}: {str(e)}")
        return False

# Sensor type definitions
I2C_SENSORS = {
    "HTU21": {
        "address": 0x40,
        "name": "HTU21",
        "values": [
            {"measurand": "temperature", "correction": 0.0},
            {"measurand": "humidity", "correction": 0.0}
        ]
    },
    "SI7021": {
        "address": 0x40,
        "name": "SI7021",
        "values": [
            {"measurand": "temperature", "correction": 0.0},
            {"measurand": "humidity", "correction": 0.0}
        ]
    },
    "BME280": {
        "address": 0x76,  # Also check 0x77 as alternate address
        "alternate_address": 0x77,
        "name": "BME280",
        "values": [
            {"measurand": "temperature", "correction": 0.0},
            {"measurand": "humidity", "correction": 0.0},
            {"measurand": "pressure", "correction": 0.0}
        ]
    }
}

def create_sensor_config(sensor_type, bus_num, address, channel=None):
    """Create a configuration dictionary for a sensor."""
    sensor_info = I2C_SENSORS[sensor_type]
    config = {
        "id": address,
        "sensor": sensor_type,
        "enabled": 1,
        "values": sensor_info["values"].copy()
    }
    
    # Add channel if using multiplexer
    if channel is not None:
        config["channel"] = channel
        config["location"] = f"i2c_{bus_num}_ch{channel}"
    else:
        config["location"] = f"i2c_{bus_num}"
    
    return config

def detect_sensor_type(bus_num, address):
    """Detect the type of sensor at a given address."""
    if address == 0x40:  # Special handling for HTU21/SI7021 which share the same address
        print(f"Found device at address 0x40")
        try:
            bus = smbus.SMBus(bus_num)
            # Read the device ID to distinguish between HTU21 and SI7021
            # First, send the read ID command
            bus.write_i2c_block_data(0x40, 0xFA, [0x0F])
            time.sleep(0.1)
            # Read the ID
            data = bus.read_i2c_block_data(0x40, 0, 8)
            bus.close()
            
            # SI7021 and HTU21 have different ID patterns
            if data[0] == 0x15:  # SI7021 ID
                print(f"Detected SI7021 at address 0x40 on bus {bus_num}")
                return SENSOR_SI7021
            else:  # Default to HTU21 if ID doesn't match SI7021
                print(f"Detected HTU21 at address 0x40 on bus {bus_num}")
                return SENSOR_HTU21
        except Exception:
            # If we can't read the ID but we know a device exists, quietly default to HTU21
            print(f"Detected HTU21 at address 0x40 on bus {bus_num}")
            return SENSOR_HTU21
            
    # For other addresses, check against known sensor types
    for sensor_type, info in I2C_SENSORS.items():
        print(f"Checking if device at 0x{address:02x} is a {sensor_type}")
        if address == info["address"] or (
            "alternate_address" in info and address == info["alternate_address"]
        ):
            print(f"Detected {sensor_type} at address 0x{address:02x} on bus {bus_num}")
            return sensor_type
    return None

def scan_i2c_bus(bus_num, channel=None):
    """Scan an I2C bus or multiplexer channel for sensors."""
    sensors = []
    bus = None
    
    try:
        location_info = f"bus {bus_num}"
        if channel is not None:
            print(f"Scanning I2C bus {bus_num}, multiplexer channel {channel}")
            bus = smbus.SMBus(bus_num)
            try:
                bus.write_byte(0x70, 0)  # Reset all channels
                time.sleep(0.1)
                bus.write_byte(0x70, 1 << channel)  # Select channel
                time.sleep(0.1)
                location_info = f"bus {bus_num}, channel {channel}"
            except Exception as e:
                print(f"Error switching multiplexer to channel {channel}: {e}")
                if bus:
                    bus.close()
                return []
        else:
            print(f"Scanning I2C bus {bus_num} directly (no multiplexer)")
            
        # Get i2cdetect output
        result = subprocess.run(['i2cdetect', '-y', str(bus_num)], 
                             capture_output=True, text=True)
        
        # Parse output for known sensor addresses (0x40, 0x76, 0x77)
        known_addrs = {0x40, 0x76, 0x77}  # Set of addresses we care about
        found_addr = None
        
        for line in result.stdout.split('\n')[1:]:  # Skip header
            if not line or ':' not in line:
                continue
            row = line.split(':')[1].strip().split()
            row_base = int(line.split(':')[0], 16) if line.split(':')[0].strip() else 0
            
            # Check each cell in the row
            for i, cell in enumerate(row):
                if cell != '--' and cell != '':
                    addr = row_base + i
                    if addr in known_addrs:
                        found_addr = addr
                        break
            if found_addr:
                break
                
        # If we found a known address, try to identify the sensor
        if found_addr:
            sensor_type = detect_sensor_type(bus_num, found_addr)
            if sensor_type:
                sensor_config = create_sensor_config(sensor_type, bus_num, found_addr, channel)
                print(f"Found {sensor_type} on {location_info}")
                sensors.append(sensor_config)
            
    except Exception as e:
        print(f"Error scanning {location_info}: {e}", file=sys.stderr)
    
    return sensors

def detect_i2c_sensors():
    """Detect I2C sensors on all available busses, including multiplexed channels."""
    sensors = []
    
    try:
        # Check busses 0 and 1
        for bus_num in [0, 1]:
            try:
                # First check if there's an I2C multiplexer
                has_multiplexer = check_i2c_address(bus_num, 0x70)
                
                if has_multiplexer:
                    print(f"Found I2C multiplexer on bus {bus_num}")
                    # Check each channel (0-7) of the multiplexer
                    for channel in range(8):
                        sensors.extend(scan_i2c_bus(bus_num, channel))
                else:
                    # No multiplexer, just check for direct sensors
                    sensors.extend(scan_i2c_bus(bus_num))
                    
            except (OSError, IOError) as e:
                print(f"Error accessing bus {bus_num}: {e}", file=sys.stderr)
                continue
                
    except Exception as e:
        print(f"Error detecting I2C sensors: {e}", file=sys.stderr)
    
    return sensors

def detect_w1_sensors():
    """Detect 1-Wire temperature sensors."""
    sensors = []
    w1_devices = Path('/sys/bus/w1/devices')
    if w1_devices.exists():
        for device in w1_devices.glob('28-*'):  # 28- is the family code for DS18B20
            sensors.append({
                "id": device.name,
                "sensor": "DS18B20",
                "enabled": 1,
                "location": f"wire1_{device.name}",
                "values": [
                    {"correction": 0.0, "measurand": "temperature"}
                ]
            })
    return sensors

def generate_sensors_config():
    """Generate a sensors.json configuration file with all detected sensors."""
    config = {
        "mqtt": {
            "server": "localhost",
            "topic": "sensors/data"
        },
        "interval": 20,
        "node": os.uname().nodename,
        "sensors": []
    }
    
    # Detect all sensors
    config['sensors'].extend(detect_i2c_sensors())
    config['sensors'].extend(detect_w1_sensors())
    
    return config

def readDS18B20(sensor): 
    try:
        file = open('/sys/bus/w1/devices/'+sensor['id']+'/w1_slave')
        filecontent = file.read()
        file.close()
    
        if filecontent.split("\n")[0].strip()[-3:] != 'YES':
            sensor['error'] = { 'type': 'SensorValueInvalid', 'value': '???' }
        else:
            tp = filecontent.split("\n")[1].split(" ")[9]
            sensor['values'][0]['raw'] = float(tp[2:]) / 1000
            sensor['error'] = {}

            if sensor['values'][0]['raw'] > 120 or sensor['values'][0]['raw'] < -40:
                sensor['error'] = { 
                    'type': 'SensorValueInvalid_2', 
                    'value':  str(sensor['values'][0]['raw']) 
                }

    except FileNotFoundError: 
        sensor['error'] = { 'type': 'SensorNotFound', 'value': 'DS18B20 ' + sensor['id'] }
    except:
        exc_type, exc_value, _1 = sys.exc_info()
        sensor['error'] = { 'type': exc_type.__qualname__, 'value': exc_value }

def readSI7021(bus, sensor):
    i2caddr = sensor['id']

    try:
        if 'channel' in sensor:
            selectI2cChannel(bus, sensor['channel'])

        hm = bus.read_i2c_block_data(i2caddr, 0xE5, 2) 
        time.sleep(1.5)
        sensor['values'][1]['raw'] = ((hm[0] * 256 + hm[1]) * 125 / 65536.0) - 6
        
        tp = bus.read_i2c_block_data(i2caddr, 0xE3, 2)
        time.sleep(1.5)
        sensor['values'][0]['raw'] = ((tp[0] * 256 + tp[1]) * 175.72 / 65536.0) - 46.85

        sensor['error'] = {}

    except:
        exc_type, exc_value, _1 = sys.exc_info()
        sensor['error'] = { 'type': exc_type, 'value': exc_value }

def readHTU21(bus, sensor):
    try:
        if 'channel' in sensor:
            selectI2cChannel(bus, sensor['channel'])

        htu = HTU21()

        sensor['values'][0]['raw'] = htu.read_temperature()
        sensor['values'][1]['raw'] = htu.read_humidity()
        
        sensor['error'] = {}
    except:
        exc_type, exc_value, _1 = sys.exc_info()
        sensor['error'] = { 'type': exc_type, 'value': exc_value }

def selectI2cChannel(bus, channel): 
    bus.write_byte(0x70, 0b000000001 << channel )
    time.sleep(0.1)

def printErr(msg):
    print('ERROR - ' + msg, file=sys.stderr)

def keepEnabledSensors(sensors):
    return list(filter(lambda s: s['enabled'] == 1, sensors))

def refineSensorConfig(sensors):
    for s in sensors:
        s['i2c'] = ( s['sensor'] == SENSOR_SI7021 or s['sensor'] == SENSOR_HTU21 )
    return sensors

parser = argparse.ArgumentParser(description='Fetch and publish sensor values')
parser.add_argument('-c',    help='use config file, default is /etc/sensors.json', default='/etc/sensors.json', metavar='config_file')
parser.add_argument('--dry', help='dry run - do not publish values', action='store_true')
parser.add_argument('--generate', help='generate sensors.json with all detected sensors', action='store_true')
args = parser.parse_args()

is_dry_run = args.dry
config_file = args.c

if args.generate:
    config = generate_sensors_config()
    output_file = 'sensors.json'
    
    # Don't overwrite existing file without confirmation
    if os.path.exists(output_file):
        response = input(f"{output_file} already exists. Overwrite? [y/N] ").lower()
        if response != 'y':
            print("Aborted.")
            sys.exit(0)
    
    try:
        with open(output_file, 'w') as f:
            json.dump(config, f, indent=4)
        print(f"Generated {output_file} with {len(config['sensors'])} detected sensors")
        print("Review and edit the file to adjust locations and corrections as needed")
        sys.exit(0)
    except Exception as e:
        printErr(f"Failed to write {output_file}: {e}")
        sys.exit(1)

try:
    with open(config_file) as f:
        config = json.load(f)
        sensors = refineSensorConfig(keepEnabledSensors(config['sensors']))
except FileNotFoundError:
    printErr('config file "' + config_file + '" not found!')
    exit()
except json.decoder.JSONDecodeError as e:
    printErr('syntax error in config file "' + config_file + '": ' + str(e))
    exit()
except:
    printErr('error while reading config file "' + config_file + '": ' + str(sys.exc_info()[1]))
    exit()

if not is_dry_run:
    client = mqtt.Client()

    # Set access token
    # client.username_pw_set(ACCESS_TOKEN)

    # Connect default MQTT port and 60 seconds keepalive interval
    client.connect(config['mqtt']['server'], 1883, 60)
    client.loop_start()

if hasI2cSensor(sensors): 
    i2cbus = smbus.SMBus(1)
    time.sleep(2)

try:
    next_reading = time.time() 

    while True:
        for item in sensors:
            if item['sensor'] == 'DS18B20':
                readDS18B20(item) 
            elif item['sensor'] == SENSOR_SI7021:
                readSI7021(i2cbus, item)
            elif item['sensor'] == SENSOR_HTU21:
                readHTU21(i2cbus, item)
            else:
                # ignore
                pass

            if not item['error']:
                for v in item['values']:
                    msg = PAYLOAD.format(v['measurand'],item['location'],config['node'],item['sensor'],v['raw']+v['correction'])
                    print(msg)
                    if not is_dry_run:
                        client.publish(config['mqtt']['topic'], msg)
            else:
                err_msg = ERRLOAD.format(item['location'],config['node'],item['sensor'],item['error']['type'],item['error']['value'])
                print(err_msg, file=sys.stderr)
                if not is_dry_run:
                    client.publish(config['mqtt']['topic'], err_msg)

        next_reading += config['interval']
        sleep_time = next_reading - time.time()
        if sleep_time > 0:
            time.sleep(sleep_time)
except KeyboardInterrupt:
    pass

if not is_dry_run:
    client.loop_stop()
    client.disconnect()