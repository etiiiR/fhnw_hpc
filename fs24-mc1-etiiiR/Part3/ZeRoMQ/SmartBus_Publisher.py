import zmq
import json
import random
import time
import math

def generate_random_gps(lat, lon, radius):
    radius_in_degrees = radius / 111300
    u = random.uniform(0, 1)
    v = random.uniform(0, 1)
    w = radius_in_degrees * math.sqrt(u)
    t = 2 * math.pi * v
    x = w * math.cos(t)
    y = w * math.sin(t)
    new_lat = x + lat
    new_lon = y / math.cos(lat) + lon
    return new_lat, new_lon

context = zmq.Context()
socket = context.socket(zmq.PUB)
socket.bind("tcp://*:5556")

basel_lat, basel_lon = 47.5596, 7.5886  # GPS coordinates for Basel, Switzerland
bus_ids = ['Bus1', 'Bus2', 'Bus3', 'Bus4', 'Bus5', 'Bus6', 'Bus7', 'Bus8', 'Bus9', 'Bus10', 'Bus11', 'Bus12', 'Bus13', 'Bus14', 'Bus15', 'Bus16', 'Bus17', 'Bus18', 'Bus19', 'Bus20']
bus_types = ['conventional', 'electric']

while True:
    for _ in range(10):  # Send 10 messages per second
        bus_capacity = random.randint(30, 60)
        people_in_bus = random.randint(0, bus_capacity)
        lat, lon = generate_random_gps(basel_lat, basel_lon, 20000)
        bus_type = random.choice(bus_types)
        driving_time = random.uniform(0, 24)
        message = {
            "bus_id": random.choice(bus_ids),
            "bus_type": bus_type,
            "location": {"lat": lat, "lon": lon},
            "bus_capacity": bus_capacity,
            "people_in_bus": people_in_bus,
            "driving_time": driving_time,
            "driving_speed": random.uniform(0, 100),
            "engine_temperature": random.uniform(60, 120),
            "timestamp": time.time()
        }
        print(message)
        socket.send_string(f"BusData {json.dumps(message)}")
    time.sleep(1)
