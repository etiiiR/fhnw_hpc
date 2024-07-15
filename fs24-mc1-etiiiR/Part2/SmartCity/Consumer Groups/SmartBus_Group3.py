
from confluent_kafka import Consumer, Producer, KafkaError
import smartbus_pb2  # Import the generated Protobuf module
from datetime import datetime
from google.protobuf.timestamp_pb2 import Timestamp
import os
import json

class SmartBusProcessor:
    def __init__(self, servers):
        self.consumer = Consumer({
            'bootstrap.servers': servers,
            'group.id': 'bus_processor_group3',
            'auto.offset.reset': 'earliest'
        })
        self.service_probabilities = {}
        self.seconds_without_service = {}

    def calculate_service_probability(self, bus_data):
        if bus_data is None:
            return None

        # Probability increases with engine temperature and decreases with driving speed
        engine_temp_factor = bus_data.engine_temperature / 120
        driving_speed_factor = 1 - bus_data.driving_speed / 100
        technical_probability = (engine_temp_factor + driving_speed_factor) / 2

        bus_id = bus_data.bus_id
        seconds_factor = self.seconds_without_service.get(bus_id, 0) / 10  # Assuming 100 seconds is the maximum without service
        return 0.5 * technical_probability + 0.5 * seconds_factor

    def process_bus_data(self, topic="bus_data"):
        print(f"Subscribing to topic: {topic}")
        self.consumer.subscribe([topic])

        message_count = 0
        last_message_time = datetime.now()

        while True:
            msg = self.consumer.poll(1.0)

            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    print(f"Reached end of topic {msg.topic()} [{msg.partition()}] at offset {msg.offset()}")
                    continue
                else:
                    print(msg.error())
                    break
            #print("Debug - Consuming message bytes:", msg.value())
            bus_data = smartbus_pb2.BusData()  # Use the BusData message type
            try:
                bus_data.ParseFromString(msg.value())
            except Exception as e:
                print(f"Error parsing message: {e}")
                continue

            bus_id = bus_data.bus_id
            if not bus_id:
                print("Missing bus_id in message")
                continue

            # Calculate the time since the last message in seconds
            current_message_time = datetime.now()
            time_since_last_message = (current_message_time - last_message_time).total_seconds()
            last_message_time = current_message_time

            # Update the seconds_without_service for this bus
            self.seconds_without_service[bus_id] = self.seconds_without_service.get(bus_id, 0) + time_since_last_message

            service_probability = self.calculate_service_probability(bus_data)
            timestamp = datetime.now().isoformat()
            if bus_id not in self.service_probabilities:
                self.service_probabilities[bus_id] = []
            self.service_probabilities[bus_id].append({
                "timestamp": timestamp,
                "probability": service_probability
            })

            # If service probability is 80% or more, send bus into service and reset probabilities and seconds without service
            if service_probability is not None and service_probability >= 0.8:
                print(f"Bus {bus_id} has a service probability of {service_probability}. Sending bus into service.")
                BusServiceResetter(servers).reset_bus_service(bus_id)
                self.service_probabilities[bus_id] = []
                self.seconds_without_service[bus_id] = 0

            message_count += 1
            print(message_count)
            # Persist to JSON every 100 messages
            if message_count % 100 == 0:
                # This part remains as is since it's for internal tracking, not Kafka messaging
                with open('service_probabilities.json', 'w') as f:
                    json.dump(self.service_probabilities, f)

        self.consumer.close()

class BusServiceResetter:
    def __init__(self, servers):
        self.producer = Producer({'bootstrap.servers': servers})

    def reset_bus_service(self, bus_id, topic="bus_service_station"):
        print(f"Resetting service for bus {bus_id}")
        reset_message = smartbus_pb2.BusData()  # Assuming you have a suitable message type for reset
        reset_message.bus_id = bus_id
        timestamp = Timestamp()
        timestamp.FromDatetime(datetime.now())
        reset_message.timestamp


if __name__ == "__main__":
    if (os.environ.get('KAFKA_SERVER') is not None):
        servers = os.environ.get('KAFKA_SERVER', "smartstation_producer")
    else:
        servers = 'localhost:19092,localhost:19093,localhost:19094'

    smart_bus_processor = SmartBusProcessor(servers)
    smart_bus_processor.process_bus_data()
