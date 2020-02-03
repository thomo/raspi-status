#!/usr/bin/env python3

import os
import re
import time
import sys
import paho.mqtt.client as mqtt
import json
import smbus
import argparse

PAYLOAD = ("{},location={},node={},sensor={} value={:.2f}")
ERRLOAD = ("error,location={},node={},sensor={} type=\"{}\",value=\"{}\"")

isDryRun = False

def hasI2cSensor(sensors):
    for item in sensors:
        if item['sensor'] == 'Si7021':
            return True
    return False

def readDS18B20(sensor): 
    try:
        file = open('/sys/bus/w1/devices/'+sensor['id']+'/w1_slave')
        filecontent = file.read()
        file.close()
    
        tp = filecontent.split("\n")[1].split(" ")[9]
        sensor['values'][0]['raw'] = float(tp[2:]) / 1000
        sensor['error'] = {}

        if sensor['values'][0]['raw'] > 120 or sensor['values'][0]['raw'] < -40:
            sensor['error'] = { 'type': 'SensorValueInvalid', 'value':  str(sensor['values'][0]['raw']) }

    except FileNotFoundError: 
        sensor['error'] = { 'type': 'SensorNotFound', 'value': 'DS18B20 ' + sensor['id'] }
    except:
        exc_type, exc_value, _1 = sys.exc_info()
        sensor['error'] = { 'type': exc_type.__qualname__, 'value': exc_value }

def readSI7021(bus, sensor):
    i2caddr = sensor['id']

    try:
        hm = bus.read_i2c_block_data(i2caddr, 0xE5, 2) 
        time.sleep(0.1)
        sensor['values'][1]['raw'] = ((hm[0] * 256 + hm[1]) * 125 / 65536.0) - 6

        tp = bus.read_i2c_block_data(i2caddr, 0xE3, 2)
        time.sleep(0.1)
        sensor['values'][0]['raw'] = ((tp[0] * 256 + tp[1]) * 175.72 / 65536.0) - 46.85

        sensor['error'] = {}
    except:
        exc_type, exc_value, _1 = sys.exc_info()
        sensor['error'] = { 'type': exc_type.__qualname__, 'value': exc_value }

def printErr(msg):
    print('ERROR - ' + msg, file=sys.stderr)

parser = argparse.ArgumentParser(description='Fetch and publish sensor values')
parser.add_argument('-c', help='use config file, default is /etc/sensors.json', default='/etc/sensors.json', metavar='config_file')
parser.add_argument('--dry', action='store_true', help='dry run - do not publish values')
args = parser.parse_args()

is_dry_run = args.dry
config_file = args.c

next_reading = time.time() 

try:
    with open(config_file) as f:
        config = json.load(f)
        sensors = config['sensors']
except FileNotFoundError:
    printErr('config file "' + config_file + '" not found!')
    exit()
except json.decoder.JSONDecodeError as e:
    printErr('syntax error in config file: ' + str(e))
    exit()
except:
    printErr('Unexpected error while reading config file "' + config_file + '": ' + str(sys.exc_info()[1]))
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

try:
    while True:
        for item in sensors:
            if item['sensor'] == 'DS18B20':
                readDS18B20(item) 
            elif item['sensor'] == 'Si7021':
                readSI7021(i2cbus, item)
            else:
                # ignore
                pass

            if not item['error']:
                for v in item['values']:
                    print(PAYLOAD.format(v['measurand'],item['location'],config['node'],item['sensor'],v['raw']+v['correction']), flush=True)
                    if not is_dry_run:
                        client.publish(config['mqtt']['topic'], PAYLOAD.format(v['measurand'],item['location'],config['node'],item['sensor'],v['raw']+v['correction']))
            else:
                print(ERRLOAD.format(item['location'],config['node'],item['sensor'],item['error']['type'],item['error']['value']), file=sys.stderr, flush=True)
                if not is_dry_run:
                    client.publish(config['mqtt']['topic'], ERRLOAD.format(item['location'],config['node'],item['sensor'],item['error']['type'],item['error']['value']))

        next_reading += config['interval']
        sleep_time = next_reading-time.time()
        if sleep_time > 0:
            time.sleep(sleep_time)
except KeyboardInterrupt:
    pass

if not is_dry_run:
    client.loop_stop()
    client.disconnect()