package main

import (
	"context"
	"log"
	"time"

	goi2c "github.com/d2r2/go-i2c"
	"github.com/gookit/config/v2"
	"github.com/gookit/config/v2/properties"
	influxdb2 "github.com/influxdata/influxdb-client-go/v2"
)

type Config struct {
	InfluxURL    string `mapstructure:"influxURL"`
	InfluxToken  string `mapstructure:"influxToken"`
	InfluxOrg    string `mapstructure:"influxOrg"`
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
	conn, err := goi2c.NewI2C(0x48, 1)
	if err != nil {
		return 0, err
	}
	defer conn.Close()

	// Replace with actual sensor reading logic
	buf := make([]byte, 2)
	_, err = conn.ReadBytes(buf)
	if err != nil {
		return 0, err
	}

	value := float64(buf[0]) + float64(buf[1])/256.0
	return value, nil
}

func read1WireSensor() (float64, error) {
	// Replace with actual 1-Wire sensor reading logic
	return 0, nil
}

func sendToInfluxDB(client influxdb2.Client, cfg *Config, measurement string, value float64) error {
	writeAPI := client.WriteAPIBlocking(cfg.InfluxOrg, cfg.InfluxBucket)
	p := influxdb2.NewPoint(measurement,
		map[string]string{"unit": "value"},
		map[string]interface{}{"value": value},
		time.Now())
	return writeAPI.WritePoint(context.Background(), p)
}

func main() {
	cfg, err := loadConfig("config.properties")
	if err != nil {
		log.Fatalf("Error loading config: %v", err)
	}

	client := influxdb2.NewClient(cfg.InfluxURL, cfg.InfluxToken)
	defer client.Close()

	for {
		i2cValue, err := readI2CSensor()
		if err != nil {
			log.Printf("Error reading I2C sensor: %v", err)
		} else {
			if err = sendToInfluxDB(client, cfg, "i2c_sensor", i2cValue); err != nil {
				log.Printf("Error sending I2C data to InfluxDB: %v", err)
			}
		}

		oneWireValue, err := read1WireSensor()
		if err != nil {
			log.Printf("Error reading 1-Wire sensor: %v", err)
		} else {
			if err = sendToInfluxDB(client, cfg, "1wire_sensor", oneWireValue); err != nil {
				log.Printf("Error sending 1-Wire data to InfluxDB: %v", err)
			}
		}

		time.Sleep(20 * time.Second)
	}
}
