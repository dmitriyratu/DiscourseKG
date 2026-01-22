"""Core scraping functions for V12 - Single comprehensive observation tool."""
import asyncio
import sys
import json
import os
from typing import Optional, List, Dict, Union, Literal, Any
from pydantic import BaseModel
from dotenv import load_dotenv
from crawl4ai import (
    AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode,
    LLMExtractionStrategy, LLMConfig, DefaultMarkdownGenerator, VirtualScrollConfig
)
from crawl4ai.models import CrawlResult

load_dotenv()

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

async def _run_crawler(url: str, config: CrawlerRunConfig, crawler: AsyncWebCrawler):
    """Internal helper to execute crawler with session persistence."""
    return await crawler.arun(url, config=config, session_id="scraping_session")

class ClickAction(BaseModel):
    type: Literal["click"]
    value: str
    kind: str

class ScrollAction(BaseModel):
    type: Literal["scroll"]
    value: int

NavigationAction = Union[ClickAction, ScrollAction]

class ArticleWithDate(BaseModel):
    title: str
    url: str
    publication_date: Optional[str] = None
    date_confidence: Literal["HIGH", "MEDIUM", "LOW", "NONE"]
    date_source: Literal["datetime_attr", "schema_org", "url_path", "near_title", "metadata"]

class ArticleExtraction(BaseModel):
    """LLM extraction result including articles and navigation from cleaned HTML."""
    articles: List[ArticleWithDate]
    navigation_action: Optional[NavigationAction] = None
    extraction_issues: List[str] = []

class NavigationOption(BaseModel):
    kind: str
    description: str
    action: NavigationAction

class PageObservation(BaseModel):
    """Complete page observation (articles + navigation)."""
    url: str
    articles: List[ArticleWithDate]
    navigation_options: List[NavigationOption]
    extraction_error: Optional[str] = None
    failed_output: Optional[str] = None
    html_stats: Optional[Dict[str, Any]] = None

def _prepare_action(action: Optional[Dict]) -> tuple[List[str], Optional[VirtualScrollConfig]]:
    """Prepare JS code and scroll config for action."""
    js_code = []
    virtual_scroll_config = None
    
    if not action:
        return js_code, virtual_scroll_config
    
    if action["type"] == "scroll":
        scroll_count = action['value']
        # More robust scroll approach with waiting
        js_code.append(f"""
        (async () => {{
            const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));
            for (let i = 0; i < {scroll_count}; i++) {{
                const prevHeight = document.body.scrollHeight;
                window.scrollBy(0, window.innerHeight);
                
                // Wait up to 2 seconds for height change
                let start = Date.now();
                while (document.body.scrollHeight === prevHeight && Date.now() - start < 2000) {{
                    await delay(100);
                }}
                await delay(500); // Small pause for stability
            }}
            window.scrollTo(0, document.body.scrollHeight);
        }})();
        """)
    elif action["type"] == "click":
        selector_escaped = json.dumps(action['value'])
        js_code.append(f"""
        (async () => {{
            let selector = {selector_escaped};
            let el = null;
            
            if (selector.includes(':contains("')) {{
                const text = selector.split(':contains("')[1].split('")')[0];
                el = Array.from(document.querySelectorAll('a, button, span, div'))
                          .find(e => e.textContent.trim() === text || e.innerText.trim() === text);
            }} else {{
                el = document.querySelector(selector);
            }}
            
            if (!el) return;
            el.scrollIntoView({{behavior: 'smooth', block: 'center'}});
            await new Promise(r => setTimeout(r, 200));
            el.click();
        }})();
        """)
    
    return js_code, virtual_scroll_config

