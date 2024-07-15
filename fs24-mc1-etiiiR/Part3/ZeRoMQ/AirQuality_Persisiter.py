import json
import pandas as pd
import zmq
import os

class DataPersistenceConsumerZMQ:
    def __init__(self, input_endpoint, csv_file_path, hdf_store_path):
        self.context = zmq.Context()
        self.subscriber = self.context.socket(zmq.SUB)
        self.subscriber.connect(input_endpoint)
        self.subscriber.setsockopt_string(zmq.SUBSCRIBE, "ProcessedAirQualityData")  # Adjust the subscription topic
        self.csv_file_path = csv_file_path
        self.hdf_store_path = hdf_store_path

    def consume_data_and_persist(self):
        df = pd.DataFrame(columns=['timestamp', 'location', 'quality', 'processed'])
        try:
            while True:
                string = self.subscriber.recv_string()
                topic, message = string.split(' ', 1)
                data = json.loads(message)
                print(data)
                df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
                if len(df) >= 5:
                    file_empty = not os.path.exists(self.csv_file_path) or os.path.getsize(self.csv_file_path) == 0
                    df.to_csv(self.csv_file_path, index=False, mode='a', header=file_empty)
                    df.to_hdf(self.hdf_store_path, key='air_quality', mode='a', append=True, format='table')
                    df = df.iloc[0:0]
        except KeyboardInterrupt:
            pass
        finally:
            self.subscriber.close()
            self.context.term()

    def run(self):
        self.consume_data_and_persist()

if __name__ == '__main__':
    input_endpoint = "tcp://airquality_producer:5557"  # Adjust as needed, must match processor's output bind address
    csv_file_path = './MC1/SmartCity/data/air_quality_data.csv'
    hdf_store_path = './MC1/SmartCity/data/air_quality_data.h5'
    persistence_consumer_zmq = DataPersistenceConsumerZMQ(input_endpoint, csv_file_path, hdf_store_path)
    persistence_consumer_zmq.run()
