from prefect import flow, task
from datetime import datetime
from pathlib import Path
import json
import uuid
from src.shared.pipeline_state import PipelineStateManager
from src.shared.logging_utils import setup_logger
from tests.test_transcript_generator import generate_test_transcript

logger = setup_logger("scrape_flow", "scrape_flow.log")


@flow
def scrape_flow(speaker: str, start_date: str, end_date: str):
    """
    Discover and scrape speaker transcripts from web sources in date range.
    
    TEMPORARY: Using mock scraper until agents are implemented.
    """
    logger.info(f"Starting scrape for {speaker} from {start_date} to {end_date}")
    
    # TEMPORARY: Use mock scraper until agents are ready
    logger.info("Using mock scraper (agents not yet implemented)")
    
    # Mock discovery: generate 3 test transcript URLs
    mock_urls = [
        f"https://example.com/test/speech_{i}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        for i in range(3)
    ]
    
    # Scrape each URL
    results = []
    for i, url in enumerate(mock_urls):
        result = scrape_and_ingest.submit(url, speaker, i)
        results.append(result)
    
    logger.info(f"Mock scrape complete for {speaker} - {len(results)} items processed")
    return {"status": "success", "mode": "mock", "items": len(results)}


@task
def scrape_and_ingest(url: str, speaker: str, index: int):
    """
    Scrape one URL and ingest into pipeline.
    
    TEMPORARY: Uses mock data generator until agents are implemented.
    
    Steps:
    1. (FUTURE) Agent scrapes URL and extracts content
    2. Generate IDs and structure data
    3. Save to data/raw/
    4. Create pipeline state
    """
    manager = PipelineStateManager()
    
    # Deduplication check (idempotent)
    existing = manager.get_by_source_url(url)
    if existing:
        logger.info(f"URL already scraped: {url} (ID: {existing.id})")
        return {"status": "skipped", "reason": "duplicate_url"}
    
    # TEMPORARY: Use mock generator instead of real scraping
    logger.info(f"Mock scraping URL: {url}")
    result = generate_test_transcript(index)
    
    # Save to file (this is the responsibility of scrape_and_ingest)
    from src.config import config
    date = result.get('date')
    year, month, day = date.split("-")
    test_type = result.get('type')
    filename = f"{test_type}_test_{index}_{result.get('timestamp')}.json"
    file_path = Path(config.RAW_DATA_PATH) / "test" / test_type / year / month / day / filename
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Save JSON
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved test transcript to {file_path}")
    
    # Create pipeline state (this is the responsibility of scrape_and_ingest)
    scrape_cycle = datetime.now().strftime("%Y-%m-%d_%H:00:00")
    manager.create_state(
        result.get('id'), 
        scrape_cycle, 
        str(file_path), 
        result.get('source_url')
    )
    
    logger.info(f"Scraped and ingested: {url} -> {result.get('id', 'unknown')}")
    return {"status": "success", "id": result.get('id'), "url": url}