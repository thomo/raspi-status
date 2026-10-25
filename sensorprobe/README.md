# sensorprobe
## Build the Program Inside the Devcontainer

Open the project in VS Code and reopen it in the devcontainer.
Run the build script inside the devcontainer terminal:

```shell
./build.sh
```

This will produce a binary named sensorprobe_service that is compatible with the Raspberry Pi.
It is built for ARMv6 (`GOARM=6`) by default, so it runs on every 32-bit Raspberry Pi OS,
including ARMv6 boards such as the Pi 1 Model B+ and Pi Zero. Use `GOARM=7 ./build.sh`
only if the binary will never run on an ARMv6 board.

## Deploy the Binary to the Raspberry Pi
Copy the binary to your Raspberry Pi and set up the systemd service as described previously.

```shell
scp sensorprobe_service pi@raspberrypi:/usr/local/bin/
```

On the Raspberry Pi, enable and start the service:

```shell
sudo systemctl enable sensorprobe_service
sudo systemctl start sensorprobe_service
```
