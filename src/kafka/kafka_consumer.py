import logging
import json
from datetime import datetime
from confluent_kafka import DeserializingConsumer, Producer, KafkaError
from confluent_kafka.schema_registry import SchemaRegistryClient
from fastavro import validate  # For schema validation

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Kafka configuration
KAFKA_BOOTSTRAP_SERVERS = "localhost:29092"
INPUT_TOPIC = "user-login"
OUTPUT_TOPIC = "user-login-processed"
DLQ_TOPIC = "user-login-dlq"  # Dead Letter Queue topic
GROUP_ID = "user-login-consumer-group"
SCHEMA_REGISTRY_URL = "http://localhost:8081"

# Initialize Schema Registry client
schema_registry_client = SchemaRegistryClient({"url": SCHEMA_REGISTRY_URL})

# Fetch the latest schema for the input topic
def fetch_schema():
    """
    Fetch the latest schema for the input topic from the Schema Registry.
    """
    try:
        schema_str = schema_registry_client.get_latest_version(f"{INPUT_TOPIC}-value").schema.schema_str
        logger.info(f"Fetched schema: {schema_str}")
        return json.loads(schema_str)
    except Exception as e:
        logger.error(f"Failed to fetch schema: {e}")
        raise

# Function to validate data against the schema
def validate_data(data, schema):
    """
    Validate the data against the schema using fastavro.
    Returns True if the data is valid, False otherwise.
    """
    try:
        validate(data, schema)
        return True
    except Exception as e:
        logger.warning(f"Schema validation failed: {e}")
        return False

# Function to handle missing fields
def handle_missing_fields(data, schema):
    """
    Ensure all required fields are present in the data.
    Returns the data with default values for missing fields.
    If required fields are missing, returns None.
    """
    missing_fields = []
    for field in schema["fields"]:
        if field["name"] not in data:
            missing_fields.append(field["name"])
            logger.warning(f"Missing field: {field['name']}")
            if field["type"] == "string":
                data[field["name"]] = ""
            elif field["type"] == "int" or field["type"] == "long":
                data[field["name"]] = 0
            elif field["type"] == "boolean":
                data[field["name"]] = False

    # If any required fields are missing, return None
    if missing_fields:
        return None
    return data

# Function to process data
def process_data(data):
    """
    Process the data (e.g., transform, filter, or aggregate).
    Returns the processed data.
    """
    # Update timestamp format to yyyy-MM-dd HH:mm:ss
    try:
        timestamp = data.get("timestamp")
        if isinstance(timestamp, int):
            # Convert Unix timestamp to formatted string
            data["timestamp"] = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
        else:
            logger.warning(f"Invalid timestamp format: {timestamp}")
            data["timestamp"] = "1970-01-01 00:00:00"  # Default value
    except Exception as e:
        logger.error(f"Failed to format timestamp: {e}")
        data["timestamp"] = "1970-01-01 00:00:00"  # Default value

    return data

# Function to produce processed data to the output topic
def produce_processed_data(producer, data):
    """
    Produce the processed data to the output Kafka topic.
    """
    try:
        producer.produce(OUTPUT_TOPIC, value=json.dumps(data).encode("utf-8"))
        producer.flush()
        logger.info(f"Produced processed data to {OUTPUT_TOPIC}: {data}")
    except Exception as e:
        logger.error(f"Failed to produce processed data: {e}")

# Function to send messages to DLQ
def send_to_dlq(dlq_producer, message, error):
    """
    Send the problematic message to the Dead Letter Queue.
    """
    try:
        dlq_producer.produce(DLQ_TOPIC, value=json.dumps(message.value()).encode("utf-8"))
        dlq_producer.flush()
        logger.error(f"Sent message to DLQ ({DLQ_TOPIC}): {error}")
    except Exception as e:
        logger.error(f"Failed to send message to DLQ: {e}")

# Function to initialize Kafka consumer
def initialize_consumer():
    """
    Initialize and return a Kafka consumer.
    """
    return DeserializingConsumer({
        "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
        "group.id": GROUP_ID,
        "auto.offset.reset": "earliest",
        "value.deserializer": lambda value, ctx: json.loads(value.decode("utf-8"))  # JSON deserializer
    })

# Function to initialize Kafka producer
def initialize_producer():
    """
    Initialize and return a Kafka producer.
    """
    return Producer({"bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS})

# Function to process messages
def process_messages(consumer, producer, dlq_producer, schema):
    """
    Continuously poll for messages, process them, and produce to the output topic or DLQ.
    """
    total_messages = 0

    try:
        logger.info("Starting Kafka consumer...")
        while True:
            # Poll for messages
            message = consumer.poll(1.0)

            if message is None:
                continue

            if message.error():
                if message.error().code() == KafkaError._PARTITION_EOF:
                    # End of partition event
                    logger.info(f"Reached end of partition: {message.partition()}")
                else:
                    logger.error(f"Error: {message.error()}")
                continue

            # Deserialize the message value (assuming JSON format)
            try:
                data = message.value()
                logger.info(f"Received message: {data}")
            except Exception as e:
                logger.error(f"Failed to deserialize message: {e}")
                send_to_dlq(dlq_producer, message, f"Deserialization error: {e}")
                continue

            # Handle missing fields
            data = handle_missing_fields(data, schema)
            if data is None:
                logger.warning("Message has missing required fields. Sending to DLQ.")
                send_to_dlq(dlq_producer, message, "Missing required fields")
                continue

            # Validate the message against the schema
            if not validate_data(data, schema):
                logger.warning("Message does not match the schema. Sending to DLQ.")
                send_to_dlq(dlq_producer, message, "Schema validation failed")
                continue

            # Process the data
            try:
                processed_data = process_data(data)
            except Exception as e:
                logger.error(f"Failed to process data: {e}")
                send_to_dlq(dlq_producer, message, f"Processing error: {e}")
                continue

            # Update insights
            total_messages += 1

            # Produce processed data to the output topic
            produce_processed_data(producer, processed_data)

            # Log insights periodically
            if total_messages % 10 == 0:  # Log every 10 messages
                logger.info(f"Insights: Total messages={total_messages}")

    except KeyboardInterrupt:
        logger.info("Stopping Kafka consumer...")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        # Close the consumer and producers
        consumer.close()
        producer.flush()
        dlq_producer.flush()
        logger.info("Kafka consumer and producers closed.")

# Main function
def main():
    # Fetch the schema
    schema = fetch_schema()

    # Initialize Kafka consumer and producers
    consumer = initialize_consumer()
    producer = initialize_producer()
    dlq_producer = initialize_producer()

    # Subscribe to the input topic
    consumer.subscribe([INPUT_TOPIC])

    # Process messages
    process_messages(consumer, producer, dlq_producer, schema)

# Entry point
if __name__ == "__main__":
    main()