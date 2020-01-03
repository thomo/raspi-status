#!/usr/bin/env python3

import os
import re
import time
import sys
import paho.mqtt.client as mqtt
import json
import smbus

MQTT_SERVER = 'mqtt.thomo.de'

# Data capture and upload interval in seconds. Less interval will eventually hang the DHT22.
INTERVAL = 20

TOPIC = 'tmp'
PAYLOAD = ("{},location={},node={},sensor={} value={:.2f}")
ERRLOAD = ("error,location={},node={},sensor={} type={},value={}")

sensors = (
    { 
        'id': '28-0301a279dec6', 
        'sensor': 'DS18B20', 
        'node': 'ttn-gateway', 
        'location': 'ttnbox', 
        'values': [ 
            { 'correction': -1.1, 'measurand': 'temperature', 'raw': 0.0},
        ], 
        'error': {},
    }, 
    {
        'id': '28-0301a2794002', 
        'sensor': 'DS18B20', 
        'node': 'ttn-gateway', 
        'location': 'attic', 
        'values': [ 
            { 'correction': -0.2, 'measurand': 'temperature', 'raw': 0.0},
        ],
        'error': {},
    },
    {
        'id': 0x40, 
        'sensor': 'Si7021', 
        'node': 'ttn-gateway', 
        'location': 'attic', 
        'values': [ 
            { 'correction': -1.2, 'measurand': 'temperature', 'raw': 0.0},
            { 'correction': 7.0, 'measurand': 'humidity', 'raw': 0.0}, 
        ],
        'error': {},
    }
)

def readDS18B20(sensor): 
    try:
        file = open('/sys/bus/w1/devices/'+sensor['id']+'/w1_slave')
        filecontent = file.read()
        file.close()
    
        tp = filecontent.split("\n")[1].split(" ")[9]
        sensor['values'][0]['raw'] = float(tp[2:]) / 1000

        sensor['error'] = {}
    except:
        exc_type, exc_value, _1 = sys.exc_info()
        sensor['error'] = { 'type': exc_type, 'value': exc_value }

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
        sensor['error'] = { 'type': exc_type, 'value': exc_value }

next_reading = time.time() 

client = mqtt.Client()

# Set access token
# client.username_pw_set(ACCESS_TOKEN)

# Connect to ThingsBoard using default MQTT port and 60 seconds keepalive interval
client.connect(MQTT_SERVER, 1883, 60)

client.loop_start()

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
                    # pass
                    print(PAYLOAD.format(v['measurand'],item['location'],item['node'],item['sensor'],v['raw']+v['correction']))
                    client.publish(TOPIC, PAYLOAD.format(v['measurand'],item['location'],item['node'],item['sensor'],v['raw']+v['correction']))
            else:
                print(ERRLOAD.format(item['location'],item['node'],item['sensor'],item['error']['type'],item['error']['value']), file=sys.stderr)
                client.publish(TOPIC, ERRLOAD.format(item['location'],item['node'],item['sensor'],item['error']['type'],item['error']['value']))

        next_reading += INTERVAL
        sleep_time = next_reading-time.time()
        if sleep_time > 0:
            time.sleep(sleep_time)
except KeyboardInterrupt:
    pass


client.loop_stop()
client.disconnect()