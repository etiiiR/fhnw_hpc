import time
import json
import zenoh
import random

# Seed the random number generator for reproducibility
random.seed()

# Configuration dictionary for Zenoh session
config = {
    "connect": {
        "endpoints": ["tcp/localhost:7447"]
    }
}

def generate_bus_location(bus_id):
    lat = random.uniform(47.540, 47.570)
    lon = random.uniform(7.570, 7.600)
    speed = random.uniform(30, 60)  # Speed in km/h
    message = {
        "bus_id": bus_id,
        "timestamp": time.time(),
        "location": {"lat": lat, "lon": lon},
        "speed": speed
    }
    return json.dumps(message)

if __name__ == "__main__":
    print('Zenoh bus location producer started...')
    
    # Open a Zenoh session using the provided configuration
    session = zenoh.open(config)
    
    bus_ids = [f'Bus{i}' for i in range(1, 6)]

    while True:
        for bus_id in bus_ids:
            # Generate the bus location data
            buf = generate_bus_location(bus_id)
            location = json.loads(buf)
            timestamp = location["timestamp"]
            # Publish the bus location data
            key = f'bus/{bus_id}/location/{timestamp}'
            print(f"Putting Data ('{key}': '{buf}')...")
            session.put(key, buf)
            time.sleep(0.01)
