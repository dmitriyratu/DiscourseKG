"""
Simple test scrape content generator for DiscourseKG platform.

Just generates mock scrape data - no file I/O, no pipeline state creation.
"""

from datetime import datetime, timedelta
import json
import uuid
from pathlib import Path
from typing import Dict, Any

# Load content templates
TEMPLATES_PATH = Path(__file__).parent / "transcript_templates.json"
with open(TEMPLATES_PATH, 'r', encoding='utf-8') as f:
    CONTENT_TEMPLATES = json.load(f)


def generate_test_transcript(item: Dict[str, Any], content_type: str = "speech") -> dict:
    """Generate test scrape content with realistic data."""
    # Use existing ID from the item
    id = item['id']
    
    # Generate timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Use existing data from item
    date = item.get('content_date', (datetime.now() - timedelta(days=0)).strftime("%Y-%m-%d"))
    source_url = item.get('source_url', f"https://example.com/test/{content_type}_{timestamp}")
    
    # Generate scrape content
    scrape_content = generate_content_text(content_type, 0)
    
    # Return structured data (no file I/O)
    return {
        "id": id,
        "title": f"Test {content_type.title()} ({timestamp})",
        "content_date": date,
        "content_type": content_type,
        "source_url": source_url,
        "timestamp": timestamp,
        "scrape": scrape_content
    }


def generate_content_text(content_type: str, index: int) -> str:
    """Generate realistic test content from templates."""
    template = CONTENT_TEMPLATES.get(content_type, CONTENT_TEMPLATES["speech"])
    
    # Get the full template content and replace placeholders
    base_content = template.get("content", "This is test content.")
    base_content = base_content.format(index=index)  # Replace {index} placeholder
    
    return base_content
