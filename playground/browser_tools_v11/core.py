"""Core scraping functions for V11 - Split into Navigation and Harvesting."""
import asyncio
import sys
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from selectolax.parser import HTMLParser
from urllib.parse import urljoin

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

BROWSER_CONFIG = BrowserConfig(
    headless=True,
    verbose=False,
    extra_args=["--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage"]
)

# Global for session persistence across tool calls
ACTIVE_CRAWLER: Optional[AsyncWebCrawler] = None

@dataclass
class NavMapResult:
    success: bool
    url: str
    navigation_html: str = ""
    error: str = ""

@dataclass
class HarvestResult:
    success: bool
    url: str
    links: List[Dict[str, str]] = field(default_factory=list)
    error: str = ""

async def _run_crawler(url: str, config: CrawlerRunConfig, crawler: Optional[AsyncWebCrawler] = None):
    """Internal helper to execute crawler with session persistence."""
    instance = crawler or ACTIVE_CRAWLER
    if instance:
        return await instance.arun(url, config=config, session_id="scraping_session")
    async with AsyncWebCrawler(config=BROWSER_CONFIG) as temp:
        return await temp.arun(url, config=config)

async def get_navigation_map(url: str, crawler: Optional[AsyncWebCrawler] = None) -> NavMapResult:
    """Fetch prioritized navigation elements."""
    config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        simulate_user=True,
        verbose=False,
        excluded_tags=['script', 'style', 'img', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']
    )
    
    result = await _run_crawler(url, config, crawler)
    if not result.success:
        return NavMapResult(False, url, error=result.error_message)
    
    tree = HTMLParser(result.cleaned_html or result.html)
    snippets, seen = [], set()
    
    # Priority selectors for navigation/pagination
    selectors = [".pagination", ".pager", "nav", "footer", "[class*='pagination']", "[class*='pager']", "[class*='nav']"]
    tags = tree.css(", ".join(selectors)) + tree.css("button, a, [role='button']")
    
    for tag in tags:
        # If it's a container from selectors, find its interactive children
        if tag.tag not in ('a', 'button'):
            items = tag.css("a, button, [role='button']")
        else:
            items = [tag]
            
        for item in items:
            text = item.text(strip=True)
            href = item.attributes.get('href', '')
            ident = f"{item.tag}:{text}:{href}"
            
            if ident not in seen and 0 < len(text) < 50:
                attrs = {k: v for k, v in item.attributes.items() if k in ['class', 'id', 'href', 'aria-label', 'title']}
                attr_str = " ".join(f'{k}="{v}"' for k, v in attrs.items())
                snippets.append(f"<{item.tag} {attr_str}>{text}</{item.tag}>")
                seen.add(ident)
                if len(snippets) >= 60: break
        if len(snippets) >= 60: break
        
    return NavMapResult(True, result.url, "\n".join(snippets))

async def harvest_content(url: str, action: Optional[Dict] = None, crawler: Optional[AsyncWebCrawler] = None) -> HarvestResult:
    """Perform action and extract links with context."""
    js_code, delay = [], 2.0
    
    if action:
        if action["type"] == "scroll":
            js_code.append(f"for(let i=0;i<{action.get('value',3)};i++){{window.scrollTo(0,document.body.scrollHeight);await new Promise(r=>setTimeout(r,1000));}}")
            delay = 3.0
        elif action["type"] == "click":
            js_code.append(f"const el=document.querySelector('{action.get('value')}');if(el){{el.scrollIntoView({{behavior:'smooth',block:'center'}});await new Promise(r=>setTimeout(r,500));el.click();await new Promise(r=>setTimeout(r,1500));}}")
            delay = 2.5
    
    # Wait for content to load
    if not js_code:
        js_code.append("await new Promise(r=>setTimeout(r,2000));")

    config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS, simulate_user=True,
        verbose=False,
        js_code=js_code, delay_before_return_html=delay,
        excluded_tags=['script', 'style']
    )
    
    result = await _run_crawler(url, config, crawler)
    if not result.success:
        return HarvestResult(False, url, error=result.error_message)
    
    tree = HTMLParser(result.cleaned_html or result.html)
    # Only remove navigation UI elements, not semantic nav containers that might have content
    [n.decompose() for n in tree.css("header, footer, script, style")]
    
    content_links, seen = [], set()
    for link in tree.css("a[href]"):
        href = link.attributes.get('href', '')
        full_url = urljoin(result.url, href)
        if not href or href.startswith(('#', 'javascript:')) or full_url in seen:
            continue
            
        seen.add(full_url)
        # Find nearest card/list container context
        container = link
        for _ in range(3):
            if container.parent and container.parent.tag in ['li', 'div', 'article', 'section']:
                container = container.parent
            else: break
            
        content_links.append({
            "url": full_url,
            "text": link.text(strip=True),
            "context": container.text(strip=True)[:300]
        })
        
    return HarvestResult(True, result.url, content_links)
