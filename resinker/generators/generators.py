"""
Data generation module for creating values based on schemas.
"""

import logging
import uuid
import random
import string
from typing import Dict, Any, List
from datetime import datetime, date, time
from faker import Faker

from resinker.core.state_manager import StateManager

logger = logging.getLogger(__name__)


class Generator:
    """Base class for all generators."""

    def __init__(self, faker: Faker, state_manager: StateManager = None):
        self.faker = faker
        self.state_manager = state_manager

    def generate(self, schema: Dict[str, Any], context: Dict[str, Any] = None) -> Any:
        """Generate a value according to the schema."""
        raise NotImplementedError("Subclasses must implement generate()")


class UUIDGenerator(Generator):
    """Generate UUID values."""

    def generate(self, schema: Dict[str, Any], context: Dict[str, Any] = None) -> str:
        """Generate a UUID string."""
        return str(uuid.uuid4())


class RandomIntGenerator(Generator):
    """Generate random integer values."""

    def generate(self, schema: Dict[str, Any], context: Dict[str, Any] = None) -> int:
        """Generate a random integer within the specified range."""
        params = schema.get("params", {})
        min_val = params.get("min", 0)
        max_val = params.get("max", 100)
        return random.randint(min_val, max_val)


class RandomFloatGenerator(Generator):
    """Generate random float values."""

    def generate(self, schema: Dict[str, Any], context: Dict[str, Any] = None) -> float:
        """Generate a random float within the specified range."""
        params = schema.get("params", {})
        min_val = params.get("min", 0.0)
        max_val = params.get("max", 1.0)
        precision = params.get("precision", 2)
        value = random.uniform(min_val, max_val)
        return round(value, precision)


class RandomAlphanumericGenerator(Generator):
    """Generate random alphanumeric strings."""

    def generate(self, schema: Dict[str, Any], context: Dict[str, Any] = None) -> str:
        """Generate a random alphanumeric string."""
        params = schema.get("params", {})
        length = params.get("length", 10)
        chars = string.ascii_letters + string.digits
        return "".join(random.choice(chars) for _ in range(length))


class ChoiceGenerator(Generator):
    """Generate values from a predefined list of choices."""

    def generate(self, schema: Dict[str, Any], context: Dict[str, Any] = None) -> Any:
        """Choose a random value from the choices list."""
        params = schema.get("params", {})
        choices = params.get("choices", [])
        weights = params.get("weights", None)

        if not choices:
            raise ValueError("No choices provided for choice generator")

        if weights:
            if len(weights) != len(choices):
                raise ValueError("Number of weights must match number of choices")
            return random.choices(choices, weights=weights, k=1)[0]

        return random.choice(choices)


class ConditionalChoiceGenerator(Generator):
    """Generate values conditionally based on another field."""

    def generate(self, schema: Dict[str, Any], context: Dict[str, Any] = None) -> Any:
        """Choose a value based on a condition."""
        if context is None:
            context = {}

        params = schema.get("params", {})
        condition_field = params.get("condition_field", "")
        cases = params.get("cases", [])

        # Get the condition value from the context
        condition_value = context.get(condition_field)
        if condition_value is None:
            # Use the default case if available
            for case in cases:
                if "default" in case:
                    return self._choose_from_case(case)

            # If no default case, choose from the first case
            if cases:
                return self._choose_from_case(cases[0])

            raise ValueError(
                f"Condition field '{condition_field}' not found in context and no default case provided"
            )

        # Find the matching case
        for case in cases:
            # Check various condition types
            if "condition_value" in case and case["condition_value"] == condition_value:
                return self._choose_from_case(case)

            if (
                "condition_value_greater_than" in case
                and condition_value > case["condition_value_greater_than"]
            ):
                return self._choose_from_case(case)

            if (
                "condition_value_less_than" in case
                and condition_value < case["condition_value_less_than"]
            ):
                return self._choose_from_case(case)

            if (
                "condition_value_in" in case
                and condition_value in case["condition_value_in"]
            ):
                return self._choose_from_case(case)

        # Use the default case if available
        for case in cases:
            if "default" in case:
                return self._choose_from_case(case)

        # If no matching case and no default, choose from the first case
        if cases:
            return self._choose_from_case(cases[0])

        raise ValueError(
            f"No matching case found for condition '{condition_field}' with value '{condition_value}'"
        )

    def _choose_from_case(self, case: Dict[str, Any]) -> Any:
        """Choose a value from a case definition."""
        choices = case.get("choices", [])
        weights = case.get("weights", None)

        if not choices:
            raise ValueError("No choices provided in case definition")

        if weights:
            if len(weights) != len(choices):
                raise ValueError("Number of weights must match number of choices")
            return random.choices(choices, weights=weights, k=1)[0]

        return random.choice(choices)


