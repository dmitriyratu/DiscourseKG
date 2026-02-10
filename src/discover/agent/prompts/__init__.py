"""Prompt management for discovery."""
import yaml
from pathlib import Path
from typing import Tuple

from src.discover.agent.models import DateSource


def load_prompts() -> Tuple[str, str]:
    """Load prompts from YAML file."""
    prompts_file = Path(__file__).parent / "extraction.yaml"
    with open(prompts_file, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    return data['extraction_prompt'], data['delta_mode_suffix']

EXTRACTION_PROMPT_TEMPLATE, DELTA_MODE_SUFFIX = load_prompts()


def build_extraction_prompt(delta_mode: bool = False) -> str:
    """Build extraction instruction; date source data from DateSource.for_prompt()."""
    enum_values, source_bullets = DateSource.for_prompt()
    
    delta_suffix = DELTA_MODE_SUFFIX if delta_mode else ""
    
    prompt = EXTRACTION_PROMPT_TEMPLATE.format(
        date_source_enum_values=enum_values,
        date_source_bullets=source_bullets,
        delta_mode_suffix=delta_suffix
    )
    
    return prompt.strip()
