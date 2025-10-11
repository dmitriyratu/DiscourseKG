from prefect import flow, task
from datetime import datetime, timedelta
from pathlib import Path
import json
import uuid
from pipeline.pipeline_state import PipelineStateManager
from src.utils.logging_utils import setup_logger
from src.config import config

logger = setup_logger("mock_scrape_flow", "mock_scrape_flow.log")

# Load transcript templates
TEMPLATES_PATH = Path(__file__).parent / "transcript_templates.json"
with open(TEMPLATES_PATH, 'r', encoding='utf-8') as f:
    TRANSCRIPT_TEMPLATES = json.load(f)


@flow
def mock_scrape_flow(num_items: int = 3):
    """
    Mock scraper that generates dummy transcripts to test the pipeline end-to-end.
    
    Emulates what a real scraper would do:
    1. Generate transcript content
    2. Save to data/raw/test/ directory
    3. Create pipeline state
    """
    logger.info(f"Generating {num_items} test transcripts")
    
    for i in range(num_items):
        generate_test_transcript.submit(i)
    
    logger.info("Mock scrape complete")


@task
def generate_test_transcript(index: int):
    """Generate one test transcript and ingest into pipeline."""
    manager = PipelineStateManager()
    
    # Generate test data
    test_types = ["speech", "interview", "debate"]
    test_type = test_types[index % len(test_types)]
    
    # Create realistic test transcript
    transcript_content = generate_transcript_text(test_type, index)
    
    # Generate metadata
    date = (datetime.now() - timedelta(days=index)).strftime("%Y-%m-%d")
    year, month, day = date.split("-")
    
    # Generate unique timestamp for this run
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:19]  # YYYYmmdd_HHMMSS_ms
    
    # Unique URL per run
    source_url = f"https://example.com/test/{test_type}_{index}_{timestamp}"
    
    # Generate ID
    id = str(uuid.uuid4())
    
    # Build structured data
    structured_data = {
        "id": id,
        "title": f"Test {test_type.title()} #{index} ({timestamp})",
        "date": date,
        "event_date": date,
        "type": test_type,
        "source_url": source_url,
        "location": "Test Location",
        "main_subject": "Test Speaker",
        "transcript": transcript_content,
        "speakers": ["Test Speaker"]
    }
    
    # Create unique file path: data/raw/test/{type}/{YYYY}/{MM}/{DD}/{filename}.json
    filename = f"{test_type}_test_{index}_{timestamp}.json"
    file_path = Path(config.RAW_DATA_PATH) / "test" / test_type / year / month / day / filename
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Save JSON
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(structured_data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved test transcript to {file_path}")
    
    # Create pipeline state
    scrape_cycle = datetime.now().strftime("%Y-%m-%d_%H:00:00")
    manager.create_state(id, scrape_cycle, str(file_path), source_url)
    
    logger.info(f"Created pipeline state for test item {index} (ID: {id})")
    
    return {"status": "success", "id": id, "file_path": str(file_path), "timestamp": timestamp}


def generate_transcript_text(content_type: str, index: int) -> str:
    """Generate realistic test transcript content from templates."""
    template = TRANSCRIPT_TEMPLATES.get(content_type, TRANSCRIPT_TEMPLATES["speech"])
    return template.format(index=index)


def cleanup_test_data():
    """Remove all test data and pipeline states. Use for fresh start."""
    import shutil
    
    # Remove test files
    test_dir = Path(config.RAW_DATA_PATH) / "test"
    if test_dir.exists():
        shutil.rmtree(test_dir)
        logger.info(f"Deleted test directory: {test_dir}")
    
    # Remove test entries from pipeline state
    manager = PipelineStateManager()
    states = manager._read_all_states()
    
    # Keep only non-test states
    non_test_states = [
        s for s in states 
        if not s.get('source_url', '').startswith('https://example.com/test/')
    ]
    
    removed_count = len(states) - len(non_test_states)
    if removed_count > 0:
        manager._write_all_states(non_test_states)
        logger.info(f"Removed {removed_count} test entries from pipeline state")
    
    print(f"✓ Cleaned up {removed_count} test items")


if __name__ == "__main__":
    # Run the mock scraper
    mock_scrape_flow(num_items=5)

