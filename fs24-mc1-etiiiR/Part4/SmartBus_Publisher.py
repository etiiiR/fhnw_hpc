import math
import random
import time
from confluent_kafka import Producer
import smartbus_pb2  # Ensure this matches the generated file name from your smartbus.proto

servers = 'kafka1:9092,kafka2:9092,kafka3:9092'

class SmartBus:
    def __init__(self, servers):
        self.producer = Producer({'bootstrap.servers': servers})

    def delivery_report(self, err, msg):
        """ Called once for each message produced to indicate delivery result.
            Triggered by poll() or flush(). """
        if err is not None:
            print(f'Message delivery failed: {err}')
        else:
            print(f'Message delivered to {msg.topic()} [{msg.partition()}]')

    def generate_random_gps(self, lat, lon, radius):
        """ Generate random GPS coordinates within a given radius around a central point """
        radius_in_degrees = radius / 111300
        u = random.uniform(0, 1)
        v = random.uniform(0, 1)
        w = radius_in_degrees * math.sqrt(u)
        t = 2 * math.pi * v
        x = w * math.cos(t)
        y = w * math.sin(t)
        new_lat = x + lat
        new_lon = y / math.cos(lat * math.pi / 180) + lon  # Adjust for the latitude
        return new_lat, new_lon

    def send_bus_data(self, topic="bus_data"):
        """ Generate and send bus data messages """
        bus_ids = [f'Bus{i}' for i in range(1, 21)]  # Generate bus IDs Bus1 through Bus20
        bus_types = ['conventional', 'electric']
        basel_lat, basel_lon = 47.5596, 7.5886  # GPS coordinates for Basel, Switzerland
        
        while True:
            for _ in range(10):  # Send 10 messages per second
                bus_message = smartbus_pb2.BusData()
                bus_message.bus_id = random.choice(bus_ids)
                bus_message.bus_type = random.choice(bus_types)
                lat, lon = self.generate_random_gps(basel_lat, basel_lon, 20000)
                bus_message.location.lat = lat
                bus_message.location.lon = lon
                bus_capacity = random.randint(30, 60)
                bus_message.bus_capacity = bus_capacity
                bus_message.people_in_bus = random.randint(0, bus_capacity)
                driving_time = random.uniform(0, 24)
                bus_message.driving_time = driving_time
                bus_message.driving_speed = random.uniform(0, 100)
                bus_message.engine_temperature = random.uniform(60, 120)
                bus_message.timestamp = time.time()
                # Fill in the black box data
                black_box = bus_message.black_box
                black_box.acceleration = random.uniform(0, 10)
                black_box.braking = random.uniform(0, 10)
                black_box.fuel_consumption = random.uniform(0, 10)
                black_box.tire_pressure = random.uniform(1, 3)
                for _ in range(random.randint(0, 5)):
                    black_box.error_codes.append(random.randint(0, 100))
                if bus_message.bus_type == 'conventional':
                    bus_message.fuel_level = 100 - (100/24*driving_time)
                else:
                    bus_message.battery_level = 100 - random.uniform(0, 100)/(driving_time*(100/24))

                message_bytes = bus_message.SerializeToString()
                # In the SmartBus class, right before sending the message
                #print("Debug - Serialized message bytes:", message_bytes)
                # This won't be human-readable but confirms data is being serialized

                self.producer.produce(topic, message_bytes, callback=self.delivery_report)
                self.producer.poll(0)
            time.sleep(1)  # Sleep for 1 second to maintain a 10 messages per second rate
            self.producer.flush()

if __name__ == "__main__":
    # sleep for 30 seconds to allow the Kafka cluster to start
    time.sleep(30)
    smart_bus = SmartBus(servers)
    smart_bus.send_bus_data()
