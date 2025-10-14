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


def generate_test_transcript(index: int):
    """Generate test transcript data structure (no file I/O)."""
    
    # Generate test data
    test_types = ["speech", "interview", "debate"]
    test_type = test_types[index % len(test_types)]
    
    # Create realistic test transcript
    transcript_content = generate_transcript_text(test_type, index)
    
    # Generate metadata
    date = (datetime.now() - timedelta(days=index)).strftime("%Y-%m-%d")
    year, month, day = date.split("-")
    
    # Generate unique timestamp for this run
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:19]
    
    # Unique URL per run
    source_url = f"https://example.com/test/{test_type}_{index}_{timestamp}"
    
    # Generate ID
    id = str(uuid.uuid4())
    
    # Return structured data (no file I/O)
    return {
        "id": id,
        "title": f"Test {test_type.title()} #{index} ({timestamp})",
        "date": date,
        "event_date": date,
        "type": test_type,
        "source_url": source_url,
        "location": "Test Location",
        "main_subject": "Test Speaker",
        "transcript": transcript_content,
        "speakers": ["Test Speaker"],
        "timestamp": timestamp
    }


def generate_transcript_text(content_type: str, index: int) -> str:
    """Generate realistic test transcript content from templates."""
    template = TRANSCRIPT_TEMPLATES.get(content_type, TRANSCRIPT_TEMPLATES["speech"])
    return template.format(index=index)