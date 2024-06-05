import os
import time
import json
import struct
import socket
import schedule
from dotenv import load_dotenv
from pymodbus.client import ModbusTcpClient
from kafka import KafkaProducer
from datetime import datetime

load_dotenv()

# Configuration
URL_MODBUS = os.getenv("URL_MODBUS")
KFK_BROKER = os.getenv("KFK_BROKER")
KFK_TOPIC = os.getenv("KFK_TOPIC")
DEV_CONFIG = os.getenv("DEV_CONFIG")


class SensorConfig:
    def __init__(self, port, type, sn, chart, divisor=None, cutmax=None, note=None):
        self.port = port
        self.typ = type
        self.divisor = divisor
        self.sn = sn
        self.chart = chart
        self.cutmax = cutmax
        self.note = note


def is_server_available(server):
    try:
        host, port = server.split(':')
        with socket.create_connection((host, int(port)), timeout=2):
            pass
    except Exception as e:
        print(f"Error: {server} server is not available", e)
        return False
    return True


def read_sensor_config():
    try:
        with open(DEV_CONFIG, 'r') as file:
            data = json.load(file)
            sensors = [SensorConfig(**item) for item in data]
            return sensors
    except Exception as e:
        print(f"Error reading sensor configurations: {e}")
        return []


def bytes_to_float32(high, low):
    return struct.unpack('<f', struct.pack('<HH', high, low))[0]


def read_modbus_and_process(client, sensors, producer):
    message = []
    for sensor in sensors:
        try:
            # Read Modbus data based on sensor type
            if sensor.typ == "f":
                result = client.read_holding_registers(sensor.port, 2)
            elif sensor.typ == "i":
                result = client.read_holding_registers(sensor.port, 1)
            elif sensor.typ in {"l", "r"}:
                result = client.read_holding_registers(sensor.port, 2)
            else:
                continue

            # Process the obtained data
            if not result.isError():
                if sensor.typ == "f" or sensor.typ in {"l", "r"}:
                    value = bytes_to_float32(result.registers[0], result.registers[1])
                elif sensor.typ == "i":
                    value = result.registers[0]
            else:
                value = None

            if value is not None and (sensor.divisor is not None and sensor.divisor != 0):
                value = value / sensor.divisor

            # Send the processed data to Kafka
            current_time = datetime.now()
            if value <= 0:
                data = None
            else:
                data = {
                    "at": current_time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "sensor": sensor.sn,
                    "chart": sensor.chart,
                    "value": value
                }
            message.append(data)
            print(f"REGISTRY: {sensor.port}, SENSOR: {data['sensor']}, VALUE: {data['value']}, DATETIME: {data['at']}")
        except Exception as e:
            print(f"Error reading Modbus and processing data: {e}")
    producer.send(KFK_TOPIC, json.dumps(message).encode('utf-8'))


def process_data(sensors, producer):
    modbus_available = is_server_available(URL_MODBUS)
    kafka_available = is_server_available(KFK_BROKER)

    if modbus_available and kafka_available:
        adr, port = URL_MODBUS.split(':')
        with ModbusTcpClient(host=adr, port=port) as modbus_client:
            try:
                read_modbus_and_process(modbus_client, sensors, producer)
            except Exception as e:
                print(f"Error {e}")
    else:
        print("Either Modbus or Kafka is not available.")


def main():
    sensors = read_sensor_config()
    producer = KafkaProducer(bootstrap_servers=KFK_BROKER, retries=5)

    # Schedule the 'process_data' function to run every second
    schedule.every(1).seconds.do(process_data, sensors, producer)

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()
