# Resinker: A YAML-based configuration system for mocking event streams

## Example YAML configuration

```yaml
version: "1.0" # Configuration schema version

#-------------------------------------------------------------------------------
# Global Simulation Settings
#-------------------------------------------------------------------------------
simulation_settings:
  # Total duration to run the simulation (e.g., "30m", "1h", "10s")
  # Mutually exclusive with total_events. If both, duration takes precedence.
  duration: "10m"
  # Total number of events to generate before stopping.
  # total_events: 10000

  # Initial number of entities to create at startup for specific types.
  # Useful for ensuring there's data to interact with from the beginning.
  initial_entity_counts:
    Product: 50 # Create 50 products at the start
    User: 10 # Create 10 users at the start

  # Time progression settings
  time_progression:
    # Start date/time for the simulation. Events will have timestamps from this point.
    # If "now", uses the current system time at startup.
    start_time: "2025-05-06T10:00:00Z"
    # How fast simulation time passes relative to real time.
    # 1.0 = real-time, 60.0 = 1 simulation second is 1 real minute.
    # For very fast generation, this might be less relevant than event rate.
    time_multiplier: 1.0

  # Seed for random number generators for reproducible runs
  random_seed: 42

#-------------------------------------------------------------------------------
# Schema Definitions (The structure of your data objects/events)
#-------------------------------------------------------------------------------
schemas:
  UserID:
    type: string
    generator: uuid_v4
    description: "Unique identifier for a user."

  Email:
    type: string
    generator: faker.email # Using a faker provider
    description: "User's email address."

  Password: # Example of a more complex static but sensitive field
    type: string
    generator: static_hashed # A custom generator you'd implement
    params:
      algorithm: "bcrypt"
      raw_value_source: # Could be a faker password then hashed
        generator: faker.password
        params:
          length: 12
          special_chars: true
          digits: true
          upper_case: true
          lower_case: true

  Timestamp:
    type: string
    format: "iso8601" # Enforces ISO 8601, generator should respect this
    generator: current_timestamp # Special generator tied to simulation time

  ProductName:
    type: string
    generator: faker.ecommerce.product_name

  ProductPrice:
    type: number
    generator: random_float
    params:
      min: 0.99
      max: 999.99
      precision: 2

  # ---- Complex Schemas / Payloads ----
  UserRegistrationPayload:
    type: object
    properties:
      user_id: { $ref: "#/schemas/UserID" }
      full_name:
        type: string
        generator: faker.name
      email: { $ref: "#/schemas/Email" }
      password_hash: { $ref: "#/schemas/Password" } # The hashed one
      registration_timestamp: { $ref: "#/schemas/Timestamp" }
      # Example of a field that's sometimes null
      referral_code:
        type: string
        generator: random_alphanumeric
        params:
          length: 8
        nullable_probability: 0.7 # 70% chance this field will be null

  UserLoginPayload:
    type: object
    properties:
      # This user_id will be populated by an existing, registered user
      user_id:
        { $ref: "#/schemas/UserID", from_entity: "User", field: "user_id" }
      login_timestamp: { $ref: "#/schemas/Timestamp" }
      ip_address:
        type: string
        generator: faker.ipv4
      user_agent:
        type: string
        generator: faker.user_agent

  ProductUpdatePayload:
    type: object
    properties:
      product_id:
        type: string
        generator: uuid_v4 # Assuming product IDs are also UUIDs
        # If using sequential, define a sequence elsewhere and reference it
      name: { $ref: "#/schemas/ProductName" }
      description:
        type: string
        generator: faker.lorem.sentence
        params:
          nb_words: 10
      price: { $ref: "#/schemas/ProductPrice" }
      # Example of an array of simple strings
      tags:
        type: array
        items:
          type: string
          generator: choice
          params:
            choices: ["new", "featured", "sale", "eco-friendly", "premium"]
        min_items: 0
        max_items: 3
      # Example of an enum
      status:
        type: string
        generator: choice
        params:
          choices: ["available", "discontinued", "coming_soon"]
      updated_at: { $ref: "#/schemas/Timestamp" }

  PurchasePayload:
    type: object
    properties:
      purchase_id:
        type: string
        generator: uuid_v4
      # user_id will be populated by an existing, logged-in user
      user_id:
        { $ref: "#/schemas/UserID", from_entity: "User", field: "user_id" }
      # items will be an array of purchased products
      items:
        type: array
        min_items: 1
        max_items: 5
        items: # Schema for each item in the purchase
          type: object
          properties:
            # product_id will be populated from an existing, available product
            product_id:
              { type: string, from_entity: "Product", field: "product_id" }
            quantity:
              type: integer
              generator: random_int
              params:
                min: 1
                max: 3
            # Price at the time of purchase, could be copied from product or a snapshot
            unit_price:
              {
                $ref: "#/schemas/ProductPrice",
                from_entity: "Product",
                field: "price",
              }
      total_amount: # This could be a calculated field
        type: number
        generator: derived # Special generator indicating calculation
        params:
          expression: "sum(item.quantity * item.unit_price for item in items)"
          precision: 2
      purchase_timestamp: { $ref: "#/schemas/Timestamp" }
      # Example: conditional field based on total_amount
      shipping_method:
        type: string
        generator: conditional_choice
        params:
          condition_field: "total_amount"
          cases:
            - condition_value_greater_than: 50.00
              choices: ["Free Standard Shipping", "Express Shipping"]
              weights: [0.8, 0.2] # 80% free, 20% express if > 50
            - default: # else
              choices: ["Standard Shipping", "Express Shipping"]
              weights: [0.7, 0.3]

#-------------------------------------------------------------------------------
# Entity Definitions (Stateful objects that events operate on)
#-------------------------------------------------------------------------------
entities:
  User:
    schema: "#/schemas/UserRegistrationPayload" # Defines the core data structure
    primary_key: "user_id" # Field used to uniquely identify a User instance
    # State attributes are managed by the simulation engine based on events
    state_attributes:
      is_logged_in: { type: boolean, default: false }
      last_login_timestamp: { $ref: "#/schemas/Timestamp", nullable: true }
      total_purchase_value: { type: number, default: 0.0, precision: 2 }
      # We can add more complex state like session_id if needed

  Product:
    schema: "#/schemas/ProductUpdatePayload"
    primary_key: "product_id"
    state_attributes:
      # Example: if a product is "available"
      current_status: { type: string, from_field: "status" } # Mirrors the 'status' field from its schema
      # inventory_count: { type: integer, default: 100 } # If simulating inventory

#-------------------------------------------------------------------------------
# Event Type Definitions
# (Link payloads to entity lifecycle and define constraints/dependencies)
#-------------------------------------------------------------------------------
event_types:
  UserRegistered:
    payload_schema: "#/schemas/UserRegistrationPayload"
    produces_entity: "User" # This event creates a new User instance
    # No dependencies for registration
    frequency_weight: 10 # Relative weight for how often this event should be triggered

  UserLoggedIn:
    payload_schema: "#/schemas/UserLoginPayload"
    # This event operates on an existing User entity
    consumes_entities:
      - name: "User"
        alias: "logging_in_user" # Alias for referencing this specific user in actions
        # Conditions for selecting the User entity instance:
        # System will try to find a User where is_logged_in is false.
        selection_filter:
          - field: "state.is_logged_in" # 'state.' prefix refers to managed state attributes
            operator: "equals"
            value: false
    # Actions to perform on entities after event generation
    # (e.g., update state of the consumed 'logging_in_user')
    updates_entity_state:
      - entity_alias: "logging_in_user"
        set_attributes:
          is_logged_in: true
          last_login_timestamp: { from_payload_field: "login_timestamp" }
    frequency_weight: 30
    # Optional: Max outstanding logged-in users (e.g. if you want to simulate sessions ending)
    # max_active_instances_of_state:
    #   entity: "User"
    #   attribute: "is_logged_in"
    #   value: true
    #   max_count: 100 # e.g., only 100 users can be logged in concurrently

  ProductCreatedOrUpdated: # Combines creation and updates for simplicity here
    payload_schema: "#/schemas/ProductUpdatePayload"
    # This can either create a new Product or update an existing one.
    # The engine can decide based on probability or if a product_id is referenced.
    produces_or_updates_entity: "Product"
    # If updating, needs an existing Product. If creating, it doesn't.
    # This logic would be in the generator: 10% chance to pick existing, 90% create new.
    update_existing_probability: 0.1
    frequency_weight: 5

  UserPurchasedProducts:
    payload_schema: "#/schemas/PurchasePayload"
    consumes_entities:
      - name: "User"
        alias: "buyer"
        selection_filter:
          - field: "state.is_logged_in"
            operator: "equals"
            value: true # User must be logged in
      - name: "Product"
        alias: "purchased_item" # This alias applies to each item in the payload's 'items' array
        # For each item in the purchase, a product must be available
        selection_filter:
          - field: "state.current_status"
            operator: "equals"
            value: "available"
        min_required: 1 # At least one product must be available to attempt a purchase event
    updates_entity_state:
      - entity_alias: "buyer"
        # Example: Increment total purchase value. 'payload.total_amount' refers to the generated event.
        increment_attributes:
          total_purchase_value: { from_payload_field: "total_amount" }
    # Dependency: This event can only occur *after* a UserRegistered event and
    # a UserLoggedIn event for that specific user, AND after a ProductCreatedOrUpdated
    # event for the specific product(s). This is largely handled by `consumes_entities`
    # and their `selection_filter`.
    # Explicit sequence can be defined in `scenarios` if needed for stricter ordering.
    frequency_weight: 15

#-------------------------------------------------------------------------------
# Scenarios (Optional: For defining more complex, multi-step user journeys or sequences)
# More explicit control over event order beyond simple frequency and prerequisites.
#-------------------------------------------------------------------------------
scenarios:
  NewUserOnboardingAndFirstPurchase:
    description: "A new user registers, logs in, and makes a purchase."
    # Probability or weight of this scenario being chosen to start
    # (if multiple scenarios can be initiated independently)
    initiation_weight: 70
    # Sequence of events. The system will try to generate these in order,
    # satisfying dependencies.
    steps:
      - event_type: "UserRegistered"
        # Parameters specific to this step, e.g., override default values
        # for some payload fields for users in this scenario.
        # payload_overrides:
        #   referral_code: "SCENARIO_NEW"

      - event_type: "UserLoggedIn"
        # This step implicitly depends on the user created in the previous step.
        # The engine should track context within a scenario run.
        # delay_after_previous_step: # Simulate time passing
        #   min_seconds: 5
        #   max_seconds: 120

      - event_type: "UserPurchasedProducts"
        # delay_after_previous_step:
        #   min_seconds: 60
        #   max_seconds: 600
        # This purchase is by the user from step 1 & 2.
        # The engine needs to ensure products are available.
        # If not, this step might be skipped or the scenario might pause/retry.

  Product BrowseSpree: # A scenario that doesn't necessarily create a new user
    description: "An existing logged-in user makes multiple purchases over time."
    initiation_weight: 30
    # This scenario requires an existing, logged-in user to start.
    requires_initial_entities:
      - name: "User"
        alias: "active_user"
        selection_filter:
          - field: "state.is_logged_in"
            operator: "equals"
            value: true
    steps:
      - event_type: "UserPurchasedProducts" # First purchase for this user in this scenario
        # loop: # Generate this event multiple times for the same user
        #  min_count: 1
        #  max_count: 3
        #  delay_between_loops:
        #    min_seconds: 300 # 5 mins
        #    max_seconds: 3600 # 1 hour

#-------------------------------------------------------------------------------
# Output Configuration (Where the generated data goes)
#-------------------------------------------------------------------------------
outputs:
  - type: "kafka" # Or "kinesis", "stdout", "file"
    enabled: true
    topic_mapping: # Which events go to which Kafka topics
      UserRegistered: "user_lifecycle_events"
      UserLoggedIn: "user_lifecycle_events"
      ProductCreatedOrUpdated: "product_catalog_events"
      UserPurchasedProducts: "order_events"
    # Common Kafka settings
    kafka_brokers: "localhost:9092"
    # security_protocol: "SASL_SSL"
    # sasl_mechanism: "PLAIN"
    # sasl_plain_username: "user"
    # sasl_plain_password: "password"
  - type: "stdout"
    enabled: false # Can be enabled for debugging
    format: "json_pretty" # "json" or "json_pretty"
```

