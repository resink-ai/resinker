"""
Standard output handler module.
"""

import logging
import json
from typing import Dict, Any

from resinker.core.orchestrator import Event

logger = logging.getLogger(__name__)


class StdoutOutputHandler:
    """Handler for outputting events to standard output."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.format = config.get("format", "json")

    def emit_event(self, event: Event):
        """Emit an event to standard output."""
        if self.format == "json_pretty":
            print(json.dumps(event.to_dict(), indent=2))
        else:
            print(json.dumps(event.to_dict()))