def _get_extraction_instruction() -> str:
    """Get LLM instruction for article extraction."""
    return """
        Extract articles with publication dates and navigation links from this page.
        
        CRITICAL: This page may use infinite scroll, meaning content accumulates as you scroll.
        You MUST process the ENTIRE document from top to bottom. Do NOT stop at the first few articles.
        Scan through ALL content systematically and extract EVERY article you find, regardless of position.
        
        CRITICAL FOR INFINITE SCROLL: When content accumulates (HTML grows), newer content is typically at the TOP,
        but OLDER content appears as you scroll DOWN. You MUST scan through the ENTIRE document including:
        - The middle sections (often overlooked)
        - The bottom sections (where older articles appear after scrolling)
        - Do NOT assume articles at the top are the only ones - extract from ALL positions in the document
        
        CRITICAL: You MUST return a JSON object with this EXACT structure:
        {
          "articles": [array of article objects],
          "navigation_action": object or null,
          "extraction_issues": [array of strings]
        }
        
        Do NOT return just an array of articles. You MUST wrap them in the object structure above.
        
        CRITICAL: Extract PUBLICATION dates only (when article was published).
        - Look for dates in these locations (in priority order):
          1. <time datetime> attributes (most reliable)
          2. schema.org datePublished (structured data)
          3. URL path dates (/2025/01/15/)
          4. "Published on..." text near titles
          5. Other metadata sources (classify as "metadata")
        
        IMPORTANT: Process the document systematically:
        - Start from the beginning and work through to the end
        - Extract ALL articles you encounter, not just the first few
        - If content appears repeated, still extract it (deduplication happens later)
        - Pay special attention to content that appears later in the document - it may be newly loaded
        - For infinite scroll pages: Articles further down in the HTML are typically OLDER dates
        - You MUST extract articles from ALL sections: beginning, middle, AND end of the document
        - If the HTML is long (many thousands of characters), that means there are MANY articles - extract them ALL
        
        For each article:
                - title: Article title
                - url: Full URL
                - publication_date: YYYY-MM-DD format ONLY (e.g., 2025-01-15). Never use other formats.
                - date_confidence: HIGH, MEDIUM, LOW, NONE
                - date_source: Where found (datetime_attr, schema_org, url_path, near_title, metadata)
        
        Pagination Detection:
                - navigation_action: What action to take to get more articles. Can be:
                  * {"type": "click", "value": "a[href='...']", "kind": "descriptive_string"} - Click a link (use CSS selector or href URL)
                  * {"type": "scroll", "value": 3} - Scroll down N times (for infinite scroll)
                  * null - No pagination available (last page)
                - For click actions, provide a descriptive "kind" string (e.g., "next_page", "load_more", "show_more", "pagination_link", "infinite_scroll_button")
                  * "next_page": Links that navigate to a different URL/page
                  * "load_more" or "show_more": Buttons that load more content on the same page
                  * Use other descriptive strings as needed for the specific navigation pattern
                - Prefer href-based selectors: a[href="full-url"] when possible
                - Look for links with rel="next" attribute, aria-label containing "next", or buttons with "Load More"/"Show More" text
        
        OUTPUT FORMAT EXAMPLE:
        {
          "articles": [
            {
              "title": "Example Article",
              "url": "https://example.com/article",
              "publication_date": "2025-01-15",
              "date_confidence": "HIGH",
              "date_source": "datetime_attr"
            }
          ],
          "navigation_action": {"type": "click", "value": "a[href='https://example.com/news?page=2']", "kind": "next_page"},
          "extraction_issues": []
        }
        """

def _create_extraction_strategy() -> LLMExtractionStrategy:
    """Create LLM extraction strategy."""
    return LLMExtractionStrategy(
        llm_config=LLMConfig(
            provider="openai/gpt-4o-mini",
            api_token=os.getenv("OPENAI_API_KEY"),
        ),
        input_format="markdown",  # Changed from cleaned_html - markdown allows chunking to work!
        instruction=_get_extraction_instruction(),
        schema=ArticleExtraction.model_json_schema(),
        extraction_type="schema",
        extra_args={"temperature": 0.0, "max_tokens": 16000},  # Increase output limit for many articles
        apply_chunking=True,
        chunk_token_threshold=4000,  # Explicit chunk size
        overlap_rate=0.1,  # 10% overlap between chunks
        verbose=True  # Enable verbose to see chunking behavior
    )

def _get_delay_for_action(action: Optional[Dict]) -> float:
    """Get delay after JS execution completes, before HTML extraction."""
    if not action:
        return 2.0
    if action["type"] == "scroll":
        return 5.0  # Increased for infinite scroll to ensure content fully loads
    if action["type"] == "click":
        return 3.0
    return 2.0

