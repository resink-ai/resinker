# Quick Start: Creating a Configuration YAML for Data Generation

This guide will help you quickly create a configuration YAML file for generating mock event data using Resinker.

---

## 1. Minimal Example

Below is a minimal configuration YAML. Save this as `my_events.yaml`:

```yaml
version: "1.0"
simulation_settings:
  duration: "10m"
  initial_entity_counts:
    User: 10
    Product: 5
  time_progression:
    start_time: "now"
    time_multiplier: 1.0
  random_seed: 42

schemas:
  UserID:
    type: string
    generator: uuid_v4
  Email:
    type: string
    generator: faker.email
  ProductName:
    type: string
    generator: faker.ecommerce.product_name
  UserRegistrationPayload:
    type: object
    properties:
      user_id: { $ref: "#/schemas/UserID" }
      email: { $ref: "#/schemas/Email" }
  ProductPayload:
    type: object
    properties:
      product_id:
        type: string
        generator: uuid_v4
      name: { $ref: "#/schemas/ProductName" }

entities:
  User:
    schema: "#/schemas/UserRegistrationPayload"
    primary_key: "user_id"
  Product:
    schema: "#/schemas/ProductPayload"
    primary_key: "product_id"

event_types:
  UserRegistered:
    payload_schema: "#/schemas/UserRegistrationPayload"
    produces_entity: "User"
    frequency_weight: 5
  ProductCreated:
    payload_schema: "#/schemas/ProductPayload"
    produces_entity: "Product"
    frequency_weight: 2

outputs:
  - type: "stdout"
    enabled: true
    format: "json_pretty"
```

---

## 2. Configuration Sections Explained

- **version**: Schema version for compatibility.
- **simulation_settings**: Controls the simulation duration, initial entities, time progression, and randomness.
- **schemas**: Defines reusable data types and payloads for events. Use `$ref` to reference other schemas.
- **entities**: Describes stateful objects (e.g., User, Product) and their primary keys.
- **event_types**: Defines the events to generate, their payloads, and how they affect entities.
- **outputs**: Specifies where generated data goes (e.g., stdout, file, Kafka).

---

## 3. Running the Generator

1. Install Resinker (if not already):
   ```bash
   pip install resinker
   # or
   uv pip install resinker
   ```
2. Run the generator:
   ```bash
   resinker run -c my_events.yaml
   ```

---

## 4. Next Steps & Advanced Features

- **Complex Schemas**: Add more fields, use generators like `faker.*`, `random_int`, `choice`, or `derived` for calculated fields.
- **Entity State**: Add `state_attributes` to entities to track things like login status or inventory.
- **Event Dependencies**: Use `consumes_entities` and `selection_filter` to model dependencies (e.g., only allow purchases by logged-in users).
- **Scenarios**: Define multi-step user journeys in the `scenarios` section.
- **Multiple Outputs**: Output to files, Kafka, or multiple destinations at once.

---

## 5. More Examples & Documentation

- See [`examples/sample_events.yaml`](examples/sample_events.yaml) and [`examples/ecommerce_events.yaml`](examples/ecommerce_events.yaml) for full-featured configs.
- For a detailed breakdown of all configuration options, see the [System Overview](System_Overview.md).

---

Happy data generating!
