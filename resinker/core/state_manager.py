"""
State manager module for handling entities and their states.
"""

import logging
from typing import Dict, Any, List, Optional, Set
import operator
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

# Define operators for selection filters
OPERATORS = {
    "equals": operator.eq,
    "not_equals": operator.ne,
    "greater_than": operator.gt,
    "less_than": operator.lt,
    "greater_equals": operator.ge,
    "less_equals": operator.le,
    "contains": lambda a, b: b in a if hasattr(a, "__contains__") else False,
    "not_contains": lambda a, b: b not in a if hasattr(a, "__contains__") else True,
    "in": lambda a, b: a in b if hasattr(b, "__contains__") else False,
    "not_in": lambda a, b: a not in b if hasattr(b, "__contains__") else True,
}


class Entity:
    """Represents an entity instance in the system."""

    def __init__(self, entity_type: str, data: Dict[str, Any], primary_key: str):
        self.entity_type = entity_type
        self.data = data  # Core data from the payload
        self.state = {}  # Mutable state attributes
        self.primary_key = primary_key
        self.id = data.get(primary_key, str(uuid.uuid4()))
        self.created_at = datetime.now()

    def update_data(self, data: Dict[str, Any]):
        """Update the entity data."""
        self.data.update(data)

    def set_state(self, key: str, value: Any):
        """Set a state attribute."""
        self.state[key] = value

    def get_state(self, key: str, default=None) -> Any:
        """Get a state attribute value."""
        return self.state.get(key, default)

    def increment_state(self, key: str, value: Any):
        """Increment a numeric state attribute."""
        current = self.state.get(key, 0)
        if isinstance(current, (int, float)) and isinstance(value, (int, float)):
            self.state[key] = current + value
        else:
            raise ValueError(
                f"Cannot increment non-numeric state {key} with value {value}"
            )

    def matches_filter(self, filters: List[Dict[str, Any]]) -> bool:
        """Check if this entity matches all the given filters."""
        for filter_item in filters:
            field = filter_item["field"]
            op = filter_item["operator"]
            value = filter_item["value"]

            # Get the actual value from the entity
            if field.startswith("state."):
                state_key = field[6:]  # Remove "state." prefix
                actual_value = self.get_state(state_key)
            else:
                # Navigate through nested fields if needed
                parts = field.split(".")
                obj = self.data
                for part in parts:
                    if obj is None:
                        break
                    if isinstance(obj, dict) and part in obj:
                        obj = obj[part]
                    else:
                        obj = None
                        break
                actual_value = obj

            # Apply the operator
            if op not in OPERATORS:
                raise ValueError(f"Unsupported operator: {op}")

            op_func = OPERATORS[op]
            if not op_func(actual_value, value):
                return False

        return True


class StateManager:
    """Manages the state of all entities in the system."""

    def __init__(self):
        # Dictionary mapping entity type -> ID -> Entity instance
        self.entities: Dict[str, Dict[str, Entity]] = {}
        # Track entity ID sequences
        self.entity_id_sequences: Dict[str, int] = {}

    def register_entity_type(self, entity_type: str, primary_key: str):
        """Register a new entity type if not already registered."""
        if entity_type not in self.entities:
            self.entities[entity_type] = {}
            self.entity_id_sequences[entity_type] = 0
            logger.info(
                f"Registered entity type: {entity_type} with primary key: {primary_key}"
            )

    def create_entity(
        self, entity_type: str, data: Dict[str, Any], primary_key: str
    ) -> Entity:
        """Create a new entity instance."""
        # Ensure entity type is registered
        self.register_entity_type(entity_type, primary_key)

        # Create the entity
        entity = Entity(entity_type, data, primary_key)

        # Store it in our registry
        self.entities[entity_type][entity.id] = entity
        logger.debug(f"Created entity {entity_type} with ID {entity.id}")

        return entity

    def update_entity(
        self, entity_type: str, entity_id: str, data: Dict[str, Any]
    ) -> Optional[Entity]:
        """Update an existing entity's data."""
        if entity_type in self.entities and entity_id in self.entities[entity_type]:
            entity = self.entities[entity_type][entity_id]
            entity.update_data(data)
            logger.debug(f"Updated entity {entity_type} with ID {entity_id}")
            return entity
        else:
            logger.warning(
                f"Entity {entity_type} with ID {entity_id} not found for update"
            )
            return None

    def update_entity_state(
        self,
        entity_type: str,
        entity_id: str,
        set_attributes: Dict[str, Any],
        increment_attributes: Dict[str, Any],
    ) -> Optional[Entity]:
        """Update an entity's state attributes."""
        if entity_type in self.entities and entity_id in self.entities[entity_type]:
            entity = self.entities[entity_type][entity_id]

            # Set attributes
            for key, value in set_attributes.items():
                entity.set_state(key, value)

            # Increment attributes
            for key, value in increment_attributes.items():
                entity.increment_state(key, value)

            # Get the union of set and increment attributes
            changed_attributes = set_attributes.keys() | increment_attributes.keys()
            logger.debug(
                f"Updated state for entity {entity_type} with ID {entity_id}, changed: {', '.join(changed_attributes)}"
            )
            return entity
        else:
            logger.warning(
                f"Entity {entity_type} with ID {entity_id} not found for state update"
            )
            return None

    def get_entity(self, entity_type: str, entity_id: str) -> Optional[Entity]:
        """Get a specific entity by type and ID."""
        if entity_type in self.entities and entity_id in self.entities[entity_type]:
            return self.entities[entity_type][entity_id]
        return None

    def find_entities(
        self,
        entity_type: str,
        filters: List[Dict[str, Any]],
        limit: Optional[int] = None,
    ) -> List[Entity]:
        """Find entities matching the given filters."""
        if entity_type not in self.entities:
            return []

        result = []
        for entity in self.entities[entity_type].values():
            if entity.matches_filter(filters):
                result.append(entity)
                if limit is not None and len(result) >= limit:
                    break

        return result

    def count_entities(
        self, entity_type: str, filters: Optional[List[Dict[str, Any]]] = None
    ) -> int:
        """Count entities of a given type, optionally filtered."""
        if entity_type not in self.entities:
            return 0

        if filters is None:
            return len(self.entities[entity_type])

        return len(self.find_entities(entity_type, filters))

    def get_all_entity_types(self) -> Set[str]:
        """Get all registered entity types."""
        return set(self.entities.keys())

    def get_all_entities(self, entity_type: str) -> List[Entity]:
        """Get all entities of a given type."""
        if entity_type not in self.entities:
            return []
        return list(self.entities[entity_type].values())

    def delete_entity(self, entity_type: str, entity_id: str) -> bool:
        """Delete an entity by ID."""
        if entity_type in self.entities and entity_id in self.entities[entity_type]:
            del self.entities[entity_type][entity_id]
            logger.debug(f"Deleted entity {entity_type} with ID {entity_id}")
            return True
        logger.warning(
            f"Entity {entity_type} with ID {entity_id} not found for deletion"
        )
        return False
