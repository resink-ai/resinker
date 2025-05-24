"""
Kafka output handler module.
"""

import logging
import json
from typing import Dict, Any, Optional
from kafka import KafkaProducer

from resinker.core.orchestrator import Event

logger = logging.getLogger(__name__)


class KafkaOutputHandler:
    """Handler for outputting events to Kafka topics."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.topic_mapping = config.get("topic_mapping", {})
        self.default_topic = config.get("default_topic", "events")

        # Kafka configuration
        self.kafka_brokers = config.get("kafka_brokers", "localhost:9092")

        # Optional security settings
        self.security_protocol = config.get("security_protocol")
        self.sasl_mechanism = config.get("sasl_mechanism")
        self.sasl_plain_username = config.get("sasl_plain_username")
        self.sasl_plain_password = config.get("sasl_plain_password")

        # Initialize the Kafka producer
        self.producer = self._create_kafka_producer()

    def _create_kafka_producer(self) -> Optional[KafkaProducer]:
        """Create a Kafka producer with the configured settings."""
        producer_config = {
            "bootstrap_servers": self.kafka_brokers,
            "value_serializer": lambda v: json.dumps(v).encode("utf-8"),
        }

        # Add security configuration if provided
        if self.security_protocol:
            producer_config["security_protocol"] = self.security_protocol

        if self.sasl_mechanism:
            producer_config["sasl_mechanism"] = self.sasl_mechanism

        if self.sasl_plain_username and self.sasl_plain_password:
            producer_config["sasl_plain_username"] = self.sasl_plain_username
            producer_config["sasl_plain_password"] = self.sasl_plain_password

        try:
            return KafkaProducer(**producer_config)
        except Exception as e:
            logger.error(f"Failed to create Kafka producer: {e}")
            return None

    def emit_event(self, event: Event):
        """Emit an event to the appropriate Kafka topic."""
        if not self.producer:
            logger.warning("Kafka producer not available, skipping event emission")
            return

        # Determine the target topic
        topic = self.topic_mapping.get(event.event_type, self.default_topic)

        # Send the event
        try:
            future = self.producer.send(topic, event.to_dict())
            # Optional: Wait for the send to complete
            # future.get(timeout=10)
            logger.debug(f"Sent event to Kafka topic: {topic}")
        except Exception as e:
            logger.error(f"Failed to send event to Kafka topic {topic}: {e}")

    def __del__(self):
        """Cleanup when the handler is destroyed."""
        if hasattr(self, "producer") and self.producer:
            try:
                self.producer.flush()
                self.producer.close()
            except Exception as e:
                logger.error(f"Error closing Kafka producer: {e}")
