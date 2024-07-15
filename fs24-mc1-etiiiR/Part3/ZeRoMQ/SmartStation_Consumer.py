import json
import asyncio
import zmq
import zmq.asyncio
from surrealdb import Surreal

class BusArrivalEstimatorZMQ:
    def __init__(self, input_endpoint):
        self.context = zmq.asyncio.Context()
        self.subscriber = self.context.socket(zmq.SUB)
        self.subscriber.connect(input_endpoint)
        self.subscriber.setsockopt_string(zmq.SUBSCRIBE, "")  # Subscribe to all messages

    def estimate_arrival_time(self, lat, lon, speed):
        destination_lat, destination_lon = 47.560, 7.590  # Fixed destination coordinates
        distance_km = self.calculate_distance(lat, lon, destination_lat, destination_lon)
        if speed <= 0:
            return float('inf')  # Avoid division by zero
        time_hours = distance_km / speed
        return time_hours * 60  # Convert hours to minutes

    def calculate_distance(self, lat1, lon1, lat2, lon2):
        # Approximate method to calculate distance between two points
        return ((lat2 - lat1) ** 2 + (lon2 - lon1) ** 2) ** 0.5 * 111.32

    async def process_messages(self, db):
        try:
            while True:
                string = await self.subscriber.recv_string()
                message = json.loads(string)
                arrival_time = self.estimate_arrival_time(message["location"]["lat"], message["location"]["lon"], message["speed"])
                
                # Save to SurrealDB
                await db.query(f"""
                INSERT INTO bus_arrivals {{
                    bus_id: '{message['bus_id']}',
                    location: {{lat: {message["location"]["lat"]}, lon: {message["location"]["lon"]}}},
                    arrival_time: {arrival_time},
                    destination: {{lat: 47.560, lon: 7.590}}
                }};
                """)
                print(f"Bus {message['bus_id']} will arrive in approximately {arrival_time:.2f} minutes.")
        except KeyboardInterrupt:
            pass
        except Exception as e:
            print(e)
        finally:
            self.subscriber.close()
            self.context.term()
        

async def main():
    input_endpoint = "tcp://smartstation_producer:5556"
    async with Surreal("ws://surrealdb:8000/rpc") as db:
        await db.signin({"user": "etiiir", "pass": "Welcome12"})
        await db.use("Bus", "SmartCity")
        print("Connected to SurrealDB")
        estimator = BusArrivalEstimatorZMQ(input_endpoint)
        print("Processing messages")
        await estimator.process_messages(db)
        print("Done processing messages")

if __name__ == "__main__":
    print('started')
    asyncio.run(main())