def _parse_extraction_result(result: CrawlResult) -> tuple[ArticleExtraction, Optional[str], Optional[str]]:
    """Parse and validate extraction result."""
    article_data, error_msg, failed_output = None, None, None
    try:
        if result.extracted_content:
            parsed = json.loads(result.extracted_content)
            article_data = ArticleExtraction.model_validate(parsed[0])
    except Exception as e:
        error_msg = str(e)
        failed_output = str(result.extracted_content)[:2000] if result.extracted_content else None
    return article_data, error_msg, failed_output

def _extract_navigation_options(article_data: ArticleExtraction) -> List[NavigationOption]:
    """Extract navigation options from parsed article data."""
    if not article_data.navigation_action:
        return []
    
    nav_action = article_data.navigation_action
    if isinstance(nav_action, ClickAction):
        return [NavigationOption(
            kind=nav_action.kind,
            description=f"Navigation: {nav_action.value[:100]}",
            action=nav_action
        )]
    
    if isinstance(nav_action, ScrollAction):
        return [NavigationOption(
            kind="scroll",
            description=f"Infinite scroll: {nav_action.value} scrolls",
            action=nav_action
        )]
    
    return []

async def observe_page_comprehensive(
    url: str,
    crawler: AsyncWebCrawler,
    action: Optional[Dict] = None,
    is_same_page: bool = False,
    processed_markdown_length: Optional[int] = None
) -> PageObservation:
    """Single comprehensive observation function combining article extraction and navigation detection.
    
    Args:
        url: Target URL
        crawler: Browser instance
        action: Navigation action to perform (scroll, click, or None)
        is_same_page: If True, reuses existing page without navigation (for infinite scroll)
    """
    js_code, virtual_scroll_config = _prepare_action(action)
    
    # For infinite scroll: use js_only=True to avoid reloading the page
    js_only = is_same_page and action and action.get('type') == 'scroll'
    
    config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        simulate_user=True,
        verbose=False,
        page_timeout=30000,
        remove_overlay_elements=True,
        word_count_threshold=100,
        markdown_generator=DefaultMarkdownGenerator(),
        extraction_strategy=_create_extraction_strategy(),
        virtual_scroll_config=virtual_scroll_config,
        js_code=js_code,
        js_only=js_only,
        session_id="scraping_session",
        delay_before_return_html=_get_delay_for_action(action),
        excluded_tags=['script', 'style']
    )
    
    result = await _run_crawler(url, config, crawler=crawler)
    
    # Extract HTML statistics
    html_stats = None
    if result.success:
        html_stats = {
            'cleaned_html_length': len(result.cleaned_html) if result.cleaned_html else 0,
            'markdown_length': len(result.markdown) if result.markdown else 0,
            'screenshot_taken': result.screenshot is not None,
            'media_count': len(result.media) if result.media else 0
        }
        
        # Track incremental processing info for debugging
        if processed_markdown_length is not None and is_same_page and result.markdown:
            new_markdown_length = len(result.markdown) - processed_markdown_length
            html_stats['markdown_new_length'] = max(0, new_markdown_length)
            html_stats['markdown_previous_length'] = processed_markdown_length
            html_stats['is_incremental_scroll'] = new_markdown_length > 0
            # Note: Currently we still process full markdown due to crawl4ai internals,
            # but chunking helps with efficiency. True incremental extraction would require
            # modifying crawl4ai's extraction process.
    
    if not result.success:
        return PageObservation(url=url, articles=[], navigation_options=[], html_stats=html_stats)
    
    article_data, error_msg, failed_output = _parse_extraction_result(result)
    
    if error_msg:
        return PageObservation(
            url=result.url,
            articles=[],
            navigation_options=[],
            extraction_error=error_msg,
            failed_output=failed_output,
            html_stats=html_stats
        )
    
    navigation_options = _extract_navigation_options(article_data)
    
    return PageObservation(
        url=result.url,
        articles=article_data.articles,
        navigation_options=navigation_options,
        html_stats=html_stats
    )