class CurrentTimestampGenerator(Generator):
    """Generate timestamp values based on the simulation time."""

    def generate(self, schema: Dict[str, Any], context: Dict[str, Any] = None) -> str:
        """Generate a current timestamp in ISO 8601 format."""
        if context is None or "simulation_time" not in context:
            # Use real current time if simulation time not provided
            current_time = datetime.now()
        else:
            current_time = context["simulation_time"]

        # Format the timestamp according to the schema
        format_type = schema.get("format", "iso8601")
        if format_type == "iso8601":
            return current_time.isoformat()
        elif format_type == "unix":
            return int(current_time.timestamp())
        elif format_type == "unix_ms":
            return int(current_time.timestamp() * 1000)

        # Default to ISO 8601
        return current_time.isoformat()


class StaticHashedGenerator(Generator):
    """Generate statically hashed values (e.g., for passwords)."""

    def generate(self, schema: Dict[str, Any], context: Dict[str, Any] = None) -> str:
        """Generate a hashed value."""
        params = schema.get("params", {})
        algorithm = params.get("algorithm", "bcrypt")

        # Get the raw value to hash
        raw_value_source = params.get("raw_value_source", {})
        if raw_value_source:
            # Generate the raw value using another generator
            raw_value = self._generate_raw_value(raw_value_source)
        else:
            # Generate a random string as the raw value
            raw_value = "".join(
                random.choice(string.ascii_letters + string.digits) for _ in range(12)
            )

        # Hash the raw value
        if algorithm == "bcrypt":
            # Simple implementation for demo purposes
            # In a real system, you'd use a proper bcrypt library
            return f"$2a$10${self._simple_hash(raw_value)}"
        elif algorithm == "sha256":
            import hashlib

            return hashlib.sha256(raw_value.encode()).hexdigest()
        elif algorithm == "md5":
            import hashlib

            return hashlib.md5(raw_value.encode()).hexdigest()

        # Default to a simple hash
        return self._simple_hash(raw_value)

    def _generate_raw_value(self, source: Dict[str, Any]) -> str:
        """Generate a raw value using another generator."""
        generator_type = source.get("generator", "")
        if not generator_type:
            return "".join(
                random.choice(string.ascii_letters + string.digits) for _ in range(12)
            )

        # Find and use the appropriate generator
        generator = generator_factory(generator_type, self.faker, self.state_manager)
        return generator.generate(source)

    def _simple_hash(self, value: str) -> str:
        """Simple hash function for demo purposes."""
        import hashlib

        return hashlib.md5(value.encode()).hexdigest()[:22]


class FakerGenerator(Generator):
    """Generate values using the Faker library."""

    def generate(self, schema: Dict[str, Any], context: Dict[str, Any] = None) -> Any:
        """Generate a value using a Faker provider."""
        generator_type = schema.get("generator", "")

        # Extract the Faker provider and method
        if not generator_type.startswith("faker."):
            raise ValueError(f"Invalid Faker generator: {generator_type}")

        provider_method = generator_type[6:]  # Remove 'faker.' prefix

        # Split into provider and method if needed
        parts = provider_method.split(".")
        if len(parts) == 1:
            # Direct method on the faker instance
            method_name = parts[0]
            try:
                method = getattr(self.faker, method_name)
            except AttributeError:
                raise ValueError(f"Unknown Faker method: {method_name}")
        else:
            # Method on a provider
            method_name = parts[1]

            # For custom providers like 'ecommerce', call the method directly
            try:
                method = getattr(self.faker, method_name)
                # If this succeeds, it means the method is directly on faker object
                return method(**schema.get("params", {}))
            except AttributeError:
                # Try to get method from the provider
                try:
                    return self.faker.format(
                        provider_method, **schema.get("params", {})
                    )
                except (AttributeError, KeyError):
                    raise ValueError(
                        f"Unknown Faker provider or method: {provider_method}"
                    )

        # Call the method with parameters
        params = schema.get("params", {})
        try:
            return method(**params)
        except Exception as e:
            raise ValueError(f"Error calling Faker method {provider_method}: {e}")


