import json
import random
import time
import zmq

class BusLocationProducerZMQ:
    def __init__(self, endpoint):
        self.context = zmq.Context()
        self.publisher = self.context.socket(zmq.PUB)
        self.publisher.bind(endpoint)

    def generate_bus_location(self, bus_id):
        lat = random.uniform(47.540, 47.570)
        lon = random.uniform(7.570, 7.600)
        speed = random.uniform(30, 60)  # Speed in km/h
        return lat, lon, speed

    def send_location_data(self, bus_id):
        lat, lon, speed = self.generate_bus_location(bus_id)
        message = {
            "bus_id": bus_id,
            "timestamp": time.time(),
            "location": {"lat": lat, "lon": lon},
            "speed": speed
        }
        print(f"Sent message: {message}")
        self.publisher.send_string(json.dumps(message))

if __name__ == "__main__":
    print('started')
    endpoint = "tcp://*:5556"
    bus_ids = [f'Bus{i}' for i in range(1, 6)]
    producer = BusLocationProducerZMQ(endpoint, )
    
    while True:
        for bus_id in bus_ids:
            producer.send_location_data(bus_id)
        time.sleep(1)
