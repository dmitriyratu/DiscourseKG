"""Orchestrator pattern for V12 - Direct function calls with external state management."""
from datetime import datetime, timedelta, date
from typing import Optional, Dict, List, Any, Callable, Tuple
import json
from crawl4ai import AsyncWebCrawler, BrowserConfig
from playground.browser_tools_v12 import core
from playground.browser_tools_v12.callbacks import CallbackManager


class ScrapingAgent:
    """Orchestrator that manages state externally and calls observation function directly."""

    MAX_PAGES = 10
    DAYS_BEFORE_START = 1
    SCROLL_COUNT = 3

    BROWSER_CONFIG = BrowserConfig(
        headless=False, 
        verbose=True,  
        extra_args=["--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage"]
    )

    def __init__(self):
        self.collected_articles = []
        self.seen_urls = set()
        self.all_page_urls = set()
        self.visited_urls_with_action = set()
        self.scroll_stalled_urls = set()
        self.start_dt = None
        self.end_dt = None
        self.stop_dt = None
        self._cb = CallbackManager()
        self.processed_markdown_length = {}  # Track processed markdown length per URL
    
    @staticmethod
    def _parse_date(date_str: str) -> Optional[date]:
        """Parse date string, return None if invalid."""
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def _action_key(url: str, action: Dict[str, Any]) -> str:
        """Create hashable key for url+action pair."""
        return f"{url}:{json.dumps(action, sort_keys=True)}"
    
    @staticmethod
    def _is_reliable_article(article: Dict[str, Any]) -> bool:
        """Check if article has reliable date confidence."""
        return article.get('date_confidence') in ['HIGH', 'MEDIUM']
    
    async def run(self, url: str, start_date: str, end_date: str, callbacks: Optional[List[Callable]] = None) -> Dict[str, Any]:
        """Main orchestration loop."""
        
        self._cb = CallbackManager(callbacks)
        
        self.start_dt = self._parse_date(start_date)
        self.end_dt = self._parse_date(end_date)

        if not self.start_dt or not self.end_dt:
            raise ValueError("Invalid date format. Use YYYY-MM-DD")
        if self.start_dt > self.end_dt:
            raise ValueError(f"start_date ({start_date}) must be <= end_date ({end_date})")
        
        self.stop_dt = self.start_dt - timedelta(days=self.DAYS_BEFORE_START)
        
        current_url = url
        pages_processed = 0
        stop_reason = None
        is_same_page = False
        
        async with AsyncWebCrawler(config=self.BROWSER_CONFIG) as crawler:
            next_action = None
            while pages_processed < self.MAX_PAGES:
                if self._should_skip_action(current_url, next_action):
                    self._cb.emit(
                        'action_skip', url=current_url, 
                        action=next_action, reason="already_visited"
                    )
                    stop_reason = "action_skip"
                    break
                
                self._cb.emit('page_start', 
                    url=current_url, 
                    page_num=pages_processed, 
                    action=next_action,
                    start_dt=self.start_dt,
                    end_dt=self.end_dt,
                    stop_dt=self.stop_dt
                )
                
                page_result, articles_before_count = await self._process_and_collect(
                    current_url, crawler, next_action, is_same_page=is_same_page
                )
                
                if page_result.get('extraction_error'):
                    stop_reason = "extraction_error"
                    break
                
                pages_processed += 1
                self._mark_action_visited(current_url, next_action, page_result.get('articles', []), articles_before_count)
                
                if stop := self._check_stop_conditions(page_result, pages_processed):
                    self._cb.emit('stop_condition', 
                        reason=stop, 
                        pages_processed=pages_processed, 
                        articles_collected=len(self.collected_articles),
                        current_page_articles=page_result.get('articles', []),
                        stop_dt=self.stop_dt
                    )
                    stop_reason = stop
                    break
                
                if not (next_action := self._get_next_action(page_result, current_url)):
                    self._cb.emit('navigation_decision', navigation_options=page_result.get('navigation', []), selected_action=None)
                    stop_reason = "no_navigation"
                    break
                
                self._cb.emit('navigation_decision', navigation_options=page_result.get('navigation', []), selected_action=next_action)
                
                # Track if we're staying on the same page (for infinite scroll)
                new_url = page_result.get('url', current_url)
                # Use a more flexible check: ignore trailing slashes and common search params if needed
                # For now, just check if the base search URL is the same
                base_current = current_url.split('#')[0].rstrip('/')
                base_new = new_url.split('#')[0].rstrip('/')
                is_same_page = (base_new == base_current) and next_action and next_action.get('type') == 'scroll'
                current_url = new_url
            
            if stop_reason is None and pages_processed >= self.MAX_PAGES:
                stop_reason = "max_pages"
                self._cb.emit('stop_condition', 
                    reason=stop_reason, 
                    pages_processed=pages_processed, 
                    articles_collected=len(self.collected_articles),
                    max_pages=self.MAX_PAGES
                )
        
        self._cb.emit('complete', 
            pages_processed=pages_processed, 
            articles_collected=len(self.collected_articles), 
            stop_reason=stop_reason,
            articles=self.collected_articles,
            start_dt=self.start_dt,
            end_dt=self.end_dt
        )
        
        return {
            "output": f"Found {len(self.collected_articles)} articles across {pages_processed} pages",
            "articles": self.collected_articles,
            "pages_processed": pages_processed,
            "stop_reason": stop_reason
        }
    
    async def _process_and_collect(
        self, url: str, crawler: AsyncWebCrawler, action: Optional[Dict[str, Any]] = None,
        is_same_page: bool = False
    ) -> Tuple[Dict[str, Any], int]:
        """Process page and collect valid articles. Returns (page_result, articles_before_count)."""
        
        articles_before_count = len(self.collected_articles)
        
        # Get processed markdown length for incremental processing
        processed_length = self.processed_markdown_length.get(url) if is_same_page else None
        
        observation = await core.observe_page_comprehensive(
            url, crawler=crawler, action=action, is_same_page=is_same_page,
            processed_markdown_length=processed_length
        )
        page_result = {
            'url': observation.url,
            'articles': [a.model_dump() for a in observation.articles],
            'navigation': [n.model_dump() for n in observation.navigation_options],
            'extraction_error': observation.extraction_error,
            'failed_output': observation.failed_output
        }
        
        all_articles = [a.model_dump() for a in observation.articles]
        
        self._cb.emit('page_complete',
            url=observation.url,
            articles=all_articles,
            navigation_options=[n.model_dump() for n in observation.navigation_options],
            extraction_error=observation.extraction_error,
            failed_output=observation.failed_output,
            html_stats=observation.html_stats,
            start_dt=self.start_dt,
            end_dt=self.end_dt
        )
        
        valid_articles, filter_stats = self._filter_articles_by_date(page_result.get('articles', []))
        self.collected_articles.extend(valid_articles)
        
        # Update processed markdown length for tracking
        if observation.html_stats and observation.html_stats.get('markdown_length'):
            # Always track the total markdown length we've seen
            self.processed_markdown_length[url] = observation.html_stats['markdown_length']
        
        self._cb.emit('articles_filtered',
            all_articles=all_articles,
            valid_articles=valid_articles,
            filter_stats=filter_stats,
            start_dt=self.start_dt,
            end_dt=self.end_dt,
            stop_dt=self.stop_dt,
            total_collected=len(self.collected_articles)
        )
        
        return page_result, articles_before_count
    
    def _get_next_action(self, page_result: Dict[str, Any], current_url: str) -> Optional[Dict[str, Any]]:
        """Extract next action from page result, with fallback to scrolling."""
        navigation_options = page_result.get('navigation', [])
        if navigation_options:
            return navigation_options[0].get('action')

        if current_url not in self.scroll_stalled_urls:
            return {"type": "scroll", "value": self.SCROLL_COUNT}
        
        return None
    
    def _filter_articles_by_date(self, articles: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Filter by date range and deduplicate by URL. Returns (valid_articles, stats)."""
        valid = []
        rejected = {
            'duplicate_url': [],
            'low_confidence': [],
            'no_date': [],
            'out_of_range': []
        }
        
        for article in articles:
            url = article.get('url')
            if not url:
                continue
            
            if url in self.seen_urls:
                rejected['duplicate_url'].append(article)
                continue
            
            if not self._is_reliable_article(article):
                rejected['low_confidence'].append(article)
                continue
            
            article_date = self._parse_date(article.get('publication_date'))
            if not article_date:
                rejected['no_date'].append(article)
                continue
            
            if not (self.start_dt <= article_date <= self.end_dt):
                rejected['out_of_range'].append(article)
                continue
            
            valid.append(article)
            self.seen_urls.add(url)
        
        stats = {
            'total': len(articles),
            'valid': len(valid),
            'rejected': rejected,
            'rejected_counts': {k: len(v) for k, v in rejected.items()}
        }
        
        return valid, stats
    
    def _check_stop_conditions(self, page_result: Dict[str, Any], pages_processed: int) -> Optional[str]:
        """Check if scraping should stop. Returns stop reason or None."""
        articles = page_result.get('articles', [])
        
        reliable_dates = [
            d for a in articles if self._is_reliable_article(a)
            if (d := self._parse_date(a.get('publication_date')))
        ]
        
        if reliable_dates and min(reliable_dates) < self.stop_dt:
            return "date_threshold"
        
        if pages_processed > 0:
            current_urls = {a.get('url') for a in articles if a.get('url')}
            if current_urls and not (current_urls - self.seen_urls):
                return "duplicate_content"
        
        return None
    
    def _should_skip_action(self, url: str, action: Optional[Dict[str, Any]]) -> bool:
        """Check if action should be skipped (already visited or scroll stalled)."""
        if not action:
            return False
        
        if action.get('type') == 'scroll':
            return url in self.scroll_stalled_urls
        
        return self._action_key(url, action) in self.visited_urls_with_action
    
    def _mark_action_visited(self, url: str, action: Optional[Dict[str, Any]], current_articles: List[Dict[str, Any]], articles_before_count: int) -> None:
        """Mark action as visited. For scrolls, check if ANY new articles appeared (not just valid ones)."""
        if not action:
            return
        
        current_urls = {a.get('url') for a in current_articles if a.get('url')}
        
        if action.get('type') == 'scroll':
            new_articles_appeared = bool(current_urls - self.all_page_urls)

            self.all_page_urls.update(current_urls)
            
            if not new_articles_appeared:
                self.scroll_stalled_urls.add(url)
        else:
            self.visited_urls_with_action.add(self._action_key(url, action))
