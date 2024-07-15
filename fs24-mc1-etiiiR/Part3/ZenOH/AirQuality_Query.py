import zenoh
from zenoh import Sample
import json
import random
import time

# Configuration for Zenoh session
zenoh_config = {
    "connect": {
        "endpoints": ["tcp/localhost:7447"]
    }
}

# Key under which the processed data and alerts will be published
processed_data_key = "environment/air_quality/processed_data"
restricted_areas_key = "environment/air_quality/restricted_areas"

def process_data(data):
    """Simulates data processing."""
    data['processed'] = True
    data['airquality_index'] = data['pm2_5'] + data['pm10'] + data['o3']
    if data['airquality_index'] > 180:
        data['restricted'] = True
    return data

def publish_processed_data(session, data):
    session.put(processed_data_key, json.dumps(data).encode("utf-8"))
    if data.get('restricted'):
        message = {
            "location": data['location'],
            "timestamp": data['timestamp'],
            "restricted": data['restricted'],
            "message": f"Air quality at {data['location']} is too bad, the area is restricted. Find alternative routes."
        }
        session.put(restricted_areas_key, json.dumps(message).encode("utf-8"))

def queryable_callback(session, query):
    print(f">> [Queryable] Received Query '{query.selector}'")
    if query.data is not None:
        # Assuming the data payload is directly accessible
        data = json.loads(query.data.payload.decode("utf-8"))
        processed_data = process_data(data)
        publish_processed_data(session, processed_data)
        # Reply to the query with the processed data
        query.reply(Sample(query.key_expr, json.dumps(processed_data).encode("utf-8")))

def main():
    # Initiate logging
    zenoh.init_logger()
    complete = False
    print("Opening session...")
    session = zenoh.open(zenoh_config)

    key = "environment/air_quality/data"
    
    print(f"Declaring Queryable on '{key}'...")
    queryable = session.declare_queryable(key, lambda query: queryable_callback(session, query), complete)

    print("Press CTRL-C to quit...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        print("Closing Zenoh session...")
        queryable.undeclare()
        session.close()

if __name__ == "__main__":
    main()
