"""Prompt management for extractor generation."""
import yaml
from pathlib import Path
from typing import Tuple


def load_prompts() -> Tuple[str, str]:
    """Load prompts from YAML file."""
    prompts_file = Path(__file__).parent / "extraction.yaml"
    with open(prompts_file, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    return data['system_prompt'], data['user_prompt']


SYSTEM_PROMPT, USER_PROMPT = load_prompts()


def build_extractor_prompts(instructions: str, html_sample: str) -> Tuple[str, str]:
    """Build system and user prompts for extractor generation."""
    return (
        SYSTEM_PROMPT.format(instructions=instructions),
        USER_PROMPT.format(html_sample=html_sample),
    )