class DerivedGenerator(Generator):
    """Generate values derived from other fields in the context."""

    def generate(self, schema: Dict[str, Any], context: Dict[str, Any] = None) -> Any:
        """Generate a value derived from other fields."""
        if context is None:
            context = {}

        params = schema.get("params", {})
        expression = params.get("expression", "")
        precision = params.get("precision", None)

        if not expression:
            raise ValueError("No expression provided for derived generator")

        # Simple expression evaluation for demo purposes
        # In a real system, you might use a safer evaluation method
        try:
            # Create a safe environment with context variables
            safe_env = {"__builtins__": {}}
            safe_env.update(context)

            # Define some helper functions
            def sum_values(values):
                return sum(values)

            safe_env["sum"] = sum_values

            # Evaluate the expression
            result = eval(expression, safe_env)

            # Apply precision if specified
            if precision is not None and isinstance(result, (int, float)):
                result = round(result, precision)

            return result
        except Exception as e:
            raise ValueError(f"Error evaluating expression '{expression}': {e}")


class FromEntityGenerator(Generator):
    """Generate values from existing entities."""

    def generate(self, schema: Dict[str, Any], context: Dict[str, Any] = None) -> Any:
        """Get a value from an entity in the state manager."""
        if self.state_manager is None:
            raise ValueError("FromEntityGenerator requires a state manager")

        if context is None:
            context = {}

        from_entity = schema.get("from_entity")
        field = schema.get("field")

        if not from_entity or not field:
            raise ValueError(
                "FromEntityGenerator requires from_entity and field parameters"
            )

        # Check if we have an entity alias in the context
        entity_key = f"entity_{from_entity}"
        entity = context.get(entity_key)

        if entity is None:
            # Try to find the entity in consumed entities
            consumed_entities = context.get("consumed_entities", {})
            for alias, entities in consumed_entities.items():
                if alias == from_entity or (
                    isinstance(entities, list)
                    and len(entities) > 0
                    and entities[0].entity_type == from_entity
                ):
                    if isinstance(entities, list):
                        entity = entities[0]  # Use the first entity
                    else:
                        entity = entities
                    break

        if entity is None:
            # If still None, try to get a random entity of this type
            entities = self.state_manager.get_all_entities(from_entity)
            if entities:
                entity = random.choice(entities)

        if entity is None:
            raise ValueError(f"No entity found for {from_entity}")

        # Get the field value
        # For nested fields, navigate through the object
        parts = field.split(".")
        value = entity.data
        for part in parts:
            if value is None:
                break
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                value = None
                break

        return value


