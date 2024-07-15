# Mini-Challenge 1 - High-Performance Computing (HPC) FS24

## MiniChallenge Overview:

**Urban Mobility and Environmental Monitoring Suite**

### Essential Resources:
- **Kafka Application Docker Compose**: [docker-compose.yml](./Application/docker-compose.yml)
- **ZeroMQ Docker Compose**: [docker-compose.yml](./Part3/ZeRoMQ/docker-compose.yml)
- **ZenOH Docker Compose**: [docker-compose.yml](./Part3/ZeRoMQ/docker-compose.yml)
- **Performance Experiments**: [Performance.ipynb](./Part4/Performance.ipynb)

### Overview:

Initially a simulation, this suite will eventually equip each bus with an IoT device to send data via Kafka, emulating a SmartBus System. Every bus, equipped with a sensor, becomes a node in a decentralized network. The persistence layer, undecided for now, will be evaluated among CSV, HDF5, SurrealDB, and JSON during the simulation and testing phase.

Our suite, comprising SmartBus, AirQuality, and SmartStation, employs real-time data analytics to transform urban mobility and environmental monitoring. Utilizing data from public transport and environmental sensors, our applications aim to improve urban living by enhancing transportation efficiency and environmental health.

#### SmartBus System:

This component gathers operational data from buses, including location, speed, and passenger count, using a Producer module. The SmartBus Processor then processes this data to optimize routes, reduce wait times, and improve the passenger experience. Our goal is a seamless and efficient public transport system responsive to the dynamic urban environment.

#### AirQuality Monitoring:

Dedicated to collecting and analyzing air quality data, this application tracks pollutants, temperature, and humidity levels. The AirQuality Processor identifies trends and areas of concern, while the Persister module ensures long-term data storage for analysis and policy development, aiming for healthier urban environments through detailed air quality insights.

#### SmartStation Management:

This component improves transport station operations by collecting data on foot traffic, ticket sales, and vehicle movements. The SmartStation Consumer uses this data to enhance service provision and passenger satisfaction, streamlining station management and public transport experiences.

#### Infrastructure and Deployment:

Our docker-compose.yml configuration demonstrates a commitment to scalable and efficient deployment, orchestrating containerized components for seamless networking and resource allocation. This facilitates easy scalability and maintenance, allowing our solutions to evolve with urban demands.

### Kafka and Docker Overview

- **Each Consumer, Producer, and Processor has a dedicated Dockerfile and runs in its own container, ensuring modularity and isolation.**

### Component Responsibilities:

- **Producer Components**: Collect real-time data from buses, environmental sensors, and stations.
- **Processor Components**: Analyze collected data for patterns, optimizations, and insights.
- **Consumer Component**: Implements operational changes based on analyzed data.
- **Persister Component**: Stores processed data for historical analysis and policy support.

### Component Interfaces:

- **Producers and Processors** interface with data sources and messaging systems like Kafka.
- **Processors and Consumers** process data from Kafka, act on insights, or publish results.
- **Persisters** interface with storage systems, storing data from Kafka.

### Rationale and Design Decisions:

- **Kafka** is selected for its high-throughput and real-time data stream handling capabilities.
- **Docker** ensures consistent deployments across different environments.
- **Microservices Architecture**: Enhances scalability and allows for independent component deployment.
- **Python Libraries**: Utilize `confluent-kafka` for efficient Kafka integration and data processing libraries for analysis.
- **Kafka Configurations**: Topics and clusters are configured for efficient data management.

### Kafka and Docker Configurations:

- **Topics**: Organize data flow with separate topics for raw and processed data.
- **Partitions and Consumer Groups**: Support high throughput and parallel processing.
- **Containerized Applications**: Each component operates in its own container for isolation.
- **docker-compose.yml**: Defines service configurations for deployment and testing.
- **Volumes and Networks**: Ensure data persistence and secure container communication.

## Part 1:

### Solutions and Innovations:

- **Protobuf Integration**: Enhances message serialization efficiency.
- **Kubernetes and Cloud Integration**: Plans for deployment scalability and management.

## Part 2:

### Insights on Consumer Groups and Streams:

- Demonstrates scalability and parallel processing capabilities.
- Utilizes Faust for stream processing, emphasizing real-time analytics.

## Part 3:

### Explorations in ZeroMQ and ZenOH:

- Highlights ZeroMQ's broker-less model and ZenOH's edge computing advantages.
- Discusses the benefits and challenges of integrating Kafka with these technologies.

## Part 4:

### Performance Benchmarks:

- **Experiment 1**: Compares JSON and Protobuf serializers, indicating slight advantages for Protobuf.
- **Experiment 2**: Investigates data persistence bottlenecks, comparing batch sizes.
- **Further Experiments**: Examine various aspects of system performance, including database choices and Kafka configurations.

### Reflections:

- The documentation reflects on the selection and integration

 of technologies, emphasizing their role in enhancing urban mobility and environmental monitoring. The exploration of serialization formats, messaging frameworks, and storage solutions illustrates a comprehensive approach to building scalable and efficient systems. The performance benchmarks provide insights into the system's capabilities and inform future development and optimization efforts.