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

## Key Design Principles and Components:

1.  **`version`**: For future compatibility as the configuration schema evolves.
2.  **`simulation_settings`**: Global parameters controlling the overall run, initial state, and time.
3.  **`schemas`**:
    - **Atomic Types**: Defines basic reusable types like `UserID`, `Email`, `Timestamp`. This promotes DRY (Don't Repeat Yourself).
    - **Payload Schemas**: Defines the structure of each event's payload (e.g., `UserRegistrationPayload`).
    - **`type`**: Standard JSON schema types (`string`, `number`, `integer`, `boolean`, `object`, `array`).
    - **`generator`**: Specifies how to generate the data for a field.
      - **Built-in**: `uuid_v4`, `random_int`, `random_float`, `choice`, `current_timestamp` (tied to simulation time), `static_hashed` (customizable), `random_alphanumeric`.
      - **Faker**: `faker.<provider>.<method>` (e.g., `faker.email`, `faker.name`). You'd integrate the `Faker` library.
      - **`$ref`**: Allows referencing other schemas, crucial for composition.
      - **`from_entity`**: Special directive to pull a value from an existing entity instance (e.g., `user_id` for login comes from an existing `User` entity).
      - **`derived`**: For fields whose values are calculated from other fields in the same payload.
      - **`conditional_choice`**: Allows choosing values based on other field values.
    - **`params`**: Parameters specific to each generator (e.g., `min`, `max` for `random_int`).
    - **`constraints`**: (Implicitly defined by generator params, but could be explicit e.g., `maxLength`, `pattern`). The `nullable_probability` is a form of constraint.
    - **`format`**: For types like `string` (e.g., `iso8601` for timestamps).
4.  **`entities`**:
    - Defines the stateful objects your system needs to track (e.g., `User`, `Product`).
    - `schema`: Links to a schema defining its data structure.
    - `primary_key`: The field that uniquely identifies an instance of this entity. Essential for the state manager.
    - `state_attributes`: Custom attributes managed by the simulation engine that are not part of the core schema but reflect the entity's state in the simulation (e.g., `is_logged_in`). Events can modify these.
5.  **`event_types`**:
    - `payload_schema`: Links to the schema for this event's data.
    - `produces_entity`: If this event creates a new instance of a defined `entity` (e.g., `UserRegistered` creates a `User`).
    - `produces_or_updates_entity`: If the event might create a new entity or modify an existing one.
    - `consumes_entities`: Critical for dependencies. Specifies which existing entities are required for this event to occur.
      - `name`: The entity type.
      - `alias`: A local name used in `updates_entity_state` or `selection_filter`.
      - `selection_filter`: Rules to pick specific instances of the consumed entity (e.g., a user who is not logged in, a product that is available). This is how you enforce constraints like "user must be registered" or "product must be listed."
    - `updates_entity_state`: Defines how this event changes the `state_attributes` of consumed or produced entities.
      - `from_payload_field`: Pulls value from the current event's payload.
    - `frequency_weight`: A simple way to control the relative likelihood of an event being chosen for generation if its preconditions are met. The actual generation rate also depends on how quickly dependencies can be satisfied.
6.  **`scenarios`** (Optional but Powerful):
    - Allows defining explicit multi-step sequences of events.
    - `initiation_weight`: How likely this scenario is to be picked.
    - `steps`: A list of events to be generated in order. The engine would manage the context (e.g., the user created in step 1 is the one logging in for step 2).
    - `requires_initial_entities`: A scenario might need certain entities to already exist to even begin.
    - This section adds a layer of behavioral modeling on top of the reactive event generation based on `frequency_weight` and `consumes_entities`.
7.  **`outputs`**: Defines where the generated event data should be sent.

**How Dependencies and Sequences are Handled:**

- **Entity Creation:** `produces_entity` in an event type tells the engine to create and store a new entity instance in its state manager.
- **Entity Consumption:** `consumes_entities` is the primary mechanism for dependencies. An event can only be generated if:
  1.  The required entity types exist.
  2.  Instances matching the `selection_filter` can be found in the state manager.
- **State Updates:** `updates_entity_state` allows events to change the state of entities, which in turn affects the `selection_filter` for future events (e.g., logging a user in changes `is_logged_in` to `true`, making them eligible for purchase events but not for another login event until logged out).
- **`from_entity` in Schemas**: When defining a payload field, `from_entity` ensures that the value is correctly sourced from an entity instance selected during the `consumes_entities` phase of event generation.
- **Scenarios:** Provide a more explicit way to define hard sequences for specific user journeys or operational flows. The engine would iterate through scenario steps, ensuring that the entity context is passed along (e.g., the `user_id` from a `UserRegistered` step is used for the subsequent `UserLoggedIn` step in the same scenario).

**Python Application Architecture Sketch:**

1.  **Config Loader:** Uses `PyYAML` to load and potentially Pydantic models for validation.
2.  **State Manager:** A class responsible for:
    - Storing instances of entities (e.g., a dictionary of `user_id -> UserObject`).
    - Allowing querying/filtering entities based on `selection_filter`.
    - Updating entity state.
3.  **Generator Engine:**
    - A collection of generator functions/classes for each `generator` type in the YAML.
    - Parses schema definitions to produce data.
    - Handles `faker`, `derived` fields, `conditional_choice` etc.
4.  **Event Scheduler/Orchestrator:**
    - The core logic.
    - Maintains the simulation clock.
    - Decides which event to generate next based on:
      - `frequency_weight` of `event_types`.
      - Active `scenarios` and their current step.
      - Checks `consumes_entities` and `selection_filter` against the `StateManager`.
    - Coordinates with the `Generator Engine` to create the event payload.
    - Instructs the `StateManager` to update/create entities.
    - Sends the event to the defined `outputs`.
5.  **Output Adapters:** Modules for sending data to Kafka, Kinesis, stdout, etc.

## Developer guide

1. Resinker is a python uv project, project details are defined in the pyproject.toml
2. Model name is `resinker`
3. Resinker uses python `faker` library for generating realistic data.
4. Resinker has expressive configuration parsing and validations, in case of mis-configuration, it can remind of where and what is wrong with the configuration file.
