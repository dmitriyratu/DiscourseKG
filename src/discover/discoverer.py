"""
Discoverer for finding content sources using autonomous web scraping.

This module handles real article discovery using the v13 DiscoveryAgent,
replacing the previous mock discovery implementation.
"""

import asyncio
import time
from datetime import datetime
from typing import List

from src.discover.agent.date_voter import DateVoter
from src.discover.agent.discovery_agent import DiscoveryAgent
from src.discover.agent.discovery_logger import DiscoveryLogger, get_existing_source_urls
from src.discover.agent.models import Article
from src.discover.config import discovery_config, DiscoveryConfig
from src.discover.models import DiscoveredArticle, DiscoveryData, DiscoveryResult, DiscoveryRequest
from src.shared.persistence import save_data
from src.shared.pipeline_state import PipelineStateManager
from src.shared.pipeline_definitions import PipelineStages, StageResult
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)


class Discoverer:
    """
    Discoverer for finding content sources using autonomous web scraping.
    
    Uses the DiscoveryAgent to navigate websites and extract articles
    with intelligent date detection and filtering.
    """
    
    def __init__(self, config: DiscoveryConfig = discovery_config):
        self.config = config
    
    async def _run_agent_async(self, search_url: str, start_date: str, end_date: str, existing_urls: set) -> tuple:
        """Run the discovery agent asynchronously."""
        agent = DiscoveryAgent(config=self.config)
        return await agent.run(search_url, start_date, end_date, existing_urls=existing_urls)
    
    def discover_content(self, discovery_params: DiscoveryRequest) -> StageResult:
        """Discover content sources using the autonomous agent."""
        if not discovery_params.search_urls:
            logger.warning("No search URLs provided")
            return self._create_result(discovery_params, [], 0, 0)
        
        start_time = time.time()
        logger.info(f"Starting discovery ({len(discovery_params.search_urls)} search URLs)")
        
        run_timestamp = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
        manager = PipelineStateManager()
        all_discovered: List[DiscoveredArticle] = []
        total_found = 0
        duplicates_skipped = 0
        all_dates: List[str] = []
        total_all = 0

        end_date = discovery_params.end_date or datetime.now().strftime("%Y-%m-%d")
        existing_urls = get_existing_source_urls()
        for search_url in discovery_params.search_urls:
            logger.info(f"Searching: {search_url}")

            try:
                articles, all_articles = asyncio.run(self._run_agent_async(search_url, discovery_params.start_date, end_date, existing_urls))
                total_found += len(articles)
                total_all += len(all_articles)
                for a in all_articles:
                    if getattr(a, "publication_date", None):
                        all_dates.append(a.publication_date)
                
                for article in articles:
                    if article.date_score is None or article.date_score < DateVoter.THRESHOLD:
                        continue
                    
                    if manager.get_state_by_source_url(article.url):
                        duplicates_skipped += 1
                        continue
                    
                    discovered = DiscoveredArticle.from_article(article, search_url=search_url)
                    file_path = save_data(discovered, discovered.model_dump(mode='json'), PipelineStages.DISCOVER.value)
                    manager.record_discover_result(discovered, run_timestamp, file_path)
                    existing_urls.add(article.url)
                    all_discovered.append(discovered)
                    logger.debug(f"Discovered: {discovered.id}")
                    
            except Exception as e:
                logger.error(f"Error searching {search_url}: {e}", exc_info=True)
                continue
        
        processing_time = round(time.time() - start_time, 2)
        date_min = min(all_dates) if all_dates else None
        date_max = max(all_dates) if all_dates else None
        DiscoveryLogger().aggregate_complete(
            all_discovered, total_found, total_all, duplicates_skipped, processing_time,
            discovery_params.start_date, end_date, date_min, date_max
        )
        return self._create_result(discovery_params, all_discovered, total_found, duplicates_skipped)
    
    def _create_result(
        self,
        request: DiscoveryRequest,
        discovered_articles: List[DiscoveredArticle],
        total_found: int,
        duplicates_skipped: int
    ) -> StageResult:
        """Create StageResult with discovery data."""
        discovery_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        discovery_id = f"discovery-{discovery_timestamp}"
        
        discovery_data = DiscoveryData(
            discovery_id=discovery_id,
            discovered_articles=discovered_articles,
            date_range=f"{request.start_date} to {request.end_date or 'present'}",
            total_found=total_found,
            new_articles=len(discovered_articles),
            duplicates_skipped=duplicates_skipped
        )
        
        return StageResult(
            artifact=DiscoveryResult(
                id=discovery_id,
                success=True,
                data=discovery_data,
                error_message=None
            ).model_dump(mode='json'),
            metadata={}
        )
