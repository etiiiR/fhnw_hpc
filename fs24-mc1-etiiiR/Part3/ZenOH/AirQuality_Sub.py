import zenoh
from zenoh import Sample
import json
import time

class AirQualityProcessor:
    def __init__(self, zenoh_config):
        self.session = zenoh.open(zenoh_config)
        
        # Subscribe to raw air quality data
        self.subscription = self.session.declare_subscriber("environment/air_quality/publish/*/*", self.air_quality_sub_callback)
        
        print("Subscribing to 'environment/air_quality/'...")

    def process_data(self, data):
        """Simulated data processing."""
        data['processed'] = True
        data['airquality_index'] = data['pm2_5'] + data['pm10'] + data['o3']
        if data['airquality_index'] > 180:
            data['restricted'] = True
        return data

    def send_alert_message(self, data):
        """Sends an alert message if the area is restricted due to poor air quality."""
        if data.get('restricted'):
            message = {
                "location": data['location'],
                "timestamp": data['timestamp'],
                "restricted": data['restricted'],
                "message": f"Air quality at {data['location']} is too bad, the area is restricted. Find alternative routes."
            }
            self.session.put(f"environment/air_quality/restricted_areas/{data['timestamp']}", json.dumps(message).encode('utf-8'))

    def publish_processed_data(self, data):
        """Publishes processed air quality data."""
        self.session.put("environment/air_quality/processed_data", json.dumps(data).encode('utf-8'))

    def air_quality_sub_callback(self, sample):
        """Callback function for the subscriber."""
        data = json.loads(sample.payload.decode('utf-8'))
        processed_data = self.process_data(data)
        self.send_alert_message(processed_data)
        self.publish_processed_data(processed_data)
        print(f"Processed data: {processed_data}")
    
    def run(self):
        print("Press CTRL-C to quit...")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            self.cleanup()

    def cleanup(self):
        print("Closing Zenoh session...")
        self.subscription.undeclare()
        self.session.close()

if __name__ == "__main__":
    zenoh.init_logger()

    zenoh_config = {
        "connect": {
            "endpoints": ["tcp/localhost:7447"]
        }
    }

    processor = AirQualityProcessor(zenoh_config)
    processor.run()
