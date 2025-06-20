# Resinker Examples

This directory contains example configurations demonstrating different features of Resinker.

## Files Overview

### Basic Examples

- `sample_events.yaml` - A comprehensive single-file configuration example
- `ecommerce_events.yaml` - E-commerce focused event simulation
- `trading_platform.yaml` - Trading platform event simulation

### Modular Configuration Examples

- `events_main.yaml` - **Main configuration demonstrating import functionality**
- `schemas.yaml` - Common schemas and entities that can be imported
- `onboarding_events.yaml` - User onboarding event types
- `trading_events.yaml` - Trading and purchase event types

## Import/Include Functionality

The modular configuration examples demonstrate Resinker's ability to import and merge multiple YAML files:

### Running the Modular Example

```bash
# Run the main configuration that imports other files
resinker run -c examples/events_main.yaml

# Validate the configuration
resinker validate -c examples/events_main.yaml

# View configuration info (shows merged result)
resinker info -c examples/events_main.yaml
```

### File Structure

```
examples/
├── events_main.yaml      # Main config with imports
├── schemas.yaml          # Common schemas and entities
├── onboarding_events.yaml # User registration/login events
└── trading_events.yaml   # Product and purchase events
```

### Benefits of Modular Configuration

1. **Reusability**: Common schemas can be shared across multiple configurations
2. **Organization**: Logical separation of different event types
3. **Maintainability**: Easier to manage and update specific parts
4. **Collaboration**: Different team members can work on different modules

### Import Rules

- Import paths are relative to the importing file's directory
- Configurations are deep-merged with main config taking precedence
- Circular imports are detected and prevented
- Imported files can themselves import other files

## Getting Started

1. **Single File**: Start with `sample_events.yaml` for a complete example
2. **Modular**: Use `events_main.yaml` as a template for modular configurations
3. **Specific Use Cases**: Check `ecommerce_events.yaml` or `trading_platform.yaml` for domain-specific examples
