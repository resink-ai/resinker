"""
Configuration loader module for Resinker.
"""

import yaml
import os
import logging
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, field_validator, ValidationError
from datetime import datetime, timedelta
from dateutil import parser as date_parser
import re

logger = logging.getLogger(__name__)

# Regex for duration strings (e.g., "10s", "5m", "2h")
DURATION_PATTERN = re.compile(r"^(\d+)([smh])$")
DURATION_UNITS = {"s": "seconds", "m": "minutes", "h": "hours"}


class TimeProgressionSettings(BaseModel):
    """Time progression settings for the simulation."""

    start_time: str = "now"  # ISO 8601 or "now"
    time_multiplier: float = Field(default=1.0, ge=0.0)

    @field_validator("start_time")
    def validate_start_time(cls, v):
        if v.lower() == "now":
            return v
        try:
            date_parser.parse(v)
            return v
        except Exception as e:
            raise ValueError(f"Invalid start_time format. Use ISO 8601 or 'now': {e}")


class SimulationSettings(BaseModel):
    """Global simulation settings."""

    duration: Optional[str] = None
    total_events: Optional[int] = None
    initial_entity_counts: Dict[str, int] = Field(default_factory=dict)
    time_progression: TimeProgressionSettings = Field(
        default_factory=TimeProgressionSettings
    )
    random_seed: Optional[int] = None

    @field_validator("duration")
    def validate_duration(cls, v):
        if v is None:
            return v

        match = DURATION_PATTERN.match(v)
        if not match:
            raise ValueError(
                f"Invalid duration format. Use '<number><unit>' where unit is s, m, or h. Example: '30m', '1h', '10s'"
            )

        return v

    def get_duration_seconds(self) -> Optional[float]:
        """Convert duration string to seconds."""
        if self.duration is None:
            return None

        match = DURATION_PATTERN.match(self.duration)
        if match:
            value, unit = match.groups()
            seconds = int(value) * {"s": 1, "m": 60, "h": 3600}[unit]
            return seconds
        return None

    def get_start_time(self) -> datetime:
        """Get the simulation start time as a datetime object."""
        if self.time_progression.start_time.lower() == "now":
            return datetime.now()
        return date_parser.parse(self.time_progression.start_time)


class SchemaDefinition(BaseModel):
    """Schema definitions for data types."""

    type: str
    format: Optional[str] = None
    generator: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None
    items: Optional[Dict[str, Any]] = None
    min_items: Optional[int] = None
    max_items: Optional[int] = None
    nullable_probability: Optional[float] = None
    from_entity: Optional[str] = None
    field: Optional[str] = None


class StateAttribute(BaseModel):
    """Definition of entity state attributes."""

    type: str
    default: Optional[Any] = None
    nullable: bool = False
    precision: Optional[int] = None
    from_field: Optional[str] = None


class EntityDefinition(BaseModel):
    """Definition of an entity in the system."""

    schema_ref: str = Field(alias="schema")
    primary_key: str
    state_attributes: Dict[str, Dict[str, Any]] = Field(default_factory=dict)


class SelectionFilter(BaseModel):
    """Filter for selecting entities based on their state."""

    field: str
    operator: str
    value: Any


class EntityConsumption(BaseModel):
    """Definition of entity consumption for an event."""

    name: str
    alias: str
    selection_filter: List[SelectionFilter] = Field(default_factory=list)
    min_required: int = 1


class EntityStateUpdate(BaseModel):
    """Update to an entity's state."""

    entity_alias: str
    set_attributes: Dict[str, Any] = Field(default_factory=dict)
    increment_attributes: Dict[str, Any] = Field(default_factory=dict)


class EventTypeDefinition(BaseModel):
    """Definition of an event type."""

    payload_schema: str
    produces_entity: Optional[str] = None
    produces_or_updates_entity: Optional[str] = None
    update_existing_probability: Optional[float] = None
    consumes_entities: List[EntityConsumption] = Field(default_factory=list)
    updates_entity_state: List[EntityStateUpdate] = Field(default_factory=list)
    frequency_weight: float = 1.0


class ScenarioStep(BaseModel):
    """Step in a scenario."""

    event_type: str
    payload_overrides: Dict[str, Any] = Field(default_factory=dict)


class ScenarioEntityRequirement(BaseModel):
    """Requirement for an entity to start a scenario."""

    name: str
    alias: str
    selection_filter: List[SelectionFilter] = Field(default_factory=list)


class ScenarioDefinition(BaseModel):
    """Definition of a scenario."""

    description: str
    initiation_weight: float = 1.0
    requires_initial_entities: List[ScenarioEntityRequirement] = Field(
        default_factory=list
    )
    steps: List[ScenarioStep] = Field(default_factory=list)


class OutputConfiguration(BaseModel):
    """Configuration for an output destination."""

    type: str
    enabled: bool = True
    topic_mapping: Dict[str, str] = Field(default_factory=dict)
    format: str = "json"
    # Kafka specific configs
    kafka_brokers: Optional[str] = None
    security_protocol: Optional[str] = None
    sasl_mechanism: Optional[str] = None
    sasl_plain_username: Optional[str] = None
    sasl_plain_password: Optional[str] = None
    # File specific configs
    file_path: Optional[str] = None
    file_rotation: Optional[str] = None


class ResinkerConfig(BaseModel):
    """Root configuration for Resinker."""

    version: str = "1.0"
    simulation_settings: SimulationSettings = Field(default_factory=SimulationSettings)
    schemas: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    entities: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    event_types: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    scenarios: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    outputs: List[Dict[str, Any]] = Field(default_factory=list)


def load_config(config_path: str) -> ResinkerConfig:
    """
    Load and validate the configuration from a YAML file.

    Args:
        config_path: Path to the YAML configuration file

    Returns:
        ResinkerConfig: The validated configuration object
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    try:
        with open(config_path, "r") as f:
            config_dict = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing YAML configuration: {e}")

    try:
        config = ResinkerConfig(**config_dict)
        return config
    except ValidationError as e:
        # Enhance error messages with context
        msg = f"Configuration validation error: {e}"
        logger.error(msg)
        raise ValueError(msg)
