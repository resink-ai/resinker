# Resinker

A YAML-based configuration system for mocking event streams. Resinker allows you to generate realistic event data based on entity relationships, dependencies, and scenarios.

## Features

- Define your event schemas in YAML
- **Import/include other YAML files for modular configurations**
- Model complex entity relationships and state changes
- Generate realistic event data using the Faker library
- Define complex scenarios and event sequences
- Output to various destinations: Kafka, files, stdout

## Installation

```bash
pip install resinker
```

Or if you're using uv:

```bash
uv pip install resinker
```

## Quick Start

1. Create a YAML configuration file:

```yaml
version: "1.0"

# Optional: Import other configuration files
imports:
  - "schemas.yaml"
  - "events.yaml"

simulation_settings:
  duration: "10m"
  initial_entity_counts:
    User: 10
  time_progression:
    start_time: "now"
    time_multiplier: 1.0
  random_seed: 42
# Define your schemas, entities, and events here
# ...
outputs:
  - type: "stdout"
    enabled: true
    format: "json_pretty"
```

2. Run Resinker:

```bash
python -m resinker run -c examples/mysas/events_main.yaml --verbose
python -m resinker validate -c examples/mysas/events_main.yaml
python -m resinker info -c examples/mysas/events_main.yaml
```

## Modular Configuration

Resinker supports importing other YAML files to create modular, reusable configurations:

```yaml
# main.yaml
version: "1.0"
imports:
  - "schemas.yaml"
  - "user_events.yaml"
  - "product_events.yaml"

simulation_settings:
  duration: "5m"
  # ... rest of configuration
```

This allows you to:

- Share common schemas across multiple configurations
- Organize events by domain or feature
- Enable team collaboration on different modules
- Maintain cleaner, more focused configuration files

## Documentation

For detailed documentation and examples, see the [System Overview](System_Overview.md).

## Community

[![Discord](https://img.shields.io/discord/1375892790713647254?label=Discord&logo=discord&logoColor=green&color=7289DA)](https://discord.gg/Sys6MWaX)
