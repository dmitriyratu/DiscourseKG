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


def _build_js_code(action: NavigationAction | None) -> list[str]:
    """Generate JS code for the given action."""
    if not action:
        return []
    
    if action.type == "scroll":
        return [f"""
        (async () => {{
            const delay = ms => new Promise(r => setTimeout(r, ms));
            for (let i = 0; i < {action.value}; i++) {{
                const prev = document.body.scrollHeight;
                window.scrollBy(0, window.innerHeight);
                let start = Date.now();
                while (document.body.scrollHeight === prev && Date.now() - start < 2000) {{
                    await delay(100);
                }}
                await delay(500);
            }}
            window.scrollTo(0, document.body.scrollHeight);
        }})();
        """]
    
    if action.type == "click":
        selector = json.dumps(action.value)
        return [f"""
        (async () => {{
            let el = document.querySelector({selector});
            if (!el && {selector}.includes(':contains("')) {{
                const text = {selector}.split(':contains("')[1].split('")')[0];
                el = Array.from(document.querySelectorAll('a, button, span, div'))
                    .find(e => e.textContent.trim() === text);
            }}
            if (el) {{
                el.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                await new Promise(r => setTimeout(r, 200));
                el.click();
            }}
        }})();
        """]
    
    return []


def _get_delay(action: NavigationAction | None) -> float:
    """Get delay before HTML extraction based on action type."""
    if not action:
        return 2.0
    return 5.0 if action.type == "scroll" else 3.0


def _create_extraction_strategy() -> LLMExtractionStrategy:
    """Create LLM extraction strategy."""
    schema = PageExtraction.model_json_schema()
    
    return LLMExtractionStrategy(
        llm_config=LLMConfig(
            provider="openai/gpt-4o-mini", 
            api_token=os.getenv("OPENAI_API_KEY")
            ),
        instruction=EXTRACTION_PROMPT,
        schema=schema,
        extraction_type="schema",
        input_format="markdown",
        force_json_response=True,  # Force JSON output
        temperature=0.0,  # Pass directly as kwarg
        response_format={"type": "json_object"},  # Force JSON object (not array)
    )


class PageCrawler:
    """Wrapper for crawl4ai page observation."""
    
    def __init__(self, crawler: AsyncWebCrawler):
        self.crawler = crawler
    
    async def observe(self, url: str, action: NavigationAction | None = None, 
                      reuse_session: bool = False,
                      result_callback: Callable | None = None) -> PageExtraction:
        """Execute action and extract articles + next navigation."""
        config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            simulate_user=True,
            page_timeout=30000,
            remove_overlay_elements=True,
            word_count_threshold=100,
            extraction_strategy=_create_extraction_strategy(),
            js_code=_build_js_code(action),
            js_only=reuse_session,
            session_id=SESSION_ID,
            delay_before_return_html=_get_delay(action),
            excluded_tags=['script', 'style'],
        )
        
        result = await self.crawler.arun(url, config=config, session_id=SESSION_ID)
        
        if result_callback:
            result_callback(result)
        
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
