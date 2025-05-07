"""
Orchestrator module for managing event generation.
"""

import logging
import random
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from faker import Faker
import heapq
import json

from resinker.config.loader import ResinkerConfig
from resinker.core.state_manager import StateManager
from resinker.generators.generators import SchemaGenerator
from resinker.generators.providers import EcommerceProvider

logger = logging.getLogger(__name__)


class Event:
    """Represents a generated event."""

    def __init__(self, event_type: str, payload: Dict[str, Any], timestamp: datetime):
        self.event_type = event_type
        self.payload = payload
        self.timestamp = timestamp

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to a dictionary."""
        return {
            "event_type": self.event_type,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
        }

    def __str__(self) -> str:
        """String representation of the event."""
        return json.dumps(self.to_dict(), indent=2)


class ScheduledEvent:
    """Event scheduled for future generation."""

    def __init__(
        self, event_type: str, scheduled_time: datetime, context: Dict[str, Any] = None
    ):
        self.event_type = event_type
        self.scheduled_time = scheduled_time
        self.context = context or {}

    def __lt__(self, other):
        """Comparison for priority queue."""
        return self.scheduled_time < other.scheduled_time


class ScenarioInstance:
    """An instance of a running scenario."""

    def __init__(self, scenario_name: str, context: Dict[str, Any] = None):
        self.scenario_name = scenario_name
        self.context = context or {}
        self.current_step = 0
        self.completed = False
        self.entity_aliases = {}  # Maps aliases to entity IDs

    def advance_step(self):
        """Advance to the next step in the scenario."""
        self.current_step += 1


class Orchestrator:
    """Orchestrates the generation of events based on configuration."""

    def __init__(self, config: ResinkerConfig):
        self.config = config
        self.state_manager = StateManager()

        # Set random seed if specified
        if config.simulation_settings.random_seed is not None:
            random.seed(config.simulation_settings.random_seed)

        # Initialize Faker with the same seed
        self.faker = Faker()
        if config.simulation_settings.random_seed is not None:
            self.faker.seed_instance(config.simulation_settings.random_seed)

        # Register custom providers
        self.faker.add_provider(EcommerceProvider)

        # Initialize the schema registry
        self.schema_registry = config.schemas

        # Create schema generator
        self.schema_generator = SchemaGenerator(
            self.faker, self.state_manager, self.schema_registry
        )

        # Initialize entity primary keys
        self.entity_primary_keys = {}
        for entity_name, entity_def in config.entities.items():
            self.entity_primary_keys[entity_name] = entity_def["primary_key"]

        # Initialize simulation time
        self.simulation_start_time = config.simulation_settings.get_start_time()
        self.simulation_time = self.simulation_start_time
        self.time_multiplier = (
            config.simulation_settings.time_progression.time_multiplier
        )

        # Event scheduling
        self.event_queue = []  # Priority queue of scheduled events
        self.active_scenarios = []  # List of active scenario instances

        # Output handlers
        self.output_handlers = []
        for output_config in config.outputs:
            if output_config.get("enabled", True):
                handler = self._create_output_handler(output_config)
                if handler:
                    self.output_handlers.append(handler)

    def initialize(self):
        """Initialize the simulation state."""
        logger.info("Initializing simulation...")

        # Create initial entities
        for (
            entity_type,
            count,
        ) in self.config.simulation_settings.initial_entity_counts.items():
            logger.info(f"Creating {count} initial {entity_type} entities")
            self._create_initial_entities(entity_type, count)

        # Schedule initial events based on frequency weights
        self._schedule_initial_events()

        # Initialize active scenarios
        self._initialize_scenarios()

        logger.info(f"Simulation initialized. Starting at: {self.simulation_time}")

    def run(self):
        """Run the simulation."""
        logger.info("Starting simulation...")

        start_time = time.time()
        event_count = 0

        # Get simulation duration in seconds
        duration_seconds = self.config.simulation_settings.get_duration_seconds()
        total_events = self.config.simulation_settings.total_events

        # Main simulation loop
        while True:
            # Check termination conditions
            elapsed_sim_time = (
                self.simulation_time - self.simulation_start_time
            ).total_seconds()

            if duration_seconds is not None and elapsed_sim_time >= duration_seconds:
                logger.info(f"Simulation duration reached: {duration_seconds} seconds")
                break

            if total_events is not None and event_count >= total_events:
                logger.info(f"Total events limit reached: {total_events} events")
                break

            # Process the next event from the queue
            if not self.event_queue:
                logger.info("Event queue empty, scheduling more events...")
                self._schedule_additional_events()

                if not self.event_queue:
                    logger.warning(
                        "No more events can be scheduled. Ending simulation."
                    )
                    break

            # Get the next event from the queue
            scheduled_event = heapq.heappop(self.event_queue)

            # Advance simulation time
            self.simulation_time = scheduled_event.scheduled_time

            # Generate and emit the event
            event = self._generate_event(scheduled_event)
            if event:
                self._emit_event(event)
                event_count += 1

                # Log progress
                if event_count % 100 == 0:
                    logger.info(
                        f"Generated {event_count} events. Current simulation time: {self.simulation_time}"
                    )

            # Process active scenarios
            self._process_scenarios()

            # Schedule more events
            if len(self.event_queue) < 100:  # Keep the queue populated
                self._schedule_additional_events()

        # Simulation complete
        real_elapsed = time.time() - start_time
        logger.info(
            f"Simulation complete. Generated {event_count} events in {real_elapsed:.2f} seconds."
        )

    def _create_initial_entities(self, entity_type: str, count: int):
        """Create initial entities of the specified type."""
        if entity_type not in self.config.entities:
            logger.warning(f"Unknown entity type: {entity_type}")
            return

        entity_def = self.config.entities[entity_type]
        schema_ref = entity_def.get("schema_ref", entity_def.get("schema"))

        # Extract the schema name from the reference
        if schema_ref.startswith("#/schemas/"):
            schema_name = schema_ref[len("#/schemas/") :]
        else:
            schema_name = schema_ref

        if schema_name not in self.schema_registry:
            logger.warning(f"Schema not found: {schema_name}")
            return

        schema = self.schema_registry[schema_name]
        primary_key = entity_def["primary_key"]

        logger.debug(
            f"[EntityInit] Creating {count} entities of type '{entity_type}' with schema '{schema_name}' and primary key '{primary_key}'"
        )
        # Create entities
        for i in range(count):
            # Generate entity data
            logger.debug(
                f"[EntityInit] Generating entity {i+1}/{count} for type '{entity_type}' with context: {{'simulation_time': {self.simulation_time}}}"
            )
            entity_data = self.schema_generator.generate(
                schema, {"simulation_time": self.simulation_time}
            )
            # Create the entity
            entity = self.state_manager.create_entity(
                entity_type, entity_data, primary_key
            )

            # Initialize state attributes
            self._initialize_entity_state_attributes(
                entity_type, entity, entity_data, "EntityInit"
            )

    def _schedule_initial_events(self):
        """Schedule initial events based on frequency weights."""
        # Get all event types
        event_types = list(self.config.event_types.keys())

        # Calculate weights
        weights = []
        for event_type in event_types:
            weight = self.config.event_types[event_type].get("frequency_weight", 1.0)
            weights.append(weight)

        # Schedule some initial events
        for _ in range(10):  # Start with 10 events
            if not event_types:
                break

            # Choose an event type based on weights
            event_type = random.choices(event_types, weights=weights, k=1)[0]

            # Schedule it with a random delay
            delay = random.uniform(0, 60)  # 0 to 60 seconds
            scheduled_time = self.simulation_time + timedelta(seconds=delay)

            scheduled_event = ScheduledEvent(event_type, scheduled_time)
            heapq.heappush(self.event_queue, scheduled_event)

    def _schedule_additional_events(self):
        """Schedule additional events based on current state."""
        # Get all event types
        event_types = list(self.config.event_types.keys())

        # Calculate weights and filter events that can be generated
        valid_events = []
        valid_weights = []

        for event_type in event_types:
            # Check if this event can be generated
            if self._can_generate_event(event_type):
                weight = self.config.event_types[event_type].get(
                    "frequency_weight", 1.0
                )
                valid_events.append(event_type)
                valid_weights.append(weight)

        # Schedule some new events
        for _ in range(10):  # Add 10 events at a time
            if not valid_events:
                break

            # Choose an event type based on weights
            event_type = random.choices(valid_events, weights=valid_weights, k=1)[0]

            # Schedule it with a random delay
            delay = random.uniform(10, 300)  # 10 to 300 seconds
            scheduled_time = self.simulation_time + timedelta(seconds=delay)

            scheduled_event = ScheduledEvent(event_type, scheduled_time)
            heapq.heappush(self.event_queue, scheduled_event)

    def _can_generate_event(self, event_type: str) -> bool:
        """Check if an event of the given type can be generated."""
        if event_type not in self.config.event_types:
            return False

        event_def = self.config.event_types[event_type]

        # Check if the event consumes entities
        if "consumes_entities" in event_def:
            for consumption in event_def["consumes_entities"]:
                entity_type = consumption["name"]
                selection_filter = consumption.get("selection_filter", [])
                min_required = consumption.get("min_required", 1)

                # Convert selection_filter to the format expected by state_manager
                filter_list = []
                for filter_item in selection_filter:
                    filter_list.append(
                        {
                            "field": filter_item["field"],
                            "operator": filter_item["operator"],
                            "value": filter_item["value"],
                        }
                    )

                # Check if we have enough entities of this type
                entity_count = self.state_manager.count_entities(
                    entity_type, filter_list
                )
                if entity_count < min_required:
                    return False

        return True

    def _generate_event(self, scheduled_event: ScheduledEvent) -> Optional[Event]:
        """Generate an event of the given type."""
        event_type = scheduled_event.event_type
        logger.debug(
            f"[EventGen] Generating event of type '{event_type}' at simulation time {self.simulation_time} with scheduled_event context: {scheduled_event.context}"
        )

        if event_type not in self.config.event_types:
            logger.warning(f"Unknown event type: {event_type}")
            return None

        event_def = self.config.event_types[event_type]

        # Create context for event generation
        context = scheduled_event.context.copy()
        context["simulation_time"] = self.simulation_time
        logger.debug(
            f"[EventGen] Event context after adding simulation_time: {context}"
        )

        # Process entity consumption
        consumed_entities = {}
        if "consumes_entities" in event_def:
            for consumption in event_def["consumes_entities"]:
                entity_type = consumption["name"]
                alias = consumption["alias"]
                selection_filter = consumption.get("selection_filter", [])
                min_required = consumption.get("min_required", 1)
                logger.debug(
                    f"[EventGen] Consuming entities: type={entity_type}, alias={alias}, selection_filter={selection_filter}, min_required={min_required}"
                )

                # Convert selection_filter to the format expected by state_manager
                filter_list = []
                for filter_item in selection_filter:
                    filter_list.append(
                        {
                            "field": filter_item["field"],
                            "operator": filter_item["operator"],
                            "value": filter_item["value"],
                        }
                    )

                # Find matching entities
                entities = self.state_manager.find_entities(entity_type, filter_list)
                logger.debug(
                    f"[EventGen] Found {len(entities)} entities for type '{entity_type}' with filter {filter_list}"
                )

                if len(entities) < min_required:
                    logger.debug(
                        f"[EventGen] Not enough entities of type {entity_type} for event {event_type}. Required: {min_required}, Found: {len(entities)}"
                    )
                    return None

                # Store the consumed entities
                consumed_entities[alias] = entities[:min_required]

                # Add to context for payload generation
                if min_required == 1:
                    context[f"entity_{alias}"] = entities[0]
                else:
                    context[f"entity_{alias}"] = entities[:min_required]

        context["consumed_entities"] = consumed_entities
        logger.debug(f"[EventGen] Consumed entities: {consumed_entities}")

        # Generate the payload
        payload_schema_ref = event_def["payload_schema"]
        if payload_schema_ref.startswith("#/schemas/"):
            schema_name = payload_schema_ref[len("#/schemas/") :]
        else:
            schema_name = payload_schema_ref

        if schema_name not in self.schema_registry:
            logger.warning(f"Schema not found: {schema_name}")
            return None

        schema = self.schema_registry[schema_name]

        # Apply scenario overrides if available
        if "payload_overrides" in context:
            for key, value in context["payload_overrides"].items():
                if "properties" in schema and key in schema["properties"]:
                    schema["properties"][key]["value"] = value

        logger.debug(
            f"[EventGen] Generating payload for event '{event_type}' using schema '{schema_name}' and context: {context}"
        )
        payload = self.schema_generator.generate(schema, context)

        # Create the event
        event = Event(event_type, payload, self.simulation_time)
        logger.debug(f"[EventGen] Created event: {event}")

        # Process entity production
        if "produces_entity" in event_def:
            entity_type = event_def["produces_entity"]
            if entity_type in self.entity_primary_keys:
                primary_key = self.entity_primary_keys[entity_type]
                entity = self.state_manager.create_entity(
                    entity_type, payload, primary_key
                )
                logger.debug(
                    f"[produces_entity] Created entity {entity_type} with ID {entity.id}"
                )

                # Initialize state attributes
                self._initialize_entity_state_attributes(
                    entity_type, entity, payload, "produces_entity"
                )

                # Save entity in context for potential state updates
                context[f"entity_{entity_type}"] = entity

                # If this is part of a scenario, store the entity alias
                if "scenario_instance" in context and "entity_alias" in context:
                    scenario = context["scenario_instance"]
                    alias = context["entity_alias"]
                    scenario.entity_aliases[alias] = entity.id

        # Process entity updates
        if "produces_or_updates_entity" in event_def:
            entity_type = event_def["produces_or_updates_entity"]
            update_prob = event_def.get("update_existing_probability", 0.5)

            # Decide whether to update an existing entity or create a new one
            update_existing = random.random() < update_prob

            if update_existing:
                # Find an existing entity to update
                entities = self.state_manager.get_all_entities(entity_type)
                if entities:
                    entity = random.choice(entities)
                    self.state_manager.update_entity(entity_type, entity.id, payload)
                    logger.debug(f"Updated entity {entity_type} with ID {entity.id}")

                    # Save entity in context for potential state updates
                    context[f"entity_{entity_type}"] = entity
                else:
                    # No existing entities, create a new one
                    update_existing = False

            if not update_existing:
                # Create a new entity
                if entity_type in self.entity_primary_keys:
                    primary_key = self.entity_primary_keys[entity_type]
                    entity = self.state_manager.create_entity(
                        entity_type, payload, primary_key
                    )
                    logger.debug(
                        f"[produces_or_updates_entity] Created entity {entity_type} with ID {entity.id}"
                    )

                    # Initialize state attributes
                    self._initialize_entity_state_attributes(
                        entity_type, entity, payload, "produces_or_updates_entity"
                    )

                    # Save entity in context for potential state updates
                    context[f"entity_{entity_type}"] = entity

        # Process entity state updates
        if "updates_entity_state" in event_def:
            for update in event_def["updates_entity_state"]:
                entity_alias = update["entity_alias"]
                set_attributes = update.get("set_attributes", {})
                increment_attributes = update.get("increment_attributes", {})

                # Find the entity to update
                entity = None

                # First check if it's in the context
                if f"entity_{entity_alias}" in context:
                    entity = context[f"entity_{entity_alias}"]
                elif entity_alias in consumed_entities:
                    entities = consumed_entities[entity_alias]
                    if entities:
                        entity = entities[0]  # Use the first entity

                if entity is None:
                    logger.warning(
                        f"Entity with alias {entity_alias} not found for state update"
                    )
                    continue

                # Process attribute values
                processed_set_attributes = {}
                for attr, value in set_attributes.items():
                    if isinstance(value, dict) and "from_payload_field" in value:
                        field_name = value["from_payload_field"]
                        field_value = self._get_nested_value(payload, field_name)
                        processed_set_attributes[attr] = field_value
                    else:
                        processed_set_attributes[attr] = value

                processed_increment_attributes = {}
                for attr, value in increment_attributes.items():
                    if isinstance(value, dict) and "from_payload_field" in value:
                        field_name = value["from_payload_field"]
                        field_value = self._get_nested_value(payload, field_name)
                        processed_increment_attributes[attr] = field_value
                    else:
                        processed_increment_attributes[attr] = value

                # Update the entity state
                self.state_manager.update_entity_state(
                    entity.entity_type,
                    entity.id,
                    processed_set_attributes,
                    processed_increment_attributes,
                )

        return event

    def _get_nested_value(self, obj, path):
        """Get a value from a nested object using a dot-separated path."""
        parts = path.split(".")
        value = obj
        for part in parts:
            if value is None:
                return None
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return None
        return value

    def _initialize_entity_state_attributes(
        self, entity_type: str, entity, data: Dict[str, Any], log_prefix: str = ""
    ):
        """Initialize state attributes for a newly created entity.

        Args:
            entity_type: The type of entity
            entity: The entity instance
            data: The data dictionary containing field values
            log_prefix: Prefix for log messages
        """
        if entity_type not in self.config.entities:
            return

        entity_def = self.config.entities[entity_type]
        state_attributes = entity_def.get("state_attributes", {})

        for attr_name, attr_def in state_attributes.items():
            if attr_def.get("from_field"):
                field_name = attr_def["from_field"]
                if field_name in data:
                    entity.set_state(attr_name, data[field_name])
                    logger.debug(
                        f"[{log_prefix}] Set state attribute '{attr_name}' from field '{field_name}' to value '{data[field_name]}' for entity {entity}"
                    )
            else:
                default_value = attr_def.get("default")
                if default_value is not None:
                    entity.set_state(attr_name, default_value)
                    logger.debug(
                        f"[{log_prefix}] Set state attribute '{attr_name}' to default value '{default_value}' for entity {entity}"
                    )

    def _emit_event(self, event: Event):
        """Emit an event to all output handlers."""
        for handler in self.output_handlers:
            try:
                handler.emit_event(event)
            except Exception as e:
                logger.error(f"Error emitting event to handler: {e}")

    def _create_output_handler(self, output_config: Dict[str, Any]):
        """Create an output handler based on configuration."""
        output_type = output_config.get("type", "stdout")

        if output_type == "stdout":
            from resinker.outputs.stdout import StdoutOutputHandler

            return StdoutOutputHandler(output_config)
        elif output_type == "file":
            from resinker.outputs.file import FileOutputHandler

            return FileOutputHandler(output_config)
        elif output_type == "kafka":
            from resinker.outputs.kafka import KafkaOutputHandler

            return KafkaOutputHandler(output_config)
        else:
            logger.warning(f"Unknown output type: {output_type}")
            return None

    def _initialize_scenarios(self):
        """Initialize active scenarios based on configuration."""
        # Get all scenarios
        scenarios = self.config.scenarios
        if not scenarios:
            return

        # Calculate initiation weights
        scenario_names = list(scenarios.keys())
        weights = []

        for name in scenario_names:
            weight = scenarios[name].get("initiation_weight", 1.0)
            weights.append(weight)

        # Initialize some scenarios
        for _ in range(5):  # Start with 5 scenarios
            if not scenario_names:
                break

            # Choose a scenario based on weights
            scenario_name = random.choices(scenario_names, weights=weights, k=1)[0]
            scenario_def = scenarios[scenario_name]

            # Check if this scenario has entity requirements
            can_start = True
            entity_context = {}

            if "requires_initial_entities" in scenario_def:
                for requirement in scenario_def["requires_initial_entities"]:
                    entity_type = requirement["name"]
                    alias = requirement["alias"]
                    selection_filter = requirement.get("selection_filter", [])

                    # Convert selection_filter to the format expected by state_manager
                    filter_list = []
                    for filter_item in selection_filter:
                        filter_list.append(
                            {
                                "field": filter_item["field"],
                                "operator": filter_item["operator"],
                                "value": filter_item["value"],
                            }
                        )

                    # Find matching entities
                    entities = self.state_manager.find_entities(
                        entity_type, filter_list
                    )

                    if not entities:
                        can_start = False
                        break

                    # Store the entity for this requirement
                    entity_context[alias] = entities[0]

            if can_start:
                # Create the scenario instance
                scenario = ScenarioInstance(scenario_name, {"entities": entity_context})
                self.active_scenarios.append(scenario)

                # Schedule the first step
                self._schedule_scenario_step(scenario)

    def _process_scenarios(self):
        """Process active scenarios."""
        # Update scenarios based on completed events
        for scenario in self.active_scenarios[:]:
            if scenario.completed:
                self.active_scenarios.remove(scenario)

        # Add new scenarios if needed
        if len(self.active_scenarios) < 5:  # Maintain around 5 active scenarios
            self._initialize_scenarios()

    def _schedule_scenario_step(self, scenario: ScenarioInstance):
        """Schedule the next step in a scenario."""
        scenario_name = scenario.scenario_name
        scenario_def = self.config.scenarios.get(scenario_name)

        if not scenario_def or "steps" not in scenario_def:
            logger.warning(f"Scenario {scenario_name} not found or has no steps")
            scenario.completed = True
            return

        steps = scenario_def["steps"]
        current_step = scenario.current_step

        if current_step >= len(steps):
            logger.debug(f"Scenario {scenario_name} completed all steps")
            scenario.completed = True
            return

        step = steps[current_step]
        event_type = step["event_type"]

        # Create context for the event
        context = scenario.context.copy()
        context["scenario_instance"] = scenario

        if "payload_overrides" in step:
            context["payload_overrides"] = step["payload_overrides"]

        # Schedule the event
        delay = random.uniform(5, 30)  # 5 to 30 seconds
        scheduled_time = self.simulation_time + timedelta(seconds=delay)

        scheduled_event = ScheduledEvent(event_type, scheduled_time, context)
        heapq.heappush(self.event_queue, scheduled_event)

        # Advance the scenario step
        scenario.advance_step()
