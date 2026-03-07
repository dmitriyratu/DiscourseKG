"""Prompt management for extraction stage."""

import yaml
from pathlib import Path

_prompts_file = Path(__file__).parent / "extraction.yaml"
with open(_prompts_file, 'r', encoding='utf-8') as _f:
    _data = yaml.safe_load(_f)

ENTITY_SYSTEM_PROMPT: str = _data['entity_system_prompt']
ENTITY_USER_PROMPT: str = _data['entity_user_prompt']
PASSAGE_SYSTEM_PROMPT: str = _data['passage_system_prompt']
PASSAGE_USER_PROMPT: str = _data['passage_user_prompt']
