import time
import json
import zenoh
import random

# Seed the random number generator for reproducibility
random.seed()

# Configuration dictionary for Zenoh session
zenoh_config = {
    "connect": {
        "endpoints": ["tcp/localhost:7447"]
    }
}

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

if __name__ == "__main__":
    print('Zenoh air quality data publisher started...')

    # Open a Zenoh session using the provided configuration
    session = zenoh.open(zenoh_config)
    
    while True:
        for _ in range(1):  # Send 10 messages per second
            air_quality_data = generate_random_air_quality()
            buf = json.dumps(air_quality_data)
            location = air_quality_data["location"]
            timestamp = air_quality_data["timestamp"]
            key = f'environment/air_quality/publish/{location}/{timestamp}'
            print(f"Putting Data ('{key}': '{buf}')...")
            session.put(key, buf)
        time.sleep(0.5)  # Sleep for 1 second to maintain 10 messages per second

    session.close()