class SchemaGenerator(Generator):
    """Generate objects or values based on a complete schema."""

    def __init__(
        self,
        faker: Faker,
        state_manager: StateManager = None,
        schema_registry: Dict[str, Any] = None,
    ):
        super().__init__(faker, state_manager)
        self.schema_registry = schema_registry or {}

    def generate(self, schema: Dict[str, Any], context: Dict[str, Any] = None) -> Any:
        """Generate a value according to the schema."""
        if context is None:
            context = {}

        # Handle references to other schemas
        if "$ref" in schema:
            ref = schema["$ref"]
            if ref.startswith("#/schemas/"):
                schema_name = ref[len("#/schemas/") :]
                if schema_name not in self.schema_registry:
                    raise ValueError(f"Schema not found: {schema_name}")

                # Combine the reference schema with any additional properties
                referenced_schema = self.schema_registry[schema_name].copy()
                for key, value in schema.items():
                    if key != "$ref":
                        referenced_schema[key] = value

                return self.generate(referenced_schema, context)

        # Check if a value should be null based on nullable_probability
        nullable_prob = schema.get("nullable_probability", 0.0)
        if nullable_prob > 0.0 and random.random() < nullable_prob:
            return None

        # Handle entity reference
        if "from_entity" in schema:
            generator = generator_factory("from_entity", self.faker, self.state_manager)
            return generator.generate(schema, context)

        # Process based on type
        schema_type = schema.get("type", "string")

        if schema_type == "object":
            return self._generate_object(schema, context)
        elif schema_type == "array":
            return self._generate_array(schema, context)
        elif schema_type == "string":
            return self._generate_string(schema, context)
        elif schema_type == "number":
            return self._generate_number(schema, context)
        elif schema_type == "integer":
            return self._generate_integer(schema, context)
        elif schema_type == "boolean":
            return self._generate_boolean(schema, context)
        else:
            raise ValueError(f"Unsupported schema type: {schema_type}")

    def _generate_object(
        self, schema: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate an object based on the schema."""
        properties = schema.get("properties", {})
        result = {}

        # Create a new context for the object's properties
        object_context = context.copy()

        # Generate each property
        for prop_name, prop_schema in properties.items():
            # Generate the property value
            prop_value = self.generate(prop_schema, object_context)
            result[prop_name] = prop_value

            # Add the property to the context
            object_context[prop_name] = prop_value

        return result

    def _generate_array(
        self, schema: Dict[str, Any], context: Dict[str, Any]
    ) -> List[Any]:
        """Generate an array based on the schema."""
        items_schema = schema.get("items", {})
        min_items = schema.get("min_items", 0)
        max_items = schema.get("max_items", min_items + 5)

        # Determine the number of items to generate
        num_items = random.randint(min_items, max_items)

        result = []
        for i in range(num_items):
            # Create a context for this array item
            item_context = context.copy()
            item_context["array_index"] = i

            # Generate the item
            item = self.generate(items_schema, item_context)
            result.append(item)

        return result

    def _generate_string(self, schema: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Generate a string based on the schema."""
        generator_type = schema.get("generator")

        if generator_type:
            # Use the specified generator
            generator = generator_factory(
                generator_type, self.faker, self.state_manager
            )
            value = generator.generate(schema, context)

            # Convert generated value to string based on type and format
            if isinstance(value, (datetime, date, time)):
                format_type = schema.get("format")
                if format_type == "iso8601" and isinstance(value, datetime):
                    return value.isoformat()
                elif format_type == "date" and isinstance(value, (datetime, date)):
                    return (
                        value.date().isoformat()
                        if isinstance(value, datetime)
                        else value.isoformat()
                    )
                elif format_type == "time" and isinstance(value, (datetime, time)):
                    return (
                        value.time().isoformat()
                        if isinstance(value, datetime)
                        else value.isoformat()
                    )
                else:
                    # Default date/time formatting if format not specified
                    return value.isoformat()

            # Return string representation for other types
            return str(value)

        # Default string generation
        format_type = schema.get("format")
        if format_type == "iso8601":
            return datetime.now().isoformat()
        elif format_type == "date":
            return datetime.now().date().isoformat()
        elif format_type == "time":
            return datetime.now().time().isoformat()

        # Default to a random string
        return self.faker.word()

    def _generate_number(
        self, schema: Dict[str, Any], context: Dict[str, Any]
    ) -> float:
        """Generate a number based on the schema."""
        generator_type = schema.get("generator")

        if generator_type:
            # Use the specified generator
            generator = generator_factory(
                generator_type, self.faker, self.state_manager
            )
            return generator.generate(schema, context)

        # Default to random float
        return random.uniform(0, 100)

    def _generate_integer(self, schema: Dict[str, Any], context: Dict[str, Any]) -> int:
        """Generate an integer based on the schema."""
        generator_type = schema.get("generator")

        if generator_type:
            # Use the specified generator
            generator = generator_factory(
                generator_type, self.faker, self.state_manager
            )
            return generator.generate(schema, context)

        # Default to random integer
        return random.randint(0, 100)

    def _generate_boolean(
        self, schema: Dict[str, Any], context: Dict[str, Any]
    ) -> bool:
        """Generate a boolean based on the schema."""
        generator_type = schema.get("generator")

        if generator_type:
            # Use the specified generator
            generator = generator_factory(
                generator_type, self.faker, self.state_manager
            )
            return generator.generate(schema, context)

        # Default to random boolean
        return random.choice([True, False])


def generator_factory(
    generator_type: str, faker: Faker, state_manager: StateManager = None
) -> Generator:
    """Create a generator instance based on the generator type."""
    if generator_type == "uuid_v4":
        return UUIDGenerator(faker, state_manager)
    elif generator_type == "random_int":
        return RandomIntGenerator(faker, state_manager)
    elif generator_type == "random_float":
        return RandomFloatGenerator(faker, state_manager)
    elif generator_type == "random_alphanumeric":
        return RandomAlphanumericGenerator(faker, state_manager)
    elif generator_type == "choice":
        return ChoiceGenerator(faker, state_manager)
    elif generator_type == "conditional_choice":
        return ConditionalChoiceGenerator(faker, state_manager)
    elif generator_type == "current_timestamp":
        return CurrentTimestampGenerator(faker, state_manager)
    elif generator_type == "static_hashed":
        return StaticHashedGenerator(faker, state_manager)
    elif generator_type == "derived":
        return DerivedGenerator(faker, state_manager)
    elif generator_type == "from_entity":
        return FromEntityGenerator(faker, state_manager)
    elif generator_type.startswith("faker."):
        return FakerGenerator(faker, state_manager)
    else:
        raise ValueError(f"Unknown generator type: {generator_type}")
