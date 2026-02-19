"""
Scraper for collecting speaker transcripts from web sources.

Uses domain-specific extractors (cached or LLM-generated) to extract
primary content from HTML.
"""

from src.scrape.engine.extractor_manager import ExtractorManager
from src.scrape.models import ScrapingResult, ScrapingData, ScrapeContext
from src.shared.pipeline_definitions import StageResult


class Scraper:
    """
    Scrapes content from web sources using domain-specific extractors.

    Delegates extractor resolution to ExtractorManager, fetches HTML,
    runs extractor, and returns StageResult.
    """

    def __init__(self) -> None:
        self.extractor_manager = ExtractorManager()

    def scrape_content(self, processing_context: ScrapeContext) -> StageResult:
        """Scrape content from the provided processing context."""
        url = processing_context.source_url
        html = self.extractor_manager.fetch_html(url)


        extract_function = self.extractor_manager.get_or_create_extractor(url)
        scrape_text = extract_function(html)

        return self._create_result(processing_context.id, scrape_text)

    def _create_result(self, id: str, scrape_text: str) -> StageResult:
        """Helper to create StageResult with separated artifact and metadata."""
        scraping_data = ScrapingData(
            scrape=scrape_text,
            word_count=len(scrape_text.split()),
        )
        artifact = ScrapingResult(
            id=id, 
            success=True, 
            data=scraping_data, 
            error_message=None
            )

        return StageResult(
            artifact=artifact.model_dump(), 
            metadata={}
        )
