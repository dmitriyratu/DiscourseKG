"""Speaker registry utilities."""

import json

from src.speakers import SPEAKERS_FILE
from src.speakers.models import SpeakerRegistry


def get_tracked_display_names() -> list[str]:
    """Display names from speakers.json."""
    with open(SPEAKERS_FILE) as f:
        registry = SpeakerRegistry(**json.load(f))
    return list(registry.speakers)
