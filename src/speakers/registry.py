"""Speaker registry utilities."""

import json
from pathlib import Path

from src.config import config
from src.speakers.models import SpeakerRegistry


def get_display_name_to_id() -> dict[str, str]:
    """Map display_name -> speaker id for lookup."""
    speakers_file = Path(config.PROJECT_ROOT) / "data" / "speakers.json"
    with open(speakers_file) as f:
        registry = SpeakerRegistry(**json.load(f))
    return {s.display_name: key for key, s in registry.speakers.items()}


def get_tracked_display_names() -> list[str]:
    """Load display names from speakers.json."""
    return list(get_display_name_to_id().keys())
