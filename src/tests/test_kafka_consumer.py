import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime
import json
import sys
import os

# Add the src directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

# Import the functions to test
from kafka.kafka_consumer import (
    fetch_schema,
    validate_data,
    handle_missing_fields,
    process_data,
    produce_processed_data,
    send_to_dlq,
)

class TestKafkaFunctions(unittest.TestCase):

    @patch("kafka.kafka_consumer.SchemaRegistryClient")
    def test_fetch_schema(self, mock_schema_registry):
        # Mock the Schema Registry client
        mock_client = MagicMock()
        mock_client.get_latest_version.return_value.schema.schema_str = json.dumps({
            "type": "record",
            "name": "UserLogin",
            "fields": [
                {"name": "user_id", "type": "string"},
                {"name": "app_version", "type": "string"},
                {"name": "ip", "type": "string"},
                {"name": "locale", "type": "string"},
                {"name": "device_id", "type": "string"},
                {"name": "timestamp", "type": "long"},
                {"name": "device_type", "type": "string"}
            ]
        })
        mock_schema_registry.return_value = mock_client

        # Call the function
        schema = fetch_schema()

        # Assert the schema is correctly parsed
        expected_schema = {
            "type": "record",
            "name": "UserLogin",
            "fields": [
                {"name": "user_id", "type": "string"},
                {"name": "app_version", "type": "string"},
                {"name": "ip", "type": "string"},
                {"name": "locale", "type": "string"},
                {"name": "device_id", "type": "string"},
                {"name": "timestamp", "type": "long"},
                {"name": "device_type", "type": "string"}
            ]
        }
        self.assertEqual(schema, expected_schema)

    def test_validate_data(self):
        schema = {
            "type": "record",
            "name": "UserLogin",
            "fields": [
                {"name": "user_id", "type": "string"},
                {"name": "app_version", "type": "string"},
                {"name": "ip", "type": "string"},
                {"name": "locale", "type": "string"},
                {"name": "device_id", "type": "string"},
                {"name": "timestamp", "type": "long"},
                {"name": "device_type", "type": "string"}
            ],
        }

        # Test valid data
        valid_data = {
            "user_id": "123",
            "app_version": "1.0.0",
            "ip": "162.255.195.202",
            "locale": "NE",
            "device_id": "0bcbfec0-02c4-496c-99ac-35d0cc750f6b",
            "timestamp": 1742331926,
            "device_type": "android"
        }
        self.assertTrue(validate_data(valid_data, schema))

        # Test invalid data
        invalid_data = {"user_id": "123"}  # Missing required fields
        self.assertFalse(validate_data(invalid_data, schema))

    def test_handle_missing_fields(self):
        schema = {
            "type": "record",
            "name": "UserLogin",
            "fields": [
                {"name": "user_id", "type": "string"},
                {"name": "app_version", "type": "string"},
                {"name": "ip", "type": "string"},
                {"name": "locale", "type": "string"},
                {"name": "device_id", "type": "string"},
                {"name": "timestamp", "type": "long"},
                {"name": "device_type", "type": "string"}
            ],
        }

        # Test with missing fields
        data = {"user_id": "123"}
        result = handle_missing_fields(data, schema)
        expected_data = {
            "user_id": "123",
            "app_version": "",
            "ip": "",
            "locale": "",
            "device_id": "",
            "timestamp": 0,
            "device_type": ""
        }
        self.assertEqual(result, None)

        # Test with no missing fields
        data = {
            "user_id": "123",
            "app_version": "1.0.0",
            "ip": "162.255.195.202",
            "locale": "NE",
            "device_id": "0bcbfec0-02c4-496c-99ac-35d0cc750f6b",
            "timestamp": 1742331926,
            "device_type": "android"
        }
        result = handle_missing_fields(data, schema)
        self.assertEqual(result, data)

    def test_process_data(self):
        # Test with valid timestamp
        data = {"timestamp": 1742331926}
        processed_data = process_data(data)
        self.assertEqual(processed_data["timestamp"], "2025-03-18 14:05:26")  # Adjusted for local timezone

        # Test with invalid timestamp
        data = {"timestamp": "invalid"}
        processed_data = process_data(data)
        self.assertEqual(processed_data["timestamp"], "1970-01-01 00:00:00")

    @patch("kafka.kafka_consumer.Producer")
    def test_produce_processed_data(self, mock_producer):
        # Mock the Kafka producer
        mock_producer_instance = MagicMock()
        mock_producer.return_value = mock_producer_instance

        # Call the function
        data = {"user_id": "123", "app_version": "1.0.0"}
        produce_processed_data(mock_producer_instance, data)

        # Assert the producer was called correctly
        mock_producer_instance.produce.assert_called_once_with(
            "user-login-processed", value=json.dumps(data).encode("utf-8")
        )
        mock_producer_instance.flush.assert_called_once()

    @patch("kafka.kafka_consumer.Producer")
    def test_send_to_dlq(self, mock_producer):
        # Mock the Kafka producer
        mock_producer_instance = MagicMock()
        mock_producer.return_value = mock_producer_instance

        # Mock the Kafka message
        mock_message = MagicMock()
        mock_message.value.return_value = {"user_id": "123", "app_version": "1.0.0"}

        # Call the function
        send_to_dlq(mock_producer_instance, mock_message, "Test error")

        # Assert the producer was called correctly
        mock_producer_instance.produce.assert_called_once_with(
            "user-login-dlq", value=json.dumps(mock_message.value()).encode("utf-8")
        )
        mock_producer_instance.flush.assert_called_once()

if __name__ == "__main__":
    unittest.main()