# Resinker Data Generation Schema: Full Breakdown

## 1. `version`

**Purpose:**  
Specifies the configuration schema version.  
**Impact:**  
Ensures compatibility as the configuration format evolves. Always set this to the latest supported version (e.g., `"1.0"`).

---

## 2. `simulation_settings`

**Purpose:**  
Controls the overall simulation run, including how long it runs, how many events are generated, the initial state, and time progression.

**Options:**

| Option                  | Type    | Description                                                                                                                                                                                             | Example     | Impact                                                                            |
| ----------------------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------- | --------------------------------------------------------------------------------- |
| `duration`              | string  | How long the simulation should run. Format: `<number><unit>` where unit is `s` (seconds), `m` (minutes), or `h` (hours). Mutually exclusive with `total_events` (if both, `duration` takes precedence). | `"10m"`     | Limits the simulation to a set time window.                                       |
| `total_events`          | integer | Total number of events to generate before stopping.                                                                                                                                                     | `10000`     | Limits the simulation by event count instead of time.                             |
| `initial_entity_counts` | object  | Specifies how many of each entity type to create at startup. Keys are entity names, values are counts.                                                                                                  | `User: 10`  | Ensures there are entities available for events to operate on from the beginning. |
| `time_progression`      | object  | Controls simulation time. See below for sub-options.                                                                                                                                                    | (see below) | Affects event timestamps and the pace of simulated time.                          |
| `random_seed`           | integer | Seed for random number generators.                                                                                                                                                                      | `42`        | Makes runs reproducible (same config and seed = same data).                       |

