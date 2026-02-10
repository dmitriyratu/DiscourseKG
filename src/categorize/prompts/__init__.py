"""Prompt management for categorization."""
import yaml
from pathlib import Path
from typing import Tuple


def load_prompts() -> Tuple[str, str]:
    """Load prompts from YAML file."""
    prompts_file = Path(__file__).parent / "categorization.yaml"
    with open(prompts_file, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    return data['system_prompt'], data['user_prompt']

SYSTEM_PROMPT, USER_PROMPT = load_prompts()

