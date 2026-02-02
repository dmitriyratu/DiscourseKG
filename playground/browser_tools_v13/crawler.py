"""Crawl4ai wrapper for page observation."""
import json
import os
import time
from difflib import Differ
from typing import Callable

from dotenv import load_dotenv
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode, LLMExtractionStrategy, LLMConfig

from playground.browser_tools_v13.models import PageExtraction, NavigationAction, Article, ArticleExtraction, DateVoteResult
from playground.browser_tools_v13.prompts import build_extraction_prompt
from playground.browser_tools_v13.date_voter import DateVoter
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)

load_dotenv()

SESSION_ID = "scraping_session"
SCROLL_WAIT_MS = 4000
SCROLL_POLL_MS = 150


def _diff_added_only(old: str, new: str) -> str:
    """Return only lines added in new relative to old (Differ, line-based)."""
    differ = Differ()
    result = differ.compare(old.splitlines(keepends=True), new.splitlines(keepends=True))
    return "".join(line[2:] for line in result if line.startswith("+ "))


def _build_jump_wait_js() -> str:
    """Generate JS code to scroll progressively to target and wait for DOM to potentially grow."""
    return f"""
        const delay = ms => new Promise(r => setTimeout(r, ms));
        await delay(100);
        
        const target = document.body.scrollHeight;
        const viewport = window.innerHeight;
        let current = window.scrollY;
        
        // Scroll incrementally to target
        while (current < target) {{
            current = Math.min(current + viewport * 0.8, target);
            window.scrollTo(0, current);
            await delay(300);
        }}
        
        // Wait for potential growth (up to SCROLL_WAIT_MS)
        const prevHeight = document.body.scrollHeight;
        let elapsed = 0;
        while (elapsed < {SCROLL_WAIT_MS}) {{
            await delay({SCROLL_POLL_MS});
            elapsed += {SCROLL_POLL_MS};
            if (document.body.scrollHeight > prevHeight) break;
        }}
        
        // Final scroll to current bottom (may have grown) and short delay
        window.scrollTo(0, document.body.scrollHeight);
        await delay(500);
    """


def _build_js_code(action: NavigationAction | None) -> list[str]:
    """Generate JS code for the given action."""
    if action and action.type == "scroll":
        # Explicit scroll: scroll progressively to target → wait → done.
        return [f"""
        (async () => {{
            await new Promise(r => setTimeout(r, 100));
            {_build_jump_wait_js()}
        }})();
        """]
    
    if action and action.type == "click":
        selector = json.dumps(action.value)
        # Click element, then run jump/wait/classify
        return [f"""
        (async () => {{
            const delay = ms => new Promise(r => setTimeout(r, ms));
            await delay(100);
            
            // Click the element
            let el = document.querySelector({selector});
            if (!el && {selector}.includes(':contains("')) {{
                const text = {selector}.split(':contains("')[1].split('")')[0];
                el = Array.from(document.querySelectorAll('a, button, span, div'))
                    .find(e => e.textContent.trim() === text);
            }}
            if (el) {{
                el.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                await delay(200);
                el.click();
            }}
            
            // Wait for navigation/page update
            await delay(1000);
            {_build_jump_wait_js()}
        }})();
        """]
    
    return []


def _crawler_config(
    action: NavigationAction | None,
    reuse_session: bool,
    extraction_strategy: LLMExtractionStrategy | None = None,
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
        'js_code': _build_js_code(action),
        'js_only': reuse_session,
        'session_id': SESSION_ID,
        'delay_before_return_html': 2.0,
        'excluded_tags': ['script', 'style'],
        'excluded_selector': (
            'aside, .sidebar, .advertisement, .ads, .social-share, .menu, .breadcrumb, '
            '[role="dialog"], .modal, .popup, .overlay, #overlay, [data-dialog], .lightbox'
        ),
    }
    if extraction_strategy is not None:
        kwargs['extraction_strategy'] = extraction_strategy
    return CrawlerRunConfig(**kwargs)


def _create_extraction_strategy(delta_mode: bool = False) -> LLMExtractionStrategy:
    """Create LLM extraction strategy."""
    schema = PageExtraction.model_json_schema()
    instruction = build_extraction_prompt(delta_mode)
    return LLMExtractionStrategy(
        llm_config=LLMConfig(
            provider="openai/gpt-4o-mini",
            api_token=os.getenv("OPENAI_API_KEY"),
            temperature=0.0,
        ),
        instruction=instruction,
        schema=schema,
        extraction_type="schema",
        input_format="markdown",
        force_json_response=True,
        apply_chunking=False,
    )


class PageCrawler:
    """Wrapper for crawl4ai page observation."""

    def __init__(self, crawler: AsyncWebCrawler):
        self.crawler = crawler
        self._last_markdown: str | None = None

    async def observe(
        self,
        url: str,
        action: NavigationAction | None = None,
        reuse_session: bool = False,
        result_callback: Callable | None = None,
    ) -> tuple[PageExtraction, int]:
        """Execute action and extract articles + next navigation. Returns (extraction, markdown_len)."""
        result = await self.crawler.arun(
            url, config=_crawler_config(action, reuse_session), session_id=SESSION_ID
        )
        if not result.success:
            return PageExtraction(), 0

        markdown = result.markdown.raw_markdown
        use_delta = reuse_session and self._last_markdown is not None and action and action.type == "scroll"
        if use_delta:
            extraction_content = _diff_added_only(self._last_markdown, markdown)
        else:
            extraction_content = markdown
        self._last_markdown = markdown

        strategy = _create_extraction_strategy(delta_mode=use_delta)

        llm_start = time.time()
        raw = await strategy.arun(url, [extraction_content])
        llm_time = time.time() - llm_start
        if result_callback:
            result_callback(result, strategy, llm_time)

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
        
        # Create new PageExtraction with final Articles
        ext.articles = final_articles

        return ext, len(markdown)