**`time_progression` sub-options:**

| Option            | Type   | Description                                                                                                      | Example                        | Impact                                                                                 |
| ----------------- | ------ | ---------------------------------------------------------------------------------------------------------------- | ------------------------------ | -------------------------------------------------------------------------------------- |
| `start_time`      | string | When the simulation starts. `"now"` or ISO 8601 datetime.                                                        | `"now"`, `"2025-01-01T00:00Z"` | Sets the base timestamp for all generated events.                                      |
| `time_multiplier` | float  | How fast simulation time passes relative to real time. `1.0` = real time, `60.0` = 1 sim second = 1 real minute. | `1.0`, `10.0`                  | Controls the speed of simulated time, affecting event timestamps and time-based logic. |

**How these options impact data:**

- `duration`/`total_events` determine when the simulation stops.
- `initial_entity_counts` ensures there are enough entities for events (e.g., users to log in, products to purchase).
- `time_progression` affects event timestamps and can simulate rapid or slow time passage.
- `random_seed` ensures repeatability for testing or debugging.

---

## 3. `schemas`

**Purpose:**  
Defines the structure and generation logic for all data objects and event payloads.

**Types of schemas:**

- **Atomic Types:** Reusable primitives (e.g., `UserID`, `Email`, `Timestamp`).
- **Payload Schemas:** Complex objects for event payloads (e.g., `UserRegistrationPayload`).

