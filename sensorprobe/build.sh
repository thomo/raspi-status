#!/bin/bash

# Set the target architecture for Raspberry Pi (ARM)
export GOARCH=arm
export GOOS=linux
export GOARM=7

# Build the Go program
go build -o sensorprobe_service ./src/