import json
from confluent_kafka import Consumer, Producer, KafkaError, KafkaException

class AirQualityProcessor:
    def __init__(self, servers, group_id, input_topic, output_topic):
        self.consumer = Consumer({
            'bootstrap.servers': servers,
            'group.id': group_id,
            'auto.offset.reset': 'earliest'
        })
        self.producer = Producer({
            'bootstrap.servers': servers
        })
        self.input_topic = input_topic
        self.output_topic = output_topic

    def process_data(self, data):
        """Simulated data processing."""
        data['processed'] = True
        data['airquality_index'] = data['pm2_5'] + data['pm10'] + data['o3']
        if (data['airquality_index'] > 180 ):
            data['restricted'] = True
        return data

    def consume_and_process_data(self):
        self.consumer.subscribe([self.input_topic])
        try:
            while True:
                msg = self.consumer.poll(1.0)
                if msg is None:
                    continue
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    else:
                        raise KafkaException(msg.error())
                else:
                    message = json.loads(msg.value().decode('utf-8'))
                    processed_message = self.process_data(message)
                    self.publish_processed_data(processed_message)
                    print(f'Processed message: {processed_message}')
        finally:
            self.consumer.close()
            
    def send_alert_message_to_bus_drivers(self, data):
        if data.get('ClosedDown'):
            message = {
                "location": data['location'],
                "timestamp": data['timestamp'],
                "ClosedDown": data['ClosedDown'],
                "message": f"Air quality at {data['location']} is too bad, the area is closed down. Find alternative routes."
            }
            self.producer.produce(self.output_topic, json.dumps(message).encode('utf-8'))
            self.producer.poll(1)

    def publish_processed_data(self, data):
        message = json.dumps(data).encode('utf-8')
        self.producer.produce(self.output_topic, message)
        self.send_alert_message_to_bus_drivers(data)
        self.producer.poll(1)

    def run(self):
        self.consume_and_process_data()


if __name__ == '__main__':
    servers = 'localhost:19092,localhost:19093,localhost:19094'
    group_id_processor = 'air_quality_processor_group'
    input_topic = 'air_quality_data'
    output_topic = 'restricted_area_alerts'
    processor = AirQualityProcessor(servers, group_id_processor, input_topic, output_topic)
    processor.run()