**Schema fields:**

| Field                   | Type   | Description                                                                   | Example                          |
| ----------------------- | ------ | ----------------------------------------------------------------------------- | -------------------------------- |
| `type`                  | string | JSON schema type: `string`, `number`, `integer`, `boolean`, `object`, `array` | `"string"`, `"object"`           |
| `generator`             | string | How to generate the value. See below for options.                             | `"uuid_v4"`, `"faker.email"`     |
| `params`                | object | Parameters for the generator (e.g., min/max for numbers, choices for enums).  | `{min: 1, max: 10}`              |
| `description`           | string | Human-readable description.                                                   | `"Unique identifier for a user"` |
| `format`                | string | For strings: `"iso8601"`, `"date"`, `"time"`, `"unix"`, etc.                  | `"iso8601"`                      |
| `properties`            | object | For objects: field definitions.                                               | `{user_id: {...}, ...}`          |
| `items`                 | object | For arrays: schema for array items.                                           | `{type: "string"}`               |
| `min_items`/`max_items` | int    | For arrays: min/max number of items.                                          | `1`, `5`                         |
| `nullable_probability`  | float  | Probability this field is null (0.0 to 1.0).                                  | `0.7`                            |
| `$ref`                  | string | Reference to another schema.                                                  | `"#/schemas/UserID"`             |
| `from_entity`           | string | Pull value from an existing entity instance.                                  | `"User"`                         |
| `field`                 | string | Field name in the referenced entity.                                          | `"user_id"`                      |

**Generator options:**

- **Built-in:** `uuid_v4`, `random_int`, `random_float`, `choice`, `current_timestamp`, `static_hashed`, `random_alphanumeric`, `derived`, `conditional_choice`
- **Faker:** `faker.<provider>.<method>` (e.g., `faker.email`, `faker.name`)
- **References:** Use `$ref` to reuse schema definitions.
- **Entity references:** Use `from_entity` and `field` to pull values from existing entities.

**Impact:**  
Schemas define the shape and content of all generated data, including how realistic, varied, or constrained the data is.

---

## 4. `entities`

**Purpose:**  
Defines the stateful objects in your simulation (e.g., users, products).

