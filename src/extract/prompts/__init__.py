"""Prompt management for extraction stage."""

import yaml
from pathlib import Path

_dir = Path(__file__).parent

with open(_dir / "phase1_entity.yaml", encoding="utf-8") as f:
    _p1 = yaml.safe_load(f)
with open(_dir / "phase2_passage.yaml", encoding="utf-8") as f:
    _p2 = yaml.safe_load(f)

ENTITY_SYSTEM_PROMPT: str = _p1["entity_system_prompt"]
ENTITY_USER_PROMPT: str = _p1["entity_user_prompt"]
PASSAGE_SYSTEM_PROMPT: str = _p2["passage_system_prompt"]
PASSAGE_USER_PROMPT: str = _p2["passage_user_prompt"]
