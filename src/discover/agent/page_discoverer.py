"""Crawl4ai wrapper for page observation and article discovery."""

import time
from difflib import Differ
from typing import List, Optional, Tuple

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode, LLMExtractionStrategy, LLMConfig

from src.discover.agent.js_builders import build_click_js, build_scroll_js
from src.discover.agent.models import ActionType, PageExtraction, NavigationAction, Article, ArticleExtraction
from src.discover.agent.prompts import build_extraction_prompt
from src.discover.agent.adblock_engine import EXCLUDED_SELECTOR
from src.discover.agent.date_voter import DateVoter
from src.discover.config import DiscoveryConfig, discovery_config
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)


class PageDiscoverer:
    """Wrapper for crawl4ai page observation and article discovery."""

    SESSION_ID = "discovery_session"

    def __init__(self, crawler: AsyncWebCrawler, config: DiscoveryConfig = discovery_config) -> None:
        self.crawler = crawler
        self.config = config
        self._last_markdown: Optional[str] = None

    def _diff_added_only(self, old: str, new: str) -> str:
        """Return only lines added in new relative to old (Differ, line-based)."""
        differ = Differ()
        result = differ.compare(old.splitlines(keepends=True), new.splitlines(keepends=True))
        return "".join(line[2:] for line in result if line.startswith("+ "))

    def _build_js_code(self, action: Optional[NavigationAction]) -> List[str]:
        """Generate JS code for the given action."""
        if action and action.type == ActionType.SCROLL:
            return [build_scroll_js()]
        if action and action.type == ActionType.CLICK and action.value:
            return [build_click_js(action.value)]
        return []

    def _crawler_config(
        self,
        action: Optional[NavigationAction],
        reuse_session: bool,
        extraction_strategy: Optional[LLMExtractionStrategy] = None,
    ) -> CrawlerRunConfig:
        kwargs: dict = {
            'cache_mode': CacheMode.BYPASS,
            'simulate_user': True,
            'page_timeout': 30000,
            'wait_until': 'domcontentloaded',
            'wait_for_timeout': 10000,
            'remove_overlay_elements': True,
            'magic': True,
            'word_count_threshold': 50,
            'js_code': self._build_js_code(action),
            'js_only': reuse_session,
            'session_id': self.SESSION_ID,
            'delay_before_return_html': 5.0,
            'excluded_tags': ['script', 'style'],
            'excluded_selector': EXCLUDED_SELECTOR,
        }
        if extraction_strategy is not None:
            kwargs['extraction_strategy'] = extraction_strategy
        return CrawlerRunConfig(**kwargs)

    def _create_extraction_strategy(self, delta_mode: bool = False) -> LLMExtractionStrategy:
        """Create LLM extraction strategy."""
        schema = PageExtraction.model_json_schema()
        instruction = build_extraction_prompt(delta_mode)
        return LLMExtractionStrategy(
            llm_config=LLMConfig(
                provider=f"openai/{self.config.OPENAI_MODEL}",
                api_token=self.config.OPENAI_API_KEY,
                temperature=self.config.OPENAI_TEMPERATURE,
            ),
            instruction=instruction,
            schema=schema,
            extraction_type="schema",
            input_format="markdown",
            force_json_response=True,
            apply_chunking=False,
        )

    async def observe(
        self,
        url: str,
        action: Optional[NavigationAction] = None,
        reuse_session: bool = False,
    ) -> Tuple[PageExtraction, Optional[dict]]:
        """Execute action and extract articles + next navigation. Returns (extraction, llm_info)."""
        result = await self.crawler.arun(
            url, config=self._crawler_config(action, reuse_session), session_id=self.SESSION_ID
        )
        if not result.success:
            return PageExtraction(), None

        markdown = result.markdown.raw_markdown
        use_delta = reuse_session and self._last_markdown is not None and action and action.type == ActionType.SCROLL
        if use_delta:
            extraction_content = self._diff_added_only(self._last_markdown, markdown)
        else:
            extraction_content = markdown
        self._last_markdown = markdown

        strategy = self._create_extraction_strategy(delta_mode=use_delta)

        llm_start = time.time()
        raw = await strategy.arun(url, [extraction_content])
        llm_time = time.time() - llm_start

        llm_info = {"markdown_len": len(markdown), "llm_time": llm_time}
        total_usage = getattr(strategy, "total_usage", None)
        if total_usage:
            llm_info.update({
                "input_tokens": total_usage.prompt_tokens,
                "output_tokens": total_usage.completion_tokens,
                "total_tokens": total_usage.total_tokens,
            })

        parsed = raw[0] if raw else {}
        try:
            ext = PageExtraction.model_validate(parsed)
        except (TypeError, ValueError) as e:
            mode = "delta" if use_delta else "full"
            logger.error(f"{mode.capitalize()} extraction parse failed: {e}")
            ext = PageExtraction()
        
        # Convert ArticleExtraction to Article after voting
        final_articles = []
        for article_extraction in ext.articles:
            vote_result = DateVoter.vote(article_extraction.date_candidates)
            final_article = Article(
                title=article_extraction.title,
                url=article_extraction.url,
                date_candidates=article_extraction.date_candidates,
                publication_date=vote_result.publication_date,
                date_score=vote_result.date_score,
                date_source=vote_result.date_source
            )
            final_articles.append(final_article)
        
        ext.articles = final_articles

        return ext, llm_info
