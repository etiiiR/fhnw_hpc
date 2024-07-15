import json
import random
import time
from confluent_kafka import Producer

servers = 'localhost:19092,localhost:19093,localhost:19094'
topic = "bus_locations"

class BusLocationProducer:
    def __init__(self, server_list, bus_id):
        self.producer = Producer({'bootstrap.servers': server_list})
        self.bus_id = bus_id


    def generate_bus_location(self):
        # Simulate GPS coordinates for Basel area
        lat = random.uniform(47.540, 47.570)
        lon = random.uniform(7.570, 7.600)
        speed = random.uniform(30, 60)  # Speed in km/h
        return lat, lon, speed

    def send_location_data(self):
        lat, lon, speed = self.generate_bus_location()
        message = {
            "bus_id":random.choice([f'Bus{i}' for i in range(1, 200)]),
            "timestamp": time.time(),
            "location": {"lat": lat, "lon": lon},
            "speed": speed
        }
        self.producer.produce(topic, json.dumps(message).encode('utf-8'))
        print(f"Sent message: {message}, to topic: {topic}")
        self.producer.flush()

if __name__ == "__main__":
    for i in range(1, 6):  # Simulate 5 buses
        producer = BusLocationProducer(servers, f'Bus{i}')
        while True:
            producer.send_location_data()
            time.sleep(0.1)  # Send data every second
