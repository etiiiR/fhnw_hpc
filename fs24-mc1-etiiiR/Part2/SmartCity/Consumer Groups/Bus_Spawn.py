import yaml
import os

num_buses = 10
services = {
    'kafka1': {
        'image': "confluentinc/cp-kafka",
        'container_name': 'kafka1',
        'hostname': 'kafka1',
        'ports': ["19092:19092"],
        'environment': {
            'KAFKA_NODE_ID': 1,
            'KAFKA_CONTROLLER_LISTENER_NAMES': 'CONTROLLER',
            'KAFKA_LISTENER_SECURITY_PROTOCOL_MAP': 'CONTROLLER:PLAINTEXT,INTERNAL:PLAINTEXT,EXTERNAL:PLAINTEXT',
            'KAFKA_LISTENERS': 'INTERNAL://:9092,CONTROLLER://:9093,EXTERNAL://:19092',
            'KAFKA_ADVERTISED_LISTENERS': 'INTERNAL://kafka1:9092,EXTERNAL://localhost:19092',
            'KAFKA_INTER_BROKER_LISTENER_NAME': 'INTERNAL',
            'KAFKA_CONTROLLER_QUORUM_VOTERS': '1@kafka1:9093,2@kafka2:9093,3@kafka3:9093',
            'KAFKA_PROCESS_ROLES': 'broker,controller',
            'KAFKA_GROUP_INITIAL_REBALANCE_DELAY_MS': 0,
            'KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR': 3,
            'KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR': 3,
            'CLUSTER_ID': 'BDb4EWyiS1GjcEKCew2HvQ',
            'KAFKA_LOG_DIRS': '/tmp/kraft-combined-logs'
        }
    },
    'kafka2': {
        'image': 'confluentinc/cp-kafka',
        'container_name': 'kafka1',
        'hostname': 'kafka1',
        'ports': ["19093:19093"],
        'environment': {
            'KAFKA_NODE_ID': 2,
            'KAFKA_CONTROLLER_LISTENER_NAMES': 'CONTROLLER',
            'KAFKA_LISTENER_SECURITY_PROTOCOL_MAP': 'CONTROLLER:PLAINTEXT,INTERNAL:PLAINTEXT,EXTERNAL:PLAINTEXT',
            'KAFKA_LISTENERS': 'INTERNAL://:9092,CONTROLLER://:9093,EXTERNAL://:19092',
            'KAFKA_ADVERTISED_LISTENERS': 'INTERNAL://kafka1:9092,EXTERNAL://localhost:19092',
            'KAFKA_INTER_BROKER_LISTENER_NAME': 'INTERNAL',
            'KAFKA_CONTROLLER_QUORUM_VOTERS': '1@kafka1:9093,2@kafka2:9093,3@kafka3:9093',
            'KAFKA_PROCESS_ROLES': 'broker,controller',
            'KAFKA_GROUP_INITIAL_REBALANCE_DELAY_MS': 0,
            'KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR': 3,
            'KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR': 3,
            'CLUSTER_ID': 'BDb4EWyiS1GjcEKCew2HvQ',
            'KAFKA_LOG_DIRS': '/tmp/kraft-combined-logs'
        }
        # Repeat the configuration for kafka2 and kafka3 with appropriate changes
    },
    'kafka3': {
        'image': 'confluentinc/cp-kafka',
        'container_name': 'kafka1',
        'hostname': 'kafka1',
        'ports': ["19094:19094"],
        'environment': {
            'KAFKA_NODE_ID': 3,
            'KAFKA_CONTROLLER_LISTENER_NAMES': 'CONTROLLER',
            'KAFKA_LISTENER_SECURITY_PROTOCOL_MAP': 'CONTROLLER:PLAINTEXT,INTERNAL:PLAINTEXT,EXTERNAL:PLAINTEXT',
            'KAFKA_LISTENERS': 'INTERNAL://:9092,CONTROLLER://:9093,EXTERNAL://:19094',
            'KAFKA_ADVERTISED_LISTENERS': 'INTERNAL://kafka1:9092,EXTERNAL://localhost:19094',
            'KAFKA_INTER_BROKER_LISTENER_NAME': 'INTERNAL',
            'KAFKA_CONTROLLER_QUORUM_VOTERS': '1@kafka1:9093,2@kafka2:9093,3@kafka3:9093',
            'KAFKA_PROCESS_ROLES': 'broker,controller',
            'KAFKA_GROUP_INITIAL_REBALANCE_DELAY_MS': 0,
            'KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR': 3,
            'KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR': 3,
            'CLUSTER_ID': 'BDb4EWyiS1GjcEKCew2HvQ',
            'KAFKA_LOG_DIRS': '/tmp/kraft-combined-logs'
        }
    },
    'kafdrop': {
        'image': 'obsidiandynamics/kafdrop:latest',
        'container_name': 'kafdrop1',
        'ports': ["9000:9000"],
        'environment': {
            'KAFKA_BROKERCONNECT': "kafka1:9092,kafka2:9092,kafka3:9092",
            'SERVER_SERVLET_CONTEXTPATH': "/"
        },
        'depends_on': ["kafka1", "kafka2", "kafka3"]
    }
}

for i in range(1, num_buses + 1):
    bus_id = f"bus{i}"
    services[bus_id] = {
        "image": "smart_bus_image",
        "environment": [f"BUS_ID={bus_id}"],
        # Add other service configurations as needed
        'depends_on': ['kafka1', 'kafka2', 'kafka3']  # Ensure buses depend on Kafka brokers
    }

compose_file = {
    "version": "3.8",
    "services": services
}

# Adjusted for Kafka and bus services
current_dir = os.getcwd()
output_dir = os.path.join(current_dir, "Part2/SmartCity/Consumer Groups") if "fs24-mc1-etiiiR" in current_dir else current_dir

output_file = os.path.join(output_dir, "docker-compose.generated.yml")
with open(output_file, 'w') as f:
    yaml.dump(compose_file, f, sort_keys=False)
