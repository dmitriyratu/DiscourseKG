"""Autonomous discovery agent with navigation loop."""

import asyncio
import sys
from datetime import date, datetime, timedelta
from typing import List, Optional, Set

from crawl4ai import AsyncWebCrawler, BrowserConfig

from src.discover.agent.adblock_engine import setup_blocking
from src.discover.agent.models import ActionType, Article, NavigationAction, PageExtraction
from src.discover.agent.stop_condition_checker import StopConditionChecker
from src.discover.agent.page_discoverer import PageDiscoverer
from src.discover.agent.discovery_logger import DiscoveryLogger
from src.discover.agent.date_voter import DateVoter
from src.discover.config import DiscoveryConfig, discovery_config

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())




async def _block_popups(page, context, **kwargs):
    """Close new tabs, strip target="_blank", and block ads via EasyList."""
    context.on("page", lambda p: asyncio.create_task(p.close()))
    await context.add_init_script(
        "document.addEventListener('DOMContentLoaded',()=>"
        "document.querySelectorAll('a[target=\"_blank\"]').forEach(a=>a.removeAttribute('target')),"
        "{once:true});"
    )
    await setup_blocking(context)
    return page


class DiscoveryAgent:
    """Autonomous agent that navigates pages to collect articles within a date range."""

    def __init__(self, config: DiscoveryConfig = discovery_config, logger: Optional[DiscoveryLogger] = None) -> None:
        self.config = config
        self.logger = logger or DiscoveryLogger()
        self.seen_urls: set[str] = set()
        self.visited_actions: set[str] = set()
        self.stop_checker = StopConditionChecker(self.seen_urls, self.visited_actions)
        self.collected: List[Article] = []
        self.all_articles: List[Article] = []
        self.duplicates_skipped: int = 0

    async def run(self, url: str, start_date: str, end_date: str, existing_urls: Optional[Set[str]] = None) -> tuple[List[Article], List[Article]]:
        """Main discovery loop: observe -> filter -> navigate -> repeat."""
        existing_urls = existing_urls or set()
        start_dt = self._parse_date(start_date)
        end_dt = self._parse_date(end_date)
        stop_dt = start_dt - timedelta(days=1)
        
        browser_config = BrowserConfig(
            headless=self.config.HEADLESS,
            extra_args=["--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage"]
        )
        
        pages_processed = 0
        current_url = url
        next_action: NavigationAction = NavigationAction(type=ActionType.SCROLL)
        consecutive_zero = 0

        async with AsyncWebCrawler(config=browser_config) as crawler:
            crawler.crawler_strategy.set_hook("on_page_context_created", _block_popups)
            page_discoverer = PageDiscoverer(crawler, self.config)

            for page_num in range(self.config.MAX_PAGES):
                if stop := self.stop_checker.check_action_visited(current_url, next_action):
                    self._stop(stop, pages_processed, start_dt, end_dt)
                    break

                reuse = page_num > 0
                self.logger.page_start(current_url, page_num, next_action)

                extraction, llm_info = await page_discoverer.observe(
                    current_url, next_action, reuse_session=reuse
                )

                if next_action.type == ActionType.CLICK:
                    self.stop_checker.mark_action_visited(current_url, next_action)
                pages_processed += 1
                batch_articles, dropped = DateVoter.inlier_articles(extraction.articles)
                self.all_articles.extend(batch_articles)
                
                # Snapshot new URLs BEFORE _filter_articles mutates seen_urls
                new_batch_urls = {a.url for a in batch_articles} - self.seen_urls
                
                # Filter and collect valid articles (updates seen_urls)
                valid = self._filter_articles(batch_articles, start_dt, end_dt)
                self.collected.extend(valid)
                
                already_saved = sum(1 for a in valid if a.url in existing_urls)
                self.logger.extraction_result(batch_articles, valid, extraction.next_action, start_dt, end_dt, batch_num=page_num + 1, already_saved=already_saved, extraction_issues=extraction.extraction_issues, dropped=dropped, llm_info=llm_info)
                next_action = extraction.next_action
                
                # Check stop conditions AFTER processing current batch
                if stop := self.stop_checker.check_batch(batch_articles, stop_dt, new_batch_urls):
                    self._stop(stop, pages_processed, start_dt, end_dt)
                    break
                if new_batch_urls:
                    consecutive_zero = 0
                else:
                    consecutive_zero += 1
                    if stop := self.stop_checker.check_exhausted(consecutive_zero):
                        self._stop(stop, pages_processed, start_dt, end_dt)
                        break

                if next_action.type == ActionType.CLICK:
                    href = self._href_from_selector(next_action.value)
                    if href:
                        current_url = href
                        consecutive_zero = 0
                    elif stop := self.stop_checker.check_href_failed(href, next_action):
                        self._stop(stop, pages_processed, start_dt, end_dt)
                        break
            else:
                self._stop(StopConditionChecker.reason_max_pages(), pages_processed, start_dt, end_dt)
        
        return self.collected, self.all_articles
    
    def _parse_date(self, date_str: str) -> date:
        return datetime.strptime(date_str, "%Y-%m-%d").date()

    def _stop(self, reason: str, pages_processed: int, start_dt: date, end_dt: date) -> None:
        self.logger.stopping(reason)

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
