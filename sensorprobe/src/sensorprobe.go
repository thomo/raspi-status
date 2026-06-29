package main

import (
    "fmt"
    "log"
    "time"

    "github.com/gookit/config/v2"
    "github.com/gookit/config/v2/properties"
    "github.com/d2r2/go-i2c"
    influxdb2 "github.com/influxdata/influxdb-client-go/v2"
)

type Config struct {
    InfluxURL   string `mapstructure:"influxURL"`
    InfluxToken string `mapstructure:"influxToken"`
    InfluxOrg   string `mapstructure:"influxOrg"`
    InfluxBucket string `mapstructure:"influxBucket"`
}

func loadConfig(filename string) (*Config, error) {
    config.WithOptions(config.ParseEnv)
    config.AddDriver(properties.Driver)

    if err := config.LoadFiles(filename); err != nil {
        return nil, err
    }

    var cfg Config
    if err := config.BindStruct("", &cfg); err != nil {
        return nil, err
    }

    return &cfg, nil
}

func readI2CSensor() (float64, error) {
    i2c, err := i2c.NewI2C(0x48, 1)
    if err != nil {
        return 0, err
    }
    defer i2c.Close()

    // Replace with actual sensor reading logic
    data, err := i2c.ReadBytes(2)
    if err != nil {
        return 0, err
    }

    // Convert data to a meaningful value
    value := float64(data[0]) + float64(data[1])/256.0
    return value, nil
}

func read1WireSensor() (float64, error) {
    // Replace with actual 1-Wire sensor reading logic
    value, err := dht.ReadDHTxxWithRetry(dht.DHT22, "GPIO_PIN", false, 10)
    if err != nil {
        return 0, err
    }
    return value, nil
}

func sendToInfluxDB(client influxdb2.Client, measurement string, value float64) error {
    writeAPI := client.WriteAPIBlocking(influxOrg, influxBucket)
    p := influxdb2.NewPoint(measurement,
        map[string]string{"unit": "value"},
        map[string]interface{}{"value": value},
        time.Now())
    return writeAPI.WritePoint(p)
}

func main() {
    config, err := loadConfig("config.properties")
    if err != nil {
        log.Fatalf("Error loading config: %v", err)
    }

    client := influxdb2.NewClient(influxURL, influxToken)
    defer client.Close()

    for {
        i2cValue, err := readI2CSensor()
        if err != nil {
            log.Printf("Error reading I2C sensor: %v", err)
        } else {
            err = sendToInfluxDB(client, "i2c_sensor", i2cValue)
            if err != nil {
                log.Printf("Error sending I2C data to InfluxDB: %v", err)
            }
        }

        oneWireValue, err := read1WireSensor()
        if err != nil {
            log.Printf("Error reading 1-Wire sensor: %v", err)
        } else {
            err = sendToInfluxDB(client, "1wire_sensor", oneWireValue)
            if err != nil {
                log.Printf("Error sending 1-Wire data to InfluxDB: %v", err)
            }
        }

        time.Sleep(20 * time.Second)
    }
}