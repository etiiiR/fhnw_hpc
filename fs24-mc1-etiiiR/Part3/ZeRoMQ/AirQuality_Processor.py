import zmq
import json
import time

class AirQualityProcessorZMQ:
    def __init__(self, input_endpoint, output_endpoint):
        self.context = zmq.Context()
        
        # Setup ZeroMQ Subscriber
        self.subscriber = self.context.socket(zmq.SUB)
        self.subscriber.connect(input_endpoint)
        self.subscriber.setsockopt_string(zmq.SUBSCRIBE, "AirQualityData")
        
        # Setup ZeroMQ Publisher
        self.publisher = self.context.socket(zmq.PUB)
        self.publisher.bind(output_endpoint)

    def process_data(self, data):
        """Simulated data processing."""
        data['processed'] = True
        data['airquality_index'] = data['pm2_5'] + data['pm10'] + data['o3']
        if (data['airquality_index'] > 180):
            data['restricted'] = True
        return data

    def send_alert_message_to_bus_drivers(self, data):
        if data.get('restricted'):
            message = {
                "location": data['location'],
                "timestamp": data['timestamp'],
                "restricted": data['restricted'],
                "message": f"Air quality at {data['location']} is too bad, the area is restricted. Find alternative routes."
            }
            self.publisher.send_string(f"RestrictedAreaAlerts {json.dumps(message)}")

    def publish_processed_data(self, data):
        processed_data_str = json.dumps(data)
        self.publisher.send_string(f"ProcessedAirQualityData {processed_data_str}")
        self.send_alert_message_to_bus_drivers(data)

    def consume_and_process_data(self):
        try:
            while True:
                string = self.subscriber.recv_string()
                topic, message = string.split(' ', 1)
                data = json.loads(message)
                processed_data = self.process_data(data)
                self.publish_processed_data(processed_data)
                print(f'Processed message: {processed_data}')
        except KeyboardInterrupt:
            pass
        finally:
            self.subscriber.close()
            self.publisher.close()
            self.context.term()

if __name__ == '__main__':
    input_endpoint = "tcp://airquality_producer:5556"  # Adjust as needed, must match producer's bind
    output_endpoint = "tcp://*:5557"  # Bind address for publishing processed data
    processor = AirQualityProcessorZMQ(input_endpoint, output_endpoint)
    processor.consume_and_process_data()
