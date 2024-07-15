import faust
from smartbus_pb2 import BusData as ProtoBusData  # Import the Protobuf generated class for BusData
from faust.serializers import codecs
app = faust.App('smartbus_consumer_app',
                broker='localhost:19092,localhost:19093,localhost:19094',
                loglevel='debug')  # set log level to debug for verbose output
# Custom Codec for Protobuf Serialization/Deserialization
class ProtobufCodec(faust.Codec):
    def _loads(self, s: bytes) -> ProtoBusData:
        message = ProtoBusData()
        message.ParseFromString(s)
        print(message)
        return message

    def _dumps(self, obj: ProtoBusData) -> bytes:
        return obj.SerializeToString()

# Register the codec with Faust
codecs.register('protobuf', ProtobufCodec())

# Define the topic with the custom 'protobuf' serializer
topic = app.topic('bus_data', value_serializer='protobuf')
topic_avg_passengers = app.topic('average_passengers', value_type=float, value_serializer='json')
passenger_counts = app.Table('passenger_counts', default=int, partitions=1)

@app.agent(topic)
async def consume_bus_data(bus_data):
    async for data in bus_data:
        # Assuming `data` is your deserialized message with `bus_id` and `people_in_bus` attributes
        print(data.bus_id)
        print(data.people_in_bus)
        passenger_counts[data.bus_id] += data.people_in_bus  # Update passenger_counts table

        
@app.timer(interval=20) 
async def compute_average_passengers():
    if len(passenger_counts) == 0:
        print("No bus data available.")
        return
    
    total_passengers = sum(passenger_counts.values())
    avg_passengers = total_passengers / len(passenger_counts)
    print('avg passenger')
    print('passenger')
    print(avg_passengers)
    print(f'Average passengers in the last 20 minutes --> simulate in 20 seconds 20 minutes: {avg_passengers}')
    await topic_avg_passengers.send(value=avg_passengers)
    # produce the average to a new topic
    #await topic_avg_passengers.send(value=avg_passengers)

min_passenger_counts = app.Table('min_passenger_counts', default=int)
max_passenger_counts = app.Table('max_passenger_counts', default=int)

@app.agent(topic)
async def compute_min_max_passengers(bus_data):
    async for data in bus_data:
        current_count = passenger_counts[data.bus_id]
        min_count = min_passenger_counts[data.bus_id]
        max_count = max_passenger_counts[data.bus_id]
        
        if current_count < min_count or min_count == 0:
            min_passenger_counts[data.bus_id] = current_count
        
        if current_count > max_count:
            max_passenger_counts[data.bus_id] = current_count

high_density_topic = app.topic('high_density_buses', value_type=str)

@app.agent(topic)
async def alert_high_density(bus_data):
    async for data in bus_data:
        if data.people_in_bus / data.bus_capacity > 0.8:  # More than 80% capacity
            await high_density_topic.send(value=data.bus_id)
            print(f"High density alert for {data.bus_id}")


if __name__ == '__main__':
    app.main()


