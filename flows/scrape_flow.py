from prefect import flow, task
from datetime import datetime
from typing import Dict, Any
from src.shared.pipeline_state import PipelineStateManager
from src.shared.logging_utils import get_logger
from src.shared.persistence import save_data
from src.pipeline_config import PipelineStages
from src.collect.scrape_endpoint import ScrapeEndpoint

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
    
    Currently uses mock scraper - will be replaced with agent-based scraping.
    """
    logger.info(f"Starting scrape for {speaker} from {start_date} to {end_date}")
    
    # Using mock scraper - will be replaced with agent-based scraping
    logger.info("Using mock scraper (agent-based scraping to be implemented)")
    
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
        result_data = result.result()
        
        if result_data['success']:
            # Extract data once
            id = result_data['id']
            result_content = result_data['result']
            content_type = result_content.get('type', 'unknown')
            
            # Save the scraped data
            output_file = save_data(
                id,
                result_content,
                PipelineStages.SCRAPE,
                speaker=speaker
            )
            
            # Create pipeline state
            scrape_cycle = datetime.now().strftime("%Y-%m-%d_%H:00:00")
            manager.create_state(
                id, 
                scrape_cycle, 
                output_file, 
                url,
                speaker=speaker,
                content_type=content_type
            )
            
            logger.info(f"Completed scraping for item {id} -> {output_file}")
        else:
            # Handle failure
            logger.error(f"Failed scraping for URL {url}: {result_data['error']}")
    
    logger.info(f"Mock scrape complete for {speaker} - {len(mock_urls)} items processed")
    return {"status": "success", "mode": "mock", "items": len(mock_urls)}