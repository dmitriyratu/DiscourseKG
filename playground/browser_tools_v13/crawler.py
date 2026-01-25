"""Crawl4ai wrapper for page observation."""
import json
import os
from typing import Callable

from dotenv import load_dotenv
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode, LLMExtractionStrategy, LLMConfig

from playground.browser_tools_v13.models import PageExtraction, NavigationAction
from playground.browser_tools_v13.prompts import EXTRACTION_PROMPT, EXTRACTION_PROMPT_DELTA_SUFFIX

load_dotenv()

SESSION_ID = "scraping_session"


def _build_jump_wait_js() -> str:
    """Generate JS code to jump to bottom once and wait for DOM to potentially grow."""
    return """
        const delay = ms => new Promise(r => setTimeout(r, ms));
        const waitMs = 1500;
        const pollInterval = 150;
        const prevHeight = document.body.scrollHeight;
        
        // Jump to bottom once
        window.scrollTo(0, document.body.scrollHeight);
        
        // Wait and poll to see if DOM grows (up to 1500ms)
        let elapsed = 0;
        while (elapsed < waitMs) {
            await delay(pollInterval);
            elapsed += pollInterval;
            if (document.body.scrollHeight > prevHeight) break;
        }
        
        // Final scroll to bottom and short delay
        window.scrollTo(0, document.body.scrollHeight);
        await delay(500);
    """


def _build_js_code(action: NavigationAction | None) -> list[str]:
    """Generate JS code for the given action."""
    if not action:
        # Initial load: jump to bottom once → wait → done. No loop.
        # Python handles repeating if target articles not found.
        return [f"""
        (async () => {{
            {_build_jump_wait_js()}
        }})();
        """]
    
    if action.type == "click":
        selector = json.dumps(action.value)
        # Click element, then run jump/wait/classify
        return [f"""
        (async () => {{
            const delay = ms => new Promise(r => setTimeout(r, ms));
            
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
            
            // Then run jump/wait/classify
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
        'word_count_threshold': 100,
        'js_code': _build_js_code(action),
        'js_only': reuse_session,
        'session_id': SESSION_ID,
        'delay_before_return_html': 2.0,
        'excluded_tags': ['script', 'style'],
        'excluded_selector': 'aside, .sidebar, .advertisement, .ads, .social-share, .menu, .breadcrumb',
    }
    if extraction_strategy is not None:
        kwargs['extraction_strategy'] = extraction_strategy
    return CrawlerRunConfig(**kwargs)


def _create_extraction_strategy(delta_mode: bool = False) -> LLMExtractionStrategy:
    """Create LLM extraction strategy."""
    schema = PageExtraction.model_json_schema()
    instruction = EXTRACTION_PROMPT + EXTRACTION_PROMPT_DELTA_SUFFIX if delta_mode else EXTRACTION_PROMPT
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

    async def observe(
        self,
        url: str,
        action: NavigationAction | None = None,
        reuse_session: bool = False,
        result_callback: Callable | None = None,
        last_markdown_length: int = 0,
    ) -> tuple[PageExtraction, int]:
        """Execute action and extract articles + next navigation. Returns (extraction, markdown_len)."""
        use_delta = action is None and last_markdown_length > 0

        if use_delta:
            result = await self.crawler.arun(
                url, config=_crawler_config(action, reuse_session), session_id=SESSION_ID
            )
            if not result.success:
                return PageExtraction(), 0
            markdown = result.markdown.raw_markdown
            delta = markdown[last_markdown_length:]
            strategy = _create_extraction_strategy(delta_mode=True)
            raw = await strategy.arun(url, [delta])
            parsed = raw[0] if raw else {}
            try:
                ext = PageExtraction.model_validate(parsed)
            except (TypeError, ValueError) as e:
                print(f"[ERROR] Delta extraction parse failed: {e}")
                ext = PageExtraction()
            return ext, len(markdown)

        strategy = _create_extraction_strategy()
        result = await self.crawler.arun(
            url,
            config=_crawler_config(action, reuse_session, extraction_strategy=strategy),
            session_id=SESSION_ID,
        )
        if result_callback:
            result_callback(result, strategy)
        if not result.success or not result.extracted_content:
            return PageExtraction(), 0
        try:
            parsed = json.loads(result.extracted_content)
            parsed = parsed[0] if parsed else {}
            ext = PageExtraction.model_validate(parsed)
        except (json.JSONDecodeError, ValueError) as e:
            print(f"[ERROR] Failed to parse extraction: {e}")
            print(f"[DEBUG] Raw content preview: {result.extracted_content[:200] if result.extracted_content else 'None'}")
            ext = PageExtraction()
        return ext, len(result.markdown.raw_markdown)
