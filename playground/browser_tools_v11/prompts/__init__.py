"""Prompt management for research agent."""
import yaml
from pathlib import Path

def load_prompts():
    """Load prompts from YAML file."""
    prompts_file = Path(__file__).parent / "research.yaml"
    with open(prompts_file, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    return data['system_prompt'], data.get('user_prompt', '')

SYSTEM_PROMPT, USER_PROMPT = load_prompts()
