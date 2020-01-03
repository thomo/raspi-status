#!/usr/bin/python3 -u

# Copyright (c) 2017 Adafruit Industries
# Author: Tony DiCola & James DeVito
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import time
import Adafruit_SSD1306
import subprocess

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
from pytz import timezone
from dateutil.parser import parse

# Raspberry Pi pin configuration:
RST = None     # on the PiOLED this pin isnt used
# Note the following are only used with SPI:
DC = 23
SPI_PORT = 0
SPI_DEVICE = 0

def draw_center(d, y, msg):
    w, _1 = d.textsize(msg)
    d.text(((128-w)/2, y), msg, font=font, fill=255)

def draw_celsius(d, x, y):
    d.ellipse((x, y+2, x+3, y+2+3), outline=255, fill=0)
    d.text((x+5, y), "C",  font=font, fill=255)


# 128x64 display with hardware I2C:
disp = Adafruit_SSD1306.SSD1306_128_64(rst=RST)

disp.begin()

disp.clear()
disp.display()

# Create blank image for drawing.
# Make sure to create image with mode '1' for 1-bit color.
width = disp.width
height = disp.height
image = Image.new('1', (width, height))

# Get drawing object to draw on image.
draw = ImageDraw.Draw(image)

# Draw a black filled box to clear the image.
draw.rectangle((0,0,width,height), outline=0, fill=0)

# Draw some shapes.
# First define some constants to allow easy resizing of shapes.
padding = 0
top = padding
lineheight = 12
bottom = height-padding
# Move left to right keeping track of the current x position for drawing shapes.
x = 0

# Load default font.
font = ImageFont.load_default()

while True:

    # Draw a black filled box to clear the image.
    draw.rectangle((0,0,width,height), outline=0, fill=0)

    # Shell scripts for system monitoring from here : https://unix.stackexchange.com/questions/119126/command-to-display-memory-usage-disk-usage-and-cpu-load
    # cmd = "hostname -I | cut -d\' \' -f1"
    # IP = subprocess.run(cmd, shell = True, encoding = 'UTF-8', capture_output=True ).stdout
    cmd = "top -bn1 | grep load | awk '{printf \"C: %.2f\", $(NF-2)}'"
    CPU = subprocess.run(cmd, shell = True, encoding = 'UTF-8', capture_output=True ).stdout
    cmd = "free -m | awk 'NR==2{printf \"M: %.0f%%\", $3*100/$2 }'"
    MemUsage = subprocess.run(cmd, shell = True, encoding = 'UTF-8', capture_output=True ).stdout
    cmd = "df -h | awk '$NF==\"/\"{printf \"D: %s\", $5}'"
    Disk = subprocess.run(cmd, shell = True, encoding = 'UTF-8', capture_output=True ).stdout

    cmd = "uptime| sed -E 's/^[^,]*up *//; s/, *[[:digit:]]* users?.*//; s/days/d/; s/ ?([[:digit:]]+):0?([[:digit:]]+)/\\1 h, \\2 m/'"
    Up = subprocess.run(cmd, shell = True, encoding = 'UTF-8', capture_output=True ).stdout

    cmd = "grep 'temperature,location=ttnbox' /var/log/sensors.log | tail -1 | awk -F= '{printf \"%.1f\", $NF}'| tr -d '\n'"
    T_in = subprocess.run(cmd, shell = True, encoding = 'UTF-8', capture_output=True ).stdout
    cmd = "grep 'temperature,location=attic' /var/log/sensors.log | tail -1 | awk -F= '{printf \"%.1f\", $NF}'| tr -d '\n'"
    T_out = subprocess.run(cmd, shell = True, encoding = 'UTF-8', capture_output=True ).stdout

    cmd = "curl -s http://noc.thethingsnetwork.org:8085/api/v2/gateways/eui-b827ebfffe06902a | jq -r '.timestamp'"
    TTNts = parse(subprocess.run(cmd, shell = True, encoding = 'UTF-8', capture_output=True ).stdout)
    TTNts = TTNts.astimezone(timezone('Europe/Berlin'))

    # Write text
    y = top
    draw_center(draw, y, "Up: " + str(Up))
    # y += lineheight
    # draw.text((x, y), "IP: " + str(IP),  font=font, fill=255)
    y += lineheight
    draw.text((x, y), str(CPU) + " " + str(MemUsage) + " " + str(Disk), font=font, fill=255)
    
    y += lineheight
    msg = "In:" + str(T_in)
    w, _1 = draw.textsize(msg)
    draw.text((x, y), msg,  font=font, fill=255)
    draw_celsius(draw, x+1+w, y)
    msg = "Out:" + str(T_out)
    w, _1 = draw.textsize(msg)
    draw.text((64, y), msg,  font=font, fill=255)
    draw_celsius(draw, 64+1+w, y)

    y += lineheight + 3
    draw_center(draw, y, "TTN-GW last seen")
    y += lineheight
    draw_center(draw, y, str(TTNts.strftime("%Y-%m-%d %I:%M:%S")))

    # Display image
    disp.image(image)
    disp.display()
    time.sleep(0.1)