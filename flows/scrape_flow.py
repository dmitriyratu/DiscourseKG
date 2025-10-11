from prefect import flow, task
from datetime import datetime
from pathlib import Path
import json
import uuid
from pipeline.pipeline_state import PipelineStateManager
from src.utils.logging_utils import setup_logger

logger = setup_logger("scrape_flow", "scrape_flow.log")


@flow
def scrape_flow(speaker: str, start_date: str, end_date: str):
    """
    FUTURE: Discover and scrape speaker transcripts from web sources in date range.
    
    For now, creates dummy pipeline items for testing.
    Use tests.mock_scrape_flow for actual testing with generated data.
    """
    logger.info(f"Starting scrape for {speaker} from {start_date} to {end_date}")
    
    # FUTURE: Replace with actual agent discovery
    # available_urls = agent.discover_transcripts(speaker, start_date, end_date)
    
    # For now: create dummy items for testing
    scrape_cycle = datetime.now().strftime("%Y-%m-%d_%H:00:00")
    manager = PipelineStateManager()
    
    dummy_urls = [
        f"https://example.com/{speaker}/speech_{i}" 
        for i in range(3)
    ]
    
    for url in dummy_urls:
        # Check if already scraped
        existing = manager.get_by_source_url(url)
        if existing:
            logger.debug(f"Skipping {url} - already scraped")
            continue
        
        # FUTURE: scrape_and_ingest.submit(url, speaker)
        logger.info(f"Would scrape: {url}")


@task
def scrape_and_ingest(url: str, speaker: str):
    """
    FUTURE: Scrape one URL and ingest into pipeline.
    
    Steps:
    1. Agent scrapes URL and extracts content
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
    
    # FUTURE: Agent scrapes
    # scraped = agent.scrape(url)
    
    # Generate ID
    id = str(uuid.uuid4())
    
    # FUTURE: Build and save structured JSON
    # structured_data = {
    #     "id": id,
    #     "title": scraped['title'],
    #     "date": scraped['date'],
    #     "type": scraped['type'],
    #     "source_url": url,
    #     "transcript": scraped['transcript'],
    #     "speakers": scraped['speakers'],
    #     ...
    # }
    # file_path = save_raw_json(structured_data, speaker)
    
    # Create pipeline state
    # scrape_cycle = datetime.now().strftime("%Y-%m-%d_%H:00:00")
    # manager.create_state(id, scrape_cycle, file_path, url)
    
    logger.info(f"Scraped and ingested: {url}")
    return {"status": "success", "id": id}
