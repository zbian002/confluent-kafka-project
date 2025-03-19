#!/bin/bash

# Root directory of the project
ROOT_DIR=$(pwd)

# Path to docker-compose.yml
DOCKER_COMPOSE_FILE="${ROOT_DIR}/Dockerfile/docker-compose.yml"

# Step 1: Start Kafka and Schema Registry using Docker Compose
echo "Starting Kafka and Schema Registry with Docker Compose..."
if [ ! -f "$DOCKER_COMPOSE_FILE" ]; then
  echo "Error: docker-compose.yml not found at $DOCKER_COMPOSE_FILE"
  exit 1
fi

docker-compose -f "$DOCKER_COMPOSE_FILE" up -d

# Wait for Kafka to be ready
echo "Waiting for Kafka to be ready..."
sleep 10

# Step 2: Create Kafka topics
echo "Creating Kafka topic: user-login-processed..."
docker exec -it docker-kafka-kafka-1 kafka-topics --create \
  --topic user-login-processed \
  --bootstrap-server localhost:29092 \
  --partitions 1 \
  --replication-factor 1

echo "Creating Kafka topic: user-login-dlq..."
docker exec -it docker-kafka-kafka-1 kafka-topics --create \
  --topic user-login-dlq \
  --bootstrap-server localhost:29092 \
  --partitions 1 \
  --replication-factor 1

# Step 3: Register the schema from user_login.avsc
echo "Registering schema from user_login.avsc..."
SCHEMA_REGISTRY_URL="http://localhost:8081"
SCHEMA_FILE="${ROOT_DIR}/src/kafka/schema/user_login.avsc"

# Check if the schema file exists
if [ ! -f "$SCHEMA_FILE" ]; then
  echo "Schema file not found: $SCHEMA_FILE"
  exit 1
fi

# Register the schema using curl
curl -X POST -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  --data @"$SCHEMA_FILE" \
  "$SCHEMA_REGISTRY_URL/subjects/user-login-value/versions"

# Step 4: Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

echo "Setup completed successfully!"