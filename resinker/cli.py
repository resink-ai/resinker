"""
Command-line interface for Resinker.
"""

import argparse
import logging
import sys
import os
from typing import List, Optional

from resinker.config.loader import load_config
from resinker.core.orchestrator import Orchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("resinker")


def setup_parser() -> argparse.ArgumentParser:
    """Set up the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Resinker - A YAML-based configuration system for mocking event streams"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run a simulation")
    run_parser.add_argument(
        "-c", "--config", required=True, help="Path to the YAML configuration file"
    )
    run_parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging"
    )

    # Validate command
    validate_parser = subparsers.add_parser(
        "validate", help="Validate a configuration file"
    )
    validate_parser.add_argument(
        "-c", "--config", required=True, help="Path to the YAML configuration file"
    )

    # Info command
    info_parser = subparsers.add_parser(
        "info", help="Display information about a configuration file"
    )
    info_parser.add_argument(
        "-c", "--config", required=True, help="Path to the YAML configuration file"
    )

    return parser


def run_command(args: argparse.Namespace):
    """Run a simulation using the provided configuration."""
    if args.verbose:
        logging.getLogger("resinker").setLevel(logging.DEBUG)

    config_path = args.config
    logger.info(f"Loading configuration from: {config_path}")

    try:
        config = load_config(config_path)
        logger.info(f"Configuration loaded: {config.version}")

        orchestrator = Orchestrator(config)
        orchestrator.initialize()
        orchestrator.run()
    except Exception as e:
        logger.error(f"Error running simulation: {e}", exc_info=True)
        sys.exit(1)


def validate_command(args: argparse.Namespace):
    """Validate a configuration file."""
    config_path = args.config
    logger.info(f"Validating configuration: {config_path}")

    try:
        config = load_config(config_path)
        logger.info(f"Configuration is valid: {config.version}")
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        sys.exit(1)


def info_command(args: argparse.Namespace):
    """Display information about a configuration file."""
    config_path = args.config
    logger.info(f"Loading configuration from: {config_path}")

    try:
        config = load_config(config_path)

        # Display basic configuration info
        print("\nResinker Configuration Information")
        print("================================")
        print(f"Version: {config.version}")

        # Simulation settings
        print("\nSimulation Settings:")
        print(f"  Duration: {config.simulation_settings.duration or 'Not specified'}")
        print(
            f"  Total Events: {config.simulation_settings.total_events or 'Not specified'}"
        )
        print(
            f"  Random Seed: {config.simulation_settings.random_seed or 'Not specified'}"
        )
        print(f"  Start Time: {config.simulation_settings.time_progression.start_time}")
        print(
            f"  Time Multiplier: {config.simulation_settings.time_progression.time_multiplier}"
        )

        # Initial entity counts
        if config.simulation_settings.initial_entity_counts:
            print("\nInitial Entity Counts:")
            for (
                entity_type,
                count,
            ) in config.simulation_settings.initial_entity_counts.items():
                print(f"  {entity_type}: {count}")

        # Schemas
        print(f"\nSchemas: {len(config.schemas)} defined")

        # Entities
        print(f"\nEntities: {len(config.entities)} defined")
        for entity_name in config.entities:
            print(f"  - {entity_name}")

        # Event Types
        print(f"\nEvent Types: {len(config.event_types)} defined")
        for event_type in config.event_types:
            print(f"  - {event_type}")

        # Scenarios
        if config.scenarios:
            print(f"\nScenarios: {len(config.scenarios)} defined")
            for scenario_name in config.scenarios:
                print(f"  - {scenario_name}")

        # Outputs
        if config.outputs:
            print(f"\nOutputs: {len(config.outputs)} configured")
            for i, output in enumerate(config.outputs):
                output_type = output.get("type", "unknown")
                enabled = output.get("enabled", True)
                print(
                    f"  {i+1}. {output_type} ({'enabled' if enabled else 'disabled'})"
                )

    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        sys.exit(1)


def main(args: Optional[List[str]] = None):
    """Main entry point for the CLI."""
    parser = setup_parser()
    parsed_args = parser.parse_args(args)

    if not parsed_args.command:
        parser.print_help()
        return

    if parsed_args.command == "run":
        run_command(parsed_args)
    elif parsed_args.command == "validate":
        validate_command(parsed_args)
    elif parsed_args.command == "info":
        info_command(parsed_args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
