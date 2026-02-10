"""
Simple test scrape content generator for DiscourseKG platform.

Just generates mock scrape data - no file I/O, no pipeline state creation.
"""

import json
from pathlib import Path
from typing import Dict, Any

# Load content templates
TEMPLATES_PATH = Path(__file__).parent / "transcript_templates.json"
with open(TEMPLATES_PATH, 'r', encoding='utf-8') as f:
    CONTENT_TEMPLATES = json.load(f)


def generate_test_transcript(item: Dict[str, Any], content_type: str = "speech") -> dict:
    """Generate test scrape content."""
    id = item['id']
    
    # Extract index from ID for template variation
    try:
        index = int(id.split('-')[2])
    except (IndexError, ValueError):
        index = 0
    
    scrape_content = generate_content_text(content_type, index)
    
    return {
        "id": id,
        "scrape": scrape_content
    }


def generate_content_text(content_type: str, index: int) -> str:
    """Generate realistic test content from templates."""
    template = CONTENT_TEMPLATES.get(content_type, CONTENT_TEMPLATES["speech"])
    
    # Get the full template content and replace placeholders
    base_content = template.get("content", "This is test content.")
    base_content = base_content.format(index=index)  # Replace {index} placeholder
    
    return base_content
