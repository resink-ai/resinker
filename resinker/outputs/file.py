"""
File output handler module.
"""

import logging
import json
import os
from typing import Dict, Any, Optional, TextIO
from datetime import datetime

from resinker.core.orchestrator import Event

logger = logging.getLogger(__name__)


class FileOutputHandler:
    """Handler for outputting events to a file."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.format = config.get("format", "json")
        self.file_path = config.get("file_path", "events.json")
        self.file_rotation = config.get("file_rotation")
        self.file: Optional[TextIO] = None
        self.current_file_path: Optional[str] = None
        self.events_written = 0
        self.rotation_count = 0

        # Create the output directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(self.file_path)), exist_ok=True)

        # Open the file
        self._open_file()

    def _open_file(self):
        """Open the output file."""
        if self.file:
            self.file.close()

        if self.file_rotation:
            # Apply rotation pattern
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename, ext = os.path.splitext(self.file_path)
            self.current_file_path = (
                f"{filename}_{timestamp}_{self.rotation_count}{ext}"
            )
            self.rotation_count += 1
        else:
            self.current_file_path = self.file_path

        logger.info(f"Opening output file: {self.current_file_path}")
        self.file = open(self.current_file_path, "w")
        self.events_written = 0

        # Start a JSON array if using JSON format
        if self.format.startswith("json"):
            self.file.write("[\n")

    def emit_event(self, event: Event):
        """Emit an event to the file."""
        if not self.file:
            self._open_file()

        # Check if we need to rotate the file
        if self.file_rotation == "count" and self.events_written >= 1000:
            self._close_json_array()
            self._open_file()

        # Write the event
        if self.format == "json_pretty":
            event_json = json.dumps(event.to_dict(), indent=2)
        else:
            event_json = json.dumps(event.to_dict())

        # Add a comma if not the first event
        if self.events_written > 0:
            self.file.write(",\n")

        self.file.write(event_json)
        self.file.flush()
        self.events_written += 1

    def _close_json_array(self):
        """Close the JSON array in the file."""
        if self.file and self.format.startswith("json"):
            self.file.write("\n]")
            self.file.flush()

    def __del__(self):
        """Cleanup when the handler is destroyed."""
        self._close_json_array()
        if self.file:
            self.file.close()
