from fastapi import FastAPI, WebSocket
from confluent_kafka import Consumer, KafkaError
from aiokafka import AIOKafkaConsumer
import asyncio
import json
import random
import smartbus_pb2
app = FastAPI()

servers = 'kafka1:9092,kafka2:9092,kafka3:9092'
server = 'localhost:19092,localhost:19093,localhost:19094'

@app.get("/")
async def read_root():
    return {"Hello": "World"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    consumer = AIOKafkaConsumer(
        "bus_data",
        bootstrap_servers=servers,
        group_id="FrontendGroup" + str(random.randint(1, 1000)),
        enable_auto_commit=False,
        auto_offset_reset="earliest",
    )

    await consumer.start()

    try:
        async for msg in consumer:
            try:
                bus_data_proto = smartbus_pb2.BusData()
                bus_data_proto.ParseFromString(msg.value)

                bus_data_dict = {
                    "bus_id": bus_data_proto.bus_id,
                    "bus_type": bus_data_proto.bus_type,
                    "location": {
                        "lat": bus_data_proto.location.lat,
                        "lon": bus_data_proto.location.lon,
                    },
                    "bus_capacity": bus_data_proto.bus_capacity,
                    "people_in_bus": bus_data_proto.people_in_bus,
                    "driving_time": bus_data_proto.driving_time,
                    "driving_speed": bus_data_proto.driving_speed,
                    "engine_temperature": bus_data_proto.engine_temperature,
                    "timestamp": bus_data_proto.timestamp,
                    "black_box": {
                        "acceleration": bus_data_proto.black_box.acceleration,
                        "braking": bus_data_proto.black_box.braking,
                        "fuel_consumption": bus_data_proto.black_box.fuel_consumption,
                        "tire_pressure": bus_data_proto.black_box.tire_pressure,
                        "error_codes": list(bus_data_proto.black_box.error_codes),
                    },
                    "power_source": {},
                }
                
                # Send as JSON string
                await websocket.send_text(json.dumps(bus_data_dict))
                print('sent to frontend')
                print(bus_data_dict)
            except Exception as e:
                print(f"Error processing message: {e}")
                continue

    except Exception as e:
        print(f"Error sending WebSocket message: {e}")
    finally:
        await consumer.stop()


@app.websocket("/ws_locations")
async def websocket_buslocations(websocket: WebSocket):
    await websocket.accept()
    
    c = Consumer(
        {
            "bootstrap.servers": servers,
            "group.id": "FrontendGroup" + str(random.randint(1, 1000)),
            "auto.offset.reset": "latest",
            "enable.auto.commit": False,
        }
    )
    c.subscribe(["bus_locations"])

    try:
        while True:
            msg = c.poll(10)

            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                else:
                    print(msg.error())
                    break
            
            print(f"Consumed message: {msg.value()}")
            try:
                await websocket.send_text(msg.value().decode("utf-8"))
            except Exception as e:
                print(f"Error sending WebSocket message: {e}")
            
    except Exception as e:
        print(f"Error in WebSocket endpoint: {e}")
    finally:
        c.close()