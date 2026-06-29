#!/usr/bin/env python

import sys
import time
import subprocess
import board
import busio
import adafruit_ssd1306

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
from pytz import timezone
from dateutil.parser import parse

def check_required_tools():
    """Check if required command line tools are available."""
    try:
        subprocess.run(['jq', '--version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: 'jq' command not found. Please install it using:", file=sys.stderr)
        print("  sudo apt-get install jq", file=sys.stderr)
        sys.exit(1)

# Check for required tools before starting
check_required_tools()

# Create the I2C interface
i2c = busio.I2C(board.SCL, board.SDA)

# Create the SSD1306 OLED display
# Most displays are 128x64 or 128x32
disp = adafruit_ssd1306.SSD1306_I2C(128, 64, i2c)

def draw_text(d, x, y, msg):
    d.text((x, y), msg, font=font, fill=255)

def draw_center(d, y, msg):
    # Split text into lines and handle each line separately
    lines = str(msg).splitlines()
    if not lines:  # Handle empty string case
        lines = ['']
    for line in lines:
        w = d.textlength(line, font=font)
        d.text(((128-w)/2, y), line, font=font, fill=255)
        # Get line height from bbox
        bbox = font.getbbox(line)
        line_height = bbox[3] - bbox[1]  # bottom - top
        y += line_height  # Move to next line

def draw_celsius(d, x, y):
    d.ellipse((x, y+2, x+3, y+2+3), outline=255, fill=0)
    d.text((x+5, y), "C",  font=font, fill=255)

# Clear the display
disp.fill(0)
disp.show()

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
    try:
        # Draw a black filled box to clear the image.
        draw.rectangle((0,0,width,height), outline=0, fill=0)

        # Shell scripts for system monitoring from here : https://unix.stackexchange.com/questions/119126/command-to-display-memory-usage-disk-usage-and-cpu-load
        # cmd = "hostname -I | cut -d\' \' -f1"
        # IP = subprocess.run(cmd, shell = True, encoding = 'UTF-8', capture_output=True ).stdout
        cmd = "top -bn1 | grep load | awk '{printf \"C: %.2f\", $(NF-2)}'"
        Cpu = subprocess.run(cmd, shell = True, encoding = 'UTF-8', capture_output=True ).stdout
        
        cmd = "free -m | awk 'NR==2{printf \"M: %.0f%%\", $3*100/$2 }'"
        MemUsage = subprocess.run(cmd, shell = True, encoding = 'UTF-8', capture_output=True ).stdout
        
        cmd = "df -h | awk '$NF==\"/\"{printf \"D: %s\", $5}'"
        Disk = subprocess.run(cmd, shell = True, encoding = 'UTF-8', capture_output=True ).stdout

        cmd = "uptime| sed -E 's/^[^,]*up *//; s/, *[[:digit:]]* users?.*//; s/days/d/; s/ ?([[:digit:]]+):0?([[:digit:]]+)/\\1 h, \\2 m/'"
        Up = subprocess.run(cmd, shell = True, encoding = 'UTF-8', capture_output=True ).stdout

        cmd = "journalctl --since '-60sec' -t python | grep -a 'temperature,location=ttnbox' | tail -1 | awk -F= '{printf \"%.1f\", $NF}'| tr -d '\n'"
        T_in = subprocess.run(cmd, shell = True, encoding = 'UTF-8', capture_output=True ).stdout
        
        cmd = "journalctl --since '-60sec' -t python | grep -a 'temperature,location=attic' | tail -1 | awk -F= '{printf \"%.1f\", $NF}'| tr -d '\n'"
        T_out = subprocess.run(cmd, shell = True, encoding = 'UTF-8', capture_output=True ).stdout

        cmd = "curl -s https://mapper.packetbroker.net/api/v2/gateways/netID=000013,tenantID=ttn,id=eui-b827ebfffe06902a | jq -r '.updatedAt'"
        TTNts = parse(subprocess.run(cmd, shell = True, encoding = 'UTF-8', capture_output=True ).stdout)
        TTNts = TTNts.astimezone(timezone('Europe/Berlin'))

        # Write text
        y = top
        draw_center(draw, y, "Up: " + str(Up))
        
        y += lineheight + 3
        msg = str(Cpu) + " " + str(MemUsage) + " " + str(Disk)
        dw = max(0, (128 - draw.textlength(msg, font=font)) / 2)
        draw_text(draw, x + dw, y, msg)
        
        y += lineheight
        msg = "In:" + str(T_in).strip()
        w = draw.textlength(msg, font=font)
        draw_text(draw, x, y, msg)
        draw_celsius(draw, x+1+w, y)
        msg = "Out:" + str(T_out).strip()
        w = draw.textlength(msg, font=font)
        draw_text(draw, 64, y, msg)
        draw_celsius(draw, 64+1+w, y)

        y += lineheight + 3
        draw_center(draw, y, "TTN-GW last seen")
        y += lineheight
        draw_center(draw, y, str(TTNts.strftime("%Y-%m-%d %H:%M:%S")))

        # Display image
        disp.image(image)
        disp.show()
        
        time.sleep(1.0)
    except KeyboardInterrupt:
        print("\nExiting gracefully...", file=sys.stderr, flush=True)
        # Clear the display before exiting
        disp.fill(0)
        disp.show()
        sys.exit(0)
    except:
        print(sys.exc_info(), file=sys.stderr, flush=True)
