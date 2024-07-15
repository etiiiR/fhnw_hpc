from confluent_kafka import Consumer, KafkaError
import json
import asyncio
from surrealdb import Surreal

# Kafka Consumer Configuration
servers = 'localhost:19092,localhost:19093,localhost:19094'
servers = 'kafka1:9092,kafka2:9092,kafka3:9092'
topic = 'bus_locations'

class BusArrivalEstimator:
    def __init__(self, server_list):
        self.consumer = Consumer({
            'bootstrap.servers': server_list,
            'group.id': 'bus_arrival_estimator',
            'auto.offset.reset': 'earliest'
        })
        self.consumer.subscribe([topic])

    def estimate_arrival_time(self, lat, lon, speed):
        destination_lat, destination_lon = 47.560, 7.590  # Fixed destination coordinates
        distance_km = self.calculate_distance(lat, lon, destination_lat, destination_lon)
        if speed <= 0:
            return float('inf')  # Avoid division by zero
        time_hours = distance_km / speed
        return time_hours * 60  # Convert hours to minutes

    def calculate_distance(self, lat1, lon1, lat2, lon2):
        return ((lat2 - lat1) ** 2 + (lon2 - lon1) ** 2) ** 0.5 * 111.32  # Approximation

    async def process_messages(self, db):
        while True:
            msg = self.consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                else:
                    print(msg.error())
                    break

            message = json.loads(msg.value().decode('utf-8'))
            print(message)
            arrival_time = self.estimate_arrival_time(message["location"]["lat"], message["location"]["lon"], message["speed"])
            print(f"Bus {message['bus_id']} will arrive in approximately {arrival_time:.2f} minutes.")
            
            # Save to SurrealDB
            await db.query(f"""
            insert into bus_arrivals {{
                bus_id: '{message['bus_id']}',
                location: {{lat: {message["location"]["lat"]}, lon: {message["location"]["lon"]}}},
                arrival_time: {arrival_time},
                destination: {{lat: 47.560, lon: 7.590}}
            }};
            """)

async def main():
    async with Surreal("ws://surrealdb:8000/rpc") as db:
        await db.signin({"user": "etiiir", "pass": "Welcome12"})
        await db.use("Bus", "SmartCity")
        print("Connected to SurrealDB")
        estimator = BusArrivalEstimator(servers)
        await estimator.process_messages(db)
        print("Done processing messages")

if __name__ == "__main__":
    asyncio.run(main())
