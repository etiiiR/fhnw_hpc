import json
import pandas as pd
from confluent_kafka import Consumer, KafkaError, KafkaException
import os

class DataPersistenceConsumer:
    def __init__(self, servers, group_id, topic, csv_file_path, hdf_store_path):
        self.consumer = Consumer({
            'bootstrap.servers': servers,
            'group.id': group_id,
            'auto.offset.reset': 'earliest'
        })
        self.topic = topic
        self.csv_file_path = csv_file_path
        self.hdf_store_path = hdf_store_path

    def consume_data_and_persist(self):
        self.consumer.subscribe([self.topic])
        df = pd.DataFrame(columns=['timestamp', 'location', 'quality', 'processed'])

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
                    df = pd.concat([df, pd.DataFrame([message])], ignore_index=True)
                    if len(df) >= 5:
                        file_empty = os.path.getsize(self.csv_file_path) == 0
                        df.to_csv(self.csv_file_path, index=False, mode='a', header=file_empty)
                        df.to_hdf(self.hdf_store_path, key='air_quality', mode='a', append=True)
                        df = df.iloc[0:0]
        finally:
            self.consumer.close()

    def run(self):
        self.consume_data_and_persist()

servers = 'localhost:19092,localhost:19093,localhost:19094'
group_id_processor = 'air_quality_processor_group'
group_id_persistence = 'data_persistence_group'
input_topic = 'air_quality_data'
csv_file_path = './MC1/SmartCity/data/air_quality_data.csv'
hdf_store_path = './MC1/SmartCity/data/air_quality_data.h5'

# Start the persistence consumer
persistence_consumer = DataPersistenceConsumer(servers, group_id_persistence, input_topic, csv_file_path, hdf_store_path)
# Persistence consumer can be run in a separate thread or process
persistence_consumer.run()
