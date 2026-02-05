"""
Discoverer for finding content sources using autonomous web scraping.

This module handles real article discovery using the v13 DiscoveryAgent,
replacing the previous mock discovery implementation.
"""

import asyncio
import hashlib
import time
from datetime import datetime
from typing import Dict, Any, List

from src.discover.agent.discovery_agent import DiscoveryAgent
from src.discover.agent.models import Article
from src.discover.config import discovery_config, DiscoveryConfig
from src.discover.models import DiscoveredArticle, DiscoveryData, DiscoveryResult
from src.shared.persistence import save_data
from src.shared.pipeline_state import PipelineStateManager
from src.shared.pipeline_definitions import StageResult
from src.utils.logging_utils import get_logger
from src.utils.string_utils import slugify

logger = get_logger(__name__)


def _generate_discover_id(article: Article) -> str:
    """Generate unique ID from article: {date}-{title_slug}-{url_hash}."""
    date = article.publication_date or "unknown"
    title_slug = slugify(article.title, max_length=40)
    url_hash = hashlib.md5(article.url.encode()).hexdigest()[:6]
    return f"{date}-{title_slug}-{url_hash}"


def _to_discovered_article(article: Article, speaker: str) -> DiscoveredArticle:
    """Convert v13 Article to DiscoveredArticle."""
    return DiscoveredArticle(
        id=_generate_discover_id(article),
        title=article.title,
        url=article.url,
        publication_date=article.publication_date,
        date_score=article.date_score,
        date_source=article.date_source.value if article.date_source else "unknown",
        speaker=speaker
    )


class Discoverer:
    """
    Discoverer for finding content sources using autonomous web scraping.
    
    Uses the DiscoveryAgent to navigate websites and extract articles
    with intelligent date detection and filtering.
    """
    
    def __init__(self, config: DiscoveryConfig = None):
        self.config = config or discovery_config
        logger.debug("Discoverer initialized with real agent discovery")
    
    async def _run_agent_async(self, search_url: str, start_date: str, end_date: str) -> List[Article]:
        """Run the discovery agent asynchronously."""
        agent = DiscoveryAgent(headless=self.config.HEADLESS)
        return await agent.run(search_url, start_date, end_date)
    
    def discover_content(self, discovery_params: Dict[str, Any]) -> StageResult:
        """Discover content sources using the autonomous agent."""
        speaker = discovery_params['speaker']
        start_date = discovery_params['start_date']
        end_date = discovery_params['end_date']
        search_urls = discovery_params.get('search_urls', [])
        
        if not search_urls:
            logger.warning(f"No search URLs provided for speaker {speaker}")
            return self._create_empty_result(speaker, start_date, end_date)
        
        start_time = time.time()
        logger.info(f"Starting discovery for speaker: {speaker} ({len(search_urls)} search URLs)")
        
        run_timestamp = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
        discovery_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        manager = PipelineStateManager()
        all_discovered: List[DiscoveredArticle] = []
        total_found = 0
        duplicates_skipped = 0
        
        # Process each search URL
        for search_url in search_urls:
            logger.info(f"Searching: {search_url}")
            
            try:
                # Run agent (async wrapped in sync)
                articles = asyncio.run(self._run_agent_async(search_url, start_date, end_date))
                total_found += len(articles)
                
                # Process each article
                for article in articles:
                    # Filter by date score
                    if article.date_score is None or article.date_score < self.config.MIN_DATE_SCORE:
                        continue
                    
                    # Check for duplicates by article URL
                    if manager.get_by_source_url(article.url):
                        duplicates_skipped += 1
                        continue
                    
                    # Convert to DiscoveredArticle
                    discovered = _to_discovered_article(article, speaker)
                    
                    # Save to file (pass fallbacks since state doesn't exist yet)
                    file_path = save_data(
                        id=discovered.id,
                        data=discovered.model_dump(),
                        data_type="discover",
                        speaker=speaker,
                        search_url=search_url
                    )
                    
                    # Create pipeline state
                    manager.create_state(
                        id=discovered.id,
                        run_timestamp=run_timestamp,
                        file_path=file_path,
                        source_url=article.url,  # For scraping
                        search_url=search_url,   # For traceability
                        speaker=speaker
                    )
                    
                    all_discovered.append(discovered)
                    logger.debug(f"Discovered: {discovered.id}")
                    
            except Exception as e:
                logger.error(f"Error searching {search_url}: {e}", exc_info=True)
                continue
        
        processing_time = round(time.time() - start_time, 2)
        new_articles = len(all_discovered)
        
        logger.info(
            f"Discovery complete: {total_found} found, {new_articles} new, "
            f"{duplicates_skipped} duplicates skipped ({processing_time}s)"
        )
        
        return self._create_result(
            all_discovered, speaker, start_date, end_date,
            discovery_timestamp, total_found, new_articles, duplicates_skipped
        )
    
    def _create_empty_result(self, speaker: str, start_date: str, end_date: str) -> StageResult:
        """Create empty result when no search URLs are provided."""
        discovery_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return self._create_result([], speaker, start_date, end_date, discovery_timestamp, 0, 0, 0)
    
    def _create_result(
        self, 
        discovered_articles: List[DiscoveredArticle],
        speaker: str, 
        start_date: str, 
        end_date: str,
        discovery_timestamp: str,
        total_found: int,
        new_articles: int,
        duplicates_skipped: int
    ) -> StageResult:
        """Create StageResult with discovery data."""
        discovery_data = DiscoveryData(
            discovery_id=f"discovery-{discovery_timestamp}",
            discovered_articles=discovered_articles,
            speaker=speaker,
            date_range=f"{start_date} to {end_date}",
            total_found=total_found,
            new_articles=new_articles,
            duplicates_skipped=duplicates_skipped
        )
        
        artifact = DiscoveryResult(
            success=True,
            data=discovery_data,
            error_message=None
        )
        
        return StageResult(artifact=artifact.model_dump(), metadata=None)
