"""
Simple test transcript generator for KG-Sentiment platform.

Just generates mock transcript data - no file I/O, no pipeline state creation.
"""

from datetime import datetime, timedelta
import json
import uuid
from pathlib import Path

# Load transcript templates
TEMPLATES_PATH = Path(__file__).parent / "transcript_templates.json"
with open(TEMPLATES_PATH, 'r', encoding='utf-8') as f:
    TRANSCRIPT_TEMPLATES = json.load(f)


def generate_test_transcript(index: int, content_type: str = "speech") -> dict:
    """
    Generate a test transcript with realistic content.
    
    Args:
        index: Index number for the transcript
        content_type: Type of content (speech, debate, interview)
    
    Returns:
        Dictionary containing transcript data
    """
    # Generate unique ID
    id = f"test-{content_type}-{index}-{uuid.uuid4().hex[:8]}"
    
    # Generate timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Generate date (recent)
    date = (datetime.now() - timedelta(days=index)).strftime("%Y-%m-%d")
    
    # Generate source URL
    source_url = f"https://example.com/test/{content_type}_{index}_{timestamp}"
    
    # Generate transcript content
    transcript_content = generate_transcript_text(content_type, index)
    
    # Return structured data (no file I/O)
    return {
        "id": id,
        "title": f"Test {content_type.title()} #{index} ({timestamp})",
        "date": date,
        "event_date": date,
        "type": content_type,
        "source_url": source_url,
        "location": "Test Location",
        "main_subject": "Test Speaker",
        "speakers": ["Test Speaker"],
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
