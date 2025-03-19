# Kafka Data Pipeline Project

This project implements a Kafka-based data pipeline for processing user login events. It includes a Kafka consumer that processes incoming data, validates it against a schema, handles missing fields, and produces processed data to an output topic. Faulty messages are sent to a Dead Letter Queue (DLQ) for further investigation.

## Table of Contents
1. [Project Overview](#project-overview)
2. [Setup Instructions](#setup-instructions)
3. [Running the Pipeline](#running-the-pipeline)
4. [Design Choices](#design-choices)
5. [Data Flow](#data-flow)
6. [Efficiency, Scalability, and Fault Tolerance](#efficiency-scalability-and-fault-tolerance)
7. [Production Deployment](#production-deployment)
8. [Production-Ready Components](#production-ready-components)
9. [Scaling with a Growing Dataset](#scaling-with-a-growing-dataset)
10. [License](#license)

## Project Overview
The pipeline consists of the following components:
- **Kafka**: A distributed streaming platform used to handle real-time data feeds.
- **Schema Registry**: Manages Avro schemas for data validation.
- **Kafka Consumer**: Processes incoming user login events, validates them, and produces processed data to an output topic.
- **Dead Letter Queue (DLQ)**: Stores messages that fail validation or processing for further analysis.
- **Docker**: Used to containerize Kafka, Zookeeper, and Schema Registry for easy setup and deployment.

## Setup Instructions
### Prerequisites
- **Python 3.7.8**: Ensure Python 3.7.8 is installed on your system.
- **Docker**: Install Docker to run Kafka, Zookeeper, and Schema Registry.
- **Docker Compose**: Install Docker Compose to manage multi-container Docker applications.

### Steps to Set Up
1. **Clone the Repository**:
   ```bash
   git clone git@github.com:zbian002/confluent-kafka-project.git
   cd confluent-kafka-project
2. **Set Up the Environment**
Ensure Python 3.7.8 is installed. You can use pyenv or any other version manager to install it:
    ```bash
   brew install pyenv
    pyenv install 3.7.8
    pyenv local 3.7.8
3. **Run the Setup Script**
Make the `setup.sh` script executable and run it:
   ```bash 
    chmod +x setup.sh
    ./setup.shThis script will:
- Start Kafka, Zookeeper, and Schema Registry using Docker Compose.
- Create the required Kafka topics (`user-login-processed` and `user-login-dlq`).
- Register the Avro schema from `src/kafka/schema/user_login.avsc`.
- Install Python dependencies from `requirements.txt`.
- Run the test suite to verify the setup.

4. **Verify the Setup**
    - Check that the Kafka topics were created:
    ```bash   
    docker exec -it docker-kafka-kafka-1 kafka-topics --list --bootstrap-server localhost:29092    
    ```
   - Verify that the schema was registered:
    ```bash 
    curl http://localhost:8081/subjects/user-login-value/versions/1
## Running the Pipeline
1. Start the Kafka Consumer
    - The `setup.sh` script automatically starts the Kafka consumer. If you need to restart it, run:
        ```bash 
        python3 src/kafka/kafka_consumer.py
   
2. Produce Test Data
    - Use a Kafka producer (e.g., `kafka-console-producer`) to send test messages to the `user-login` topic:
        ```bash   
        docker exec -it docker-kafka-kafka-1 kafka-console-producer \
        --topic user-login \
        --bootstrap-server localhost:29092
   - Example message:
        ```bash 
        {"user_id": "123", "app_version": "1.0.0", "ip": "162.255.195.202", "locale": "NE", "device_id": "0bcbfec0-02c4-496c-99ac-35d0cc750f6b", "timestamp": 1742331926, "device_type": "android"}
 3. Monitor the Pipeline
    - Check the logs of the Kafka consumer to ensure messages are being processed.
    - Inspect the `user-login-processed` topic for successfully processed messages.
    - Inspect the `user-login-dlq` topic for any failed messages.

## Design Choices
### 1. Schema Validation
**Why**: Ensures that incoming data adheres to a predefined structure, reducing the risk of processing invalid data.
**How**: The pipeline uses Avro schemas registered in the Schema Registry. The `validate_data` function checks each message against the schema.

### 2. Dead Letter Queue (DLQ)
**Why**: Provides a mechanism to handle faulty messages without stopping the pipeline.
**How**: Messages that fail validation or processing are sent to the `user-login-dlq` topic for further investigation.

### 3. Dockerized Environment
**Why**: Simplifies setup and ensures consistency across different environments.
**How**: Kafka, Zookeeper, and Schema Registry are containerized using Docker Compose.

### 4. Fault Tolerance
**Why**: Ensures the pipeline can recover from failures and continue processing.
**How**: Kafka's built-in replication and consumer offset tracking ensure that messages are not lost even if a consumer fails.

## Data Flow
- **Producer**: Sends user login events to the `user-login` topic.
- **Consumer**:
    - Fetches messages from the `user-login` topic.
    - Validates each message against the Avro schema.
    - Handles missing fields by assigning default values.
    - Processes the data (e.g., formatting timestamps).
    - Produces processed data to the `user-login-processed` topic.
    - Sends faulty messages to the `user-login-dlq` topic.
- **DLQ**: Stores messages that fail validation or processing for manual review.

## Efficiency, Scalability, and Fault Tolerance
### Efficiency
- **Batch Processing**: Kafka consumers can process messages in batches, reducing overhead.
- **Schema Validation**: FastAvro is used for efficient schema validation.

### Scalability
- **Kafka Partitions**: The pipeline can scale horizontally by increasing the number of partitions for each topic.
- **Consumer Groups**: Multiple consumers can be added to a consumer group to parallelize processing.

### Fault Tolerance
- **Kafka Replication**: Topics are replicated across multiple brokers to prevent data loss.
- **Consumer Offsets**: Kafka tracks the last processed offset for each consumer, ensuring that messages are not lost if a consumer fails.
- **DLQ**: Faulty messages are isolated in the DLQ, allowing the pipeline to continue processing valid messages.

## Production Deployment
### Container Orchestration
- Use Kubernetes or Docker Swarm to manage Kafka, Zookeeper, and Schema Registry containers in a production environment.
- Deploy the Kafka consumer as a Kubernetes Deployment or Docker Service.

### Monitoring and Logging
- Integrate monitoring tools like Prometheus and Grafana to track Kafka metrics (e.g., message throughput, consumer lag).
- Use centralized logging (e.g., ELK Stack or Fluentd) to collect and analyze logs.

### High Availability
- Deploy Kafka and Zookeeper in a multi-node cluster to ensure high availability.
- Use replication factors greater than 1 for Kafka topics to prevent data loss.

### Security
- Enable SSL/TLS encryption for Kafka brokers and clients.
- Use SASL authentication to secure access to Kafka.

## Production-Ready Components
### Monitoring and Alerting
- Add Prometheus and Grafana for real-time monitoring of Kafka metrics.
- Set up alerts for consumer lag, broker failures, and DLQ growth.

### Logging and Tracing
- Use the ELK Stack (Elasticsearch, Logstash, Kibana) for centralized logging.
- Integrate OpenTelemetry or Jaeger for distributed tracing.

### Security
- Enable SSL/TLS for secure communication between Kafka components.
- Use SASL/SCRAM for authentication and ACLs for authorization.

### Automated Testing
- Add CI/CD pipelines (e.g., GitHub Actions, Jenkins) to automate testing and deployment.

### Data Backup
- Implement a backup strategy for Kafka topics using tools like Confluent Replicator or MirrorMaker.

## Scaling with a Growing Dataset
### Increase Kafka Partitions
- Add more partitions to Kafka topics to distribute the load across multiple brokers.
- Ensure the number of partitions matches the number of consumers in the consumer group.

### Horizontal Scaling
- Add more Kafka brokers to the cluster to handle increased message throughput.
- Scale the Kafka consumer horizontally by adding more instances to the consumer group.

### Optimize Consumer Performance
- Use batch processing to reduce the overhead of processing individual messages.
- Tune Kafka consumer configurations (e.g., `fetch.max.bytes`, `max.poll.records`) for better performance.

### Data Retention Policies
- Configure Kafka topic retention policies (e.g., time-based or size-based) to manage disk usage.
- Use tiered storage (e.g., Confluent Tiered Storage) to offload older data to cheaper storage.

### Data Partitioning
- Partition data based on a key (e.g., `user_id`) to ensure even distribution across partitions.
- Use custom partitioners if needed to optimize data distribution.

## License
This project is licensed under the MIT License. See the `LICENSE` file for details.
    