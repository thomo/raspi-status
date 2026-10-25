#!/bin/bash

# Set the target architecture for Raspberry Pi (ARM)
# GOARM=6 runs on every 32-bit Raspberry Pi OS, including ARMv6 boards
# (Pi 1, Zero, Zero W). Override with GOARM=7 for ARMv7-only builds.
export GOARCH=arm
export GOOS=linux
export GOARM="${GOARM:-6}"

# Build the Go program
go build -o sensorprobe_service ./src/
