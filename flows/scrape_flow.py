from prefect import flow, task
from datetime import datetime
from typing import Dict, Any
from src.shared.pipeline_state import PipelineStateManager
from src.shared.logging_utils import get_logger
from src.shared.persistence import save_data
from src.collect.scrape_endpoint import ScrapeEndpoint
from src.app_config import config

logger = get_logger(__name__)


@task(name="scrape_item", retries=2, retry_delay_seconds=30)
def scrape_item(url: str, speaker: str, index: int) -> Dict[str, Any]:
    """Task to scrape article content."""
    try:
        logger.info("Calling ScrapeEndpoint...")
        
        # Create item dict for standardized interface
        item = {
            'url': url,
            'speaker': speaker,
            'index': index
        }
        
        result = ScrapeEndpoint().execute(item)
        logger.info(f"Scraping completed: {result}")
        return result
    except Exception as e:
        logger.error(f"Error scraping article: {str(e)}")
        raise


@flow
def scrape_flow(speaker: str, start_date: str, end_date: str):
    """
    Discover and scrape speaker transcripts from web sources in date range.
    
    TEMPORARY: Using mock scraper until agents are implemented.
    """
    logger.info(f"Starting scrape for {speaker} from {start_date} to {end_date}")
    
    # TEMPORARY: Use mock scraper until agents are ready
    logger.info("Using mock scraper (agents not yet implemented)")
    
    # Mock discovery: generate test transcript URLs
    MOCK_ITEM_COUNT = 3  # Number of mock items to generate
    mock_urls = [
        f"https://example.com/test/speech_{i}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        for i in range(MOCK_ITEM_COUNT)
    ]
    
    manager = PipelineStateManager()
    
    # Scrape each URL
    for i, url in enumerate(mock_urls):
        # Process the item
        result = scrape_item.submit(url, speaker, i)
        
        # Wait for result and handle persistence/state updates
        if result.result()['success']:
            # Save the raw data
            output_file = save_data(
                result.result()['id'],
                result.result()['result'],
                'raw'
            )
            
            # Create pipeline state
            scrape_cycle = datetime.now().strftime("%Y-%m-%d_%H:00:00")
            manager.create_state(
                result.result()['id'], 
                scrape_cycle, 
                output_file, 
                result.result()['url']
            )
            
            logger.info(f"Completed scraping for item {result.result()['id']} -> {output_file}")
        else:
            # Handle failure
            logger.error(f"Failed scraping for URL {url}: {result.result()['error']}")
    
    logger.info(f"Mock scrape complete for {speaker} - {len(mock_urls)} items processed")
    return {"status": "success", "mode": "mock", "items": len(mock_urls)}