| Field              | Type   | Description                                                                       | Example                                           |
| ------------------ | ------ | --------------------------------------------------------------------------------- | ------------------------------------------------- |
| `schema`           | string | Reference to the schema defining the entity's data structure.                     | `"#/schemas/UserRegistrationPayload"`             |
| `primary_key`      | string | Field that uniquely identifies an instance of this entity.                        | `"user_id"`                                       |
| `state_attributes` | object | Custom attributes managed by the simulation engine (not part of the core schema). | `{is_logged_in: {type: boolean, default: false}}` |

**Impact:**  
Entities are tracked throughout the simulation. Their state can be updated by events, and they can be referenced in event payloads and dependencies.

---

## 5. `event_types`

**Purpose:**  
Defines the types of events to generate, their payloads, and how they interact with entities.

| Field                        | Type   | Description                                                    | Example                               |
| ---------------------------- | ------ | -------------------------------------------------------------- | ------------------------------------- |
| `payload_schema`             | string | Reference to the schema for this event's data.                 | `"#/schemas/UserRegistrationPayload"` |
| `produces_entity`            | string | If this event creates a new entity instance.                   | `"User"`                              |
| `produces_or_updates_entity` | string | If this event may create or update an entity.                  | `"Product"`                           |
| `consumes_entities`          | list   | Which existing entities are required for this event.           | See below                             |
| `updates_entity_state`       | list   | How this event changes the state of entities.                  | See below                             |
| `frequency_weight`           | number | Relative likelihood of this event being chosen for generation. | `10`                                  |

**`consumes_entities` subfields:**

- `name`: Entity type.
- `alias`: Local name for referencing in updates or filters.
- `selection_filter`: Rules for picking specific instances (e.g., only users not logged in).

**`updates_entity_state` subfields:**

- `entity_alias`: Which entity to update.
- `set_attributes`: Set state attributes to specific values.
- `increment_attributes`: Increment state attributes by a value.
- `from_payload_field`: Use a value from the event payload.

**Impact:**  
Event types control what happens in the simulation, how entities are created/updated, and how event dependencies are enforced.

---

## 6. `scenarios` (Optional)

**Purpose:**  
Defines multi-step, stateful user journeys or operational flows.

| Field                       | Type   | Description                                                                 | Example                                                  |
| --------------------------- | ------ | --------------------------------------------------------------------------- | -------------------------------------------------------- |
| `description`               | string | Human-readable description.                                                 | `"A new user registers, logs in, and makes a purchase."` |
| `initiation_weight`         | number | Likelihood of this scenario being picked.                                   | `70`                                                     |
| `steps`                     | list   | Sequence of events to generate, with optional payload overrides and delays. | See below                                                |
| `requires_initial_entities` | list   | Entities that must exist for the scenario to start.                         | See below                                                |

**`steps` subfields:**

- `event_type`: Event to generate.
- `payload_overrides`: Override default payload values for this step.
- `delay_after_previous_step`: Simulate time passing between steps.

**Impact:**  
Scenarios allow you to model realistic, multi-step behaviors and enforce strict event orderings.

---

## 7. `outputs`

**Purpose:**  
Specifies where the generated data should be sent.

| Field           | Type    | Description                                                     | Example                           |
| --------------- | ------- | --------------------------------------------------------------- | --------------------------------- |
| `type`          | string  | Output type: `"file"`, `"stdout"`, `"kafka"`, `"kinesis"`, etc. | `"file"`                          |
| `enabled`       | boolean | Whether this output is active.                                  | `true`                            |
| `file_path`     | string  | For file outputs: where to write the data.                      | `"output/events.json"`            |
| `format`        | string  | Output format: `"json"`, `"json_pretty"`, etc.                  | `"json_pretty"`                   |
| `topic_mapping` | object  | For Kafka: map event types to topics.                           | `{UserRegistered: "user_events"}` |
| `kafka_brokers` | string  | For Kafka: broker addresses.                                    | `"localhost:9092"`                |
| ...             | ...     | Other output-specific options (see examples).                   |                                   |

**Impact:**  
Controls where and how your generated data is delivered.

---

## How Dependencies and Sequences are Handled

- **Entity Creation:** `produces_entity` in an event type creates and stores a new entity instance.
- **Entity Consumption:** `consumes_entities` enforces dependencies—an event can only be generated if the required entities exist and match the `selection_filter`.
- **State Updates:** `updates_entity_state` allows events to change entity state, affecting future event eligibility.
- **Scenarios:** Provide explicit, multi-step flows, passing context (e.g., a user created in step 1 is used in step 2).

---

## Example

See [`examples/sample_events.yaml`](examples/sample_events.yaml) and [`examples/ecommerce_events.yaml`](examples/ecommerce_events.yaml) for full configurations.
