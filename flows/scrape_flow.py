from prefect import flow, task
from datetime import datetime
from src.shared.pipeline_state import PipelineStateManager
from src.shared.logging_utils import setup_logger
from src.collect.scrape_endpoint import ScrapeEndpoint

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


@task(name="scrape_article", retries=2, retry_delay_seconds=30)
def scrape_and_ingest(url: str, speaker: str, index: int):
    """Task to scrape article content."""
    logger = setup_logger("scrape_task", "scrape_flow.log")
    try:
        logger.info("Calling ScrapeEndpoint...")
        result = ScrapeEndpoint().execute(url, speaker, index)
        logger.info(f"Scraping completed: {result}")
        return result
    except Exception as e:
        logger.error(f"Error scraping article: {str(e)}")
        raise