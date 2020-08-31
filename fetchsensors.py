#!/usr/bin/env python3

import os
import re
import time
import sys
import paho.mqtt.client as mqtt
import json
import smbus
import argparse
import board
import busio
import adafruit_si7021

PAYLOAD = ("{},location={},node={},sensor={} value={:.2f}")
ERRLOAD = ("error,location={},node={},sensor={} type=\"{}\",value=\"{}\"")

SI7021 = 'Si7021'

isDryRun = False

def hasI2cSensor(sensors):
    for item in sensors:
        if item['i2c']:
            return True
    return False

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

    try:
        if 'channel' in sensor:
            selectI2cChannel(bus, sensor['channel'])

        sensor['values'][1]['raw'] = si7021sensor.relative_humidity
        sensor['values'][0]['raw'] = si7021sensor.temperature
        sensor['error'] = {}

    except:
        exc_type, exc_value, _1 = sys.exc_info()
        sensor['error'] = { 'type': exc_type.__qualname__, 'value': exc_value }

def selectI2cChannel(bus, channel): 
    print('select channel')
    bus.write_byte(0x70, 0b000000001 << channel )
    time.sleep(0.1)

def printErr(msg):
    print('ERROR - ' + msg, file=sys.stderr)

def keepEnabledSensors(sensors):
    return list(filter(lambda s: s['enabled'] == 1, sensors))

def refineSensorConfig(sensors):
    for s in sensors:
        s['i2c'] = s['sensor'] == SI7021
    return sensors

parser = argparse.ArgumentParser(description='Fetch and publish sensor values')
parser.add_argument('-c',    help='use config file, default is /etc/sensors.json', default='/etc/sensors.json', metavar='config_file')
parser.add_argument('--dry', help='dry run - do not publish values', action='store_true')
args = parser.parse_args()

is_dry_run = args.dry
config_file = args.c

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
    si7021sensor = adafruit_si7021.SI7021(busio.I2C(board.SCL, board.SDA))

try:
    next_reading = time.time() 

    while True:
        for item in sensors:
            if item['sensor'] == 'DS18B20':
                readDS18B20(item) 
            elif item['sensor'] == SI7021:
                readSI7021(i2cbus, item)
            else:
                # ignore
                pass

            if not item['error']:
                for v in item['values']:
                    msg = PAYLOAD.format(v['measurand'],item['location'],config['node'],item['sensor'],v['raw']+v['correction'])
                    print(msg, flush=True)
                    if not is_dry_run:
                        client.publish(config['mqtt']['topic'], msg)
            else:
                err_msg = ERRLOAD.format(item['location'],config['node'],item['sensor'],item['error']['type'],item['error']['value'])
                print(err_msg, file=sys.stderr, flush=True)
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