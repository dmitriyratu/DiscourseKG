"""Autonomous discovery agent with navigation loop."""

import asyncio
import sys
from datetime import date, datetime, timedelta
from typing import List, Optional

from crawl4ai import AsyncWebCrawler, BrowserConfig

from src.discover.agent.models import Article, NavigationAction, PageExtraction
from src.discover.agent.page_discoverer import PageDiscoverer
from src.discover.agent.discovery_logger import DiscoveryLogger
from src.discover.agent.date_voter import DateVoter

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())




async def _prepare_page(page, context, **kwargs):
    """Switch to main tab, close extras, remove overlays before any action."""
    overlay_selector = (
        '[role="dialog"], .modal, .popup, .overlay, #overlay, [data-dialog], .lightbox, .cookie-banner'
    )
    pages = context.pages
    if len(pages) > 1:
        main = pages[0]
        if page != main:
            await main.bring_to_front()
            page = main
        for p in pages[1:]:
            await p.close()
    await page.evaluate(
        f"document.querySelectorAll('{overlay_selector}').forEach(el => el.remove())"
    )
    return page


class DiscoveryAgent:
    """Autonomous agent that navigates pages to collect articles within a date range."""
    MAX_PAGES = 5
    ZERO_BATCH_THRESHOLD = 2

    def __init__(self, headless: bool = False, logger: Optional[DiscoveryLogger] = None) -> None:
        self.headless = headless
        self.logger = logger or DiscoveryLogger()
        self.collected: List[Article] = []
        self.all_articles: List[Article] = []
        self.seen_urls: set[str] = set()
        self.visited_actions: set[str] = set()
        self.duplicates_skipped: int = 0

    async def run(self, url: str, start_date: str, end_date: str) -> List[Article]:
        """Main discovery loop: observe -> filter -> navigate -> repeat."""
        start_dt = self._parse_date(start_date)
        end_dt = self._parse_date(end_date)
        stop_dt = start_dt - timedelta(days=1)
        
        browser_config = BrowserConfig(
            headless=self.headless,
            extra_args=["--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage"]
        )
        
        pages_processed = 0
        current_url = url
        next_action: Optional[NavigationAction] = NavigationAction(type="scroll")
        consecutive_zero = 0

        async with AsyncWebCrawler(config=browser_config) as crawler:
            crawler.crawler_strategy.set_hook("on_execution_started", _prepare_page)
            page_discoverer = PageDiscoverer(crawler)

            for page_num in range(self.MAX_PAGES):
                if self._already_visited(current_url, next_action):
                    self._stop("action_already_visited", pages_processed, start_dt, end_dt)
                    break

                reuse = page_num > 0
                self.logger.page_start(current_url, page_num, next_action)

                extraction, markdown_len, llm_info = await self.logger.observe_with_logging(
                    page_discoverer, current_url, next_action, reuse_session=reuse,
                )

                if next_action and next_action.type == "click":
                    self._mark_visited(current_url, next_action)
                pages_processed += 1
                batch_articles, dropped = DateVoter.inlier_articles(extraction.articles)
                self.all_articles.extend(batch_articles)
                if stop := self._check_stop(batch_articles, stop_dt):
                    self._stop(stop, pages_processed, start_dt, end_dt)
                    break
                valid = self._filter_articles(batch_articles, start_dt, end_dt)
                self.collected.extend(valid)
                self.logger.extraction_result(batch_articles, valid, extraction.next_action, start_dt, end_dt, extraction.extraction_issues, dropped=dropped, llm_info=llm_info)
                llm_next_action = extraction.next_action
                if not llm_next_action:
                    new_urls = {a.url for a in batch_articles} - self.seen_urls
                    if new_urls:
                        consecutive_zero = 0
                    else:
                        consecutive_zero += 1
                        if consecutive_zero >= self.ZERO_BATCH_THRESHOLD:
                            self._stop("exhausted_content", pages_processed, start_dt, end_dt)
                            break
                    next_action = NavigationAction(type="scroll")
                    continue
                next_action = llm_next_action
                if next_action.type == "click" and isinstance(next_action.value, str):
                    if href := self._href_from_selector(next_action.value):
                        current_url = href
                        consecutive_zero = 0
            else:
                self._stop("max_pages", pages_processed, start_dt, end_dt)
        
        return self.collected, self.all_articles
    
    def _parse_date(self, date_str: str) -> date:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    
    def _action_key(self, url: str, action: NavigationAction) -> str:
        return f"{url}:{action.type}:{action.value}"
    
    def _already_visited(self, url: str, action: NavigationAction) -> bool:
        return self._action_key(url, action) in self.visited_actions
    
    def _mark_visited(self, url: str, action: NavigationAction) -> None:
        if action.type == "click":
            self.visited_actions.add(self._action_key(url, action))

    def _stop(self, reason: str, pages_processed: int, start_dt: date, end_dt: date) -> None:
        self.logger.stopping(reason, len(self.collected), pages_processed, start_dt, end_dt, self.all_articles)

    def _href_from_selector(self, selector: str) -> Optional[str]:
        if not selector.startswith("a[href='") or "']" not in selector:
            return None
        try:
            return selector.split("href='")[1].split("']")[0]
        except IndexError:
            return None

    def _filter_articles(self, articles: List[Article], start_dt: date, end_dt: date) -> List[Article]:
        """Filter articles by date range and deduplicate."""
        valid = []
        for article in articles:
            if article.url in self.seen_urls:
                self.duplicates_skipped += 1
                continue
            if article.date_score is None or article.date_score < DateVoter.THRESHOLD:
                continue
            if not article.publication_date:
                continue
            try:
                article_date = self._parse_date(article.publication_date)
            except ValueError:
                continue
            if not (start_dt <= article_date <= end_dt):
                continue
            valid.append(article)
            self.seen_urls.add(article.url)
        return valid
    
    def _check_stop(self, articles: List[Article], stop_dt: date) -> Optional[str]:
        """Check if discovery should stop. Returns reason or None."""
        # Date threshold: oldest reliable article is before stop date
        reliable_dates = []
        for a in articles:
            if a.date_score is None or a.date_score < DateVoter.THRESHOLD or not a.publication_date:
                continue
            try:
                reliable_dates.append(self._parse_date(a.publication_date))
            except ValueError:
                continue
        
        if reliable_dates and min(reliable_dates) < stop_dt:
            return "date_threshold"
        
        # All articles already seen (duplicate content)
        current_urls = {a.url for a in articles}
        if current_urls and not (current_urls - self.seen_urls):
            return "duplicate_content"
        
        return None
