"""
Simple test transcript generator for KG-Sentiment platform.

Just generates mock transcript data - no file I/O, no pipeline state creation.
"""

from datetime import datetime, timedelta
import json
import uuid
from pathlib import Path
from typing import Dict, Any

# Load transcript templates
TEMPLATES_PATH = Path(__file__).parent / "transcript_templates.json"
with open(TEMPLATES_PATH, 'r', encoding='utf-8') as f:
    TRANSCRIPT_TEMPLATES = json.load(f)


def generate_test_transcript(item: Dict[str, Any], content_type: str = "speech") -> dict:
    """Generate a test transcript with realistic content."""
    # Use existing ID from the item
    id = item['id']
    
    # Generate timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Use existing data from item
    date = item.get('date', (datetime.now() - timedelta(days=0)).strftime("%Y-%m-%d"))
    source_url = item.get('source_url', f"https://example.com/test/{content_type}_{timestamp}")
    
    # Generate transcript content
    transcript_content = generate_transcript_text(content_type, 0)
    
    # Return structured data (no file I/O)
    return {
        "id": id,
        "title": f"Test {content_type.title()} ({timestamp})",
        "date": date,
        "event_date": date,
        "type": content_type,
        "source_url": source_url,
        "timestamp": timestamp,
        "transcript": transcript_content
    }


def generate_transcript_text(content_type: str, index: int) -> str:
    """Generate realistic test transcript content from templates."""
    template = TRANSCRIPT_TEMPLATES.get(content_type, TRANSCRIPT_TEMPLATES["speech"])
    
    # Get the full template content and replace placeholders
    base_content = template.get("content", "This is a test transcript.")
    base_content = base_content.format(index=index)  # Replace {index} placeholder
    
    return base_content
