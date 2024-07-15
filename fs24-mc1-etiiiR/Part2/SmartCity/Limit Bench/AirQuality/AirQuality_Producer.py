import json
import random
import os
import time
from confluent_kafka import Producer


class AirQualityProducer:
    def __init__(self, servers):
        self.producer = Producer({'bootstrap.servers': servers})
    
    def delivery_report(self, err, msg):
        if err is not None:
            print(f'Message delivery failed: {err}')
        else:
            print(f'Message delivered to {msg.topic()} [{msg.partition()}]')

    def send_air_quality_data(self, topic="air_quality_data"):
        locations = ['CityCenter', 'Suburb', 'IndustrialArea', 'Park']
        while True:
            for _ in range(10):  # Send 10 messages per second
                message = {
                    "location": random.choice(locations),
                    "pm2_5": random.uniform(5, 100),  # Particulate matter 2.5
                    "pm10": random.uniform(10, 150),  # Particulate matter 10
                    "no2": random.uniform(0, 50),  # Nitrogen Dioxide
                    "timestamp": time.time(),
                    "co2": 400 + (time.time() / 31536000) * 10,  # co2 that is rising with 10% per year
                    "temperature": random.uniform(-10, 40),  # Temperature in Celsius
                    "humidity": random.uniform(0, 100),  # Humidity in %
                    "pressure": random.uniform(950, 1050),  # Atmospheric pressure in hPa
                    "o3": random.uniform(0, 10),  # Ozone
                    "so2": random.uniform(0, 20),  # Sulphur Dioxide
                    "wind_speed": random.uniform(0, 100)  # Wind speed in km/h
                }
                message_bytes = json.dumps(message).encode('utf-8')
                self.producer.produce(topic, message_bytes, callback=self.delivery_report)
                self.producer.poll(1)
            time.sleep(1)
            self.producer.flush()


if __name__ == '__main__':
    servers = 'kafka1:9092,kafka2:9092,kafka3:9092'
    print(os.environ.get('KAFKA_SERVER'))
    if (os.environ.get('KAFKA_SERVER') is not None):
        servers = os.environ.get('KAFKA_SERVER', "smartstation_producer")
    else:
        servers = 'localhost:19092,localhost:19093,localhost:19094'
    air_quality_producer = AirQualityProducer(servers)
    air_quality_producer.send_air_quality_data()
    
