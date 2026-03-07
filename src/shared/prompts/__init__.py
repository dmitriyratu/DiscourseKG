"""Shared prompt fragments."""

import yaml
from pathlib import Path

_prompts_dir = Path(__file__).parent
with open(_prompts_dir / "speaker_naming.yaml") as f:
    _data = yaml.safe_load(f)

CANONICAL_NAMING_RULE: str = _data["canonical_naming_rule"].strip()
