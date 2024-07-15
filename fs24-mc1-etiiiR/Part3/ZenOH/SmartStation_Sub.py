import zenoh
import json
import time

config = {
    "connect": {
        "endpoints": ["tcp/localhost:7447"]
    }
}

def callback(sample):
    # Assuming the data is JSON-encoded, we decode it to print
    data = json.loads(sample.payload.decode('utf-8'))
    print(f"Received data: {data}")

if __name__ == "__main__":
    print('Zenoh bus location subscriber started...')
    session = zenoh.open(config)
    
    # Subscribe to all bus location updates
    subscriber = session.declare_subscriber("bus/*/location/**", callback)
    
    try:
        # Keep the program running to continue receiving messages.
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        # Cleanup Zenoh session before exiting
        session.close()
