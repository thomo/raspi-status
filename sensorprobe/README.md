# sensorprobe
## Build the Program Inside the Devcontainer

Open the project in VS Code and reopen it in the devcontainer.
Run the build script inside the devcontainer terminal:

```shell
./build.sh
```

This will produce a binary named sensorprobe_service that is compatible with the Raspberry Pi.
It is a static 32-bit ARMv7 binary, which runs on a Pi 3 or 4 with either 32-bit or
64-bit Raspberry Pi OS. For a native 64-bit build use
`GOOS=linux GOARCH=arm64 go build -o sensorprobe_service ./src/`.

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
