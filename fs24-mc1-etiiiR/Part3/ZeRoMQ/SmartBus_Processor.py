import zmq
import json
import csv
from datetime import datetime

class BusServiceResetterZeroMQ:
    def __init__(self, push_address="tcp://localhost:5557"):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUSH)
        self.json_filename = "/usr/src/app/data/bus_data.json"  # Adjusted file path
        self.csv_filename = "/usr/src/app/data/bus_data.csv"    # Adjusted file path
        self.socket.connect(push_address)
        print(f"Resetter connected to {push_address}")

    def reset_bus_service(self, bus_id):
        message = {
            "bus_id": bus_id,
            "timestamp": datetime.now().isoformat(),
            "reset": True
        }
        self.socket.send_string(json.dumps(message))
        print(f"Resetting service for bus {bus_id}")

class SmartBusProcessorZeroMQ:
    def __init__(self, subscription_address="tcp://smartbus_publisher:5556", resetter_address="tcp://smartbus_publisher:5557"):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.connect(subscription_address)
        self.socket.setsockopt_string(zmq.SUBSCRIBE, '')
        self.resetter = BusServiceResetterZeroMQ(resetter_address)
        self.service_probabilities = {}
        self.seconds_without_service = {}
        self.json_filename = "bus_data.json"
        self.csv_filename = "bus_data.csv"
        self.initialize_csv()

    def initialize_csv(self):
        with open(self.csv_filename, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["bus_id", "timestamp", "service_probability"])

    def process_message(self, message):
        bus_id = message.get("bus_id")
        if bus_id is None:
            print("Missing bus_id in message")
            return

        current_message_time = datetime.now()
        if bus_id in self.seconds_without_service:
            time_since_last_message = (current_message_time - self.seconds_without_service[bus_id]['last_message_time']).total_seconds()
        else:
            time_since_last_message = 0

        self.seconds_without_service[bus_id] = {
            "seconds": self.seconds_without_service.get(bus_id, {}).get("seconds", 0) + time_since_last_message,
            "last_message_time": current_message_time
        }

        service_probability = self.calculate_service_probability(message)
        if bus_id not in self.service_probabilities:
            self.service_probabilities[bus_id] = []
        self.service_probabilities[bus_id].append({
            "timestamp": datetime.now().isoformat(),
            "probability": service_probability
        })

        if service_probability is not None and service_probability >= 0.6:
            print(f"Bus {bus_id} has a service probability of {service_probability}. Sending bus into service.")
            self.resetter.reset_bus_service(bus_id)
            self.service_probabilities[bus_id] = []
            self.seconds_without_service[bus_id] = {"seconds": 0, "last_message_time": current_message_time}

        # Data sink for JSON and CSV
        self.save_to_json(message, service_probability)
        self.save_to_csv(bus_id, service_probability)

    def calculate_service_probability(self, message):
        try:
            engine_temp_factor = message["engine_temperature"] / 120
            driving_speed_factor = 1 - message["driving_speed"] / 100
            technical_probability = (engine_temp_factor + driving_speed_factor) / 2

            bus_id = message["bus_id"]
            seconds_factor = self.seconds_without_service.get(bus_id, {}).get("seconds", 0) / 10  # Adjust as necessary
            return 0.5 * technical_probability + 0.5 * seconds_factor
        except KeyError as e:
            print(f"Error calculating service probability: {e}")
            return None

    def save_to_json(self, message, service_probability):
        data = message
        data["service_probability"] = service_probability
        with open(self.json_filename, 'a') as file:
            json.dump(data, file)
            file.write('\n')

    def save_to_csv(self, bus_id, service_probability):
        with open(self.csv_filename, 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([bus_id, datetime.now().isoformat(), service_probability])

    def start(self):
        print("Starting SmartBusProcessorZeroMQ...")
        while True:
            try:
                string = self.socket.recv_string()
                topic, message = string.split(' ', 1)
                message = json.loads(message)
                self.process_message(message)
            except Exception as e:
                print(f"An error occurred: {e}")

if __name__ == "__main__":
    print('started')
    processor = SmartBusProcessorZeroMQ()
    processor.start()
