"""Crawl4ai wrapper for page observation."""
import os
import json
from typing import Callable
from dotenv import load_dotenv
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode, LLMExtractionStrategy, LLMConfig
from playground.browser_tools_v13.models import PageExtraction, NavigationAction
from playground.browser_tools_v13.prompts import EXTRACTION_PROMPT

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


def _get_delay(action: NavigationAction | None) -> float:
    """Get delay before HTML extraction based on action type."""
    # Both initial load and click use 2.0 (click now includes jump/wait/classify)
    return 2.0


def _create_extraction_strategy() -> LLMExtractionStrategy:
    """Create LLM extraction strategy."""
    schema = PageExtraction.model_json_schema()
    
    return LLMExtractionStrategy(
        llm_config=LLMConfig(
            provider="openai/gpt-4o-mini", 
            api_token=os.getenv("OPENAI_API_KEY"),
            temperature = 0.0,
            ),
        instruction=EXTRACTION_PROMPT,
        schema=schema,
        extraction_type="schema",
        input_format="markdown",
        force_json_response=True,  # Force JSON output
        apply_chunking=False,
    )


class PageCrawler:
    """Wrapper for crawl4ai page observation."""
    
    def __init__(self, crawler: AsyncWebCrawler):
        self.crawler = crawler
    
    async def observe(self, url: str, action: NavigationAction | None = None, 
                      reuse_session: bool = False,
                      result_callback: Callable | None = None) -> PageExtraction:
        """Execute action and extract articles + next navigation."""
        extraction_strategy = _create_extraction_strategy()
        config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            simulate_user=True,
            page_timeout=30000,
            remove_overlay_elements=True,
            word_count_threshold=100,
            extraction_strategy=extraction_strategy,
            js_code=_build_js_code(action),
            js_only=reuse_session,
            session_id=SESSION_ID,
            delay_before_return_html=_get_delay(action),
            excluded_tags=['script', 'style'],
        )
        
        result = await self.crawler.arun(url, config=config, session_id=SESSION_ID)
        
        if result_callback:
            result_callback(result, extraction_strategy)
        
        if not result.success or not result.extracted_content:
            return PageExtraction()
        
        # Parse and validate the extraction result
        try:
            parsed = json.loads(result.extracted_content)
            parsed = parsed[0] if parsed else {}
            return PageExtraction.model_validate(parsed)
        except (json.JSONDecodeError, ValueError) as e:
            print(f"[ERROR] Failed to parse extraction: {e}")
            print(f"[DEBUG] Raw content preview: {result.extracted_content[:200] if result.extracted_content else 'None'}")
            return PageExtraction()
