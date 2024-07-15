import zmq
import json
import random
import time
import math

def generate_random_air_quality():
    locations = ['CityCenter', 'Suburb', 'IndustrialArea', 'Park']
    return {
        "location": random.choice(locations),
        "pm2_5": random.uniform(5, 100),  # Particulate matter 2.5
        "pm10": random.uniform(10, 150),  # Particulate matter 10
        "no2": random.uniform(0, 50),  # Nitrogen Dioxide
        "co2": 400 + (time.time() / 31536000) * 10,  # CO2, increasing by 10 units per year
        "temperature": random.uniform(-10, 40),  # Temperature in Celsius
        "humidity": random.uniform(0, 100),  # Humidity in %
        "pressure": random.uniform(950, 1050),  # Atmospheric pressure in hPa
        "o3": random.uniform(0, 10),  # Ozone
        "so2": random.uniform(0, 20),  # Sulphur Dioxide
        "timestamp": time.time(),  # Current timestamp
        "wind_speed": random.uniform(0, 100)  # Wind speed in km/h
    }

context = zmq.Context()
socket = context.socket(zmq.PUB)
socket.bind("tcp://*:5556")

while True:
    for _ in range(10):  # Send 10 messages per second
        air_quality_data = generate_random_air_quality()
        print(air_quality_data)
        socket.send_string(f"AirQualityData {json.dumps(air_quality_data)}")
    time.sleep(1)  # Sleep for 1 second to maintain 10 messages per second
