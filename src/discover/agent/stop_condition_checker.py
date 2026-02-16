"""Stop condition logic for discovery loop."""

from datetime import date, datetime
from typing import List, Optional

from src.discover.agent.models import ActionType, Article, NavigationAction
from src.discover.agent.date_voter import DateVoter


class StopConditionChecker:
    """Checks all stop conditions for the discovery loop."""

    ZERO_BATCH_THRESHOLD = 2

    def __init__(self, seen_urls: set[str], visited_actions: set[str]) -> None:
        self.seen_urls = seen_urls
        self.visited_actions = visited_actions

    def _action_key(self, url: str, action: NavigationAction) -> str:
        return f"{url}:{action.type}:{action.value}"

    def mark_action_visited(self, url: str, action: NavigationAction) -> None:
        """Mark a click action as visited."""
        if action.type == ActionType.CLICK:
            self.visited_actions.add(self._action_key(url, action))

    def check_action_visited(self, url: str, action: NavigationAction) -> Optional[str]:
        """Return 'action_already_visited' if click action was already tried, else None."""
        if action.type != ActionType.CLICK:
            return None
        if self._action_key(url, action) in self.visited_actions:
            return "action_already_visited"
        return None

    def check_batch(self, articles: List[Article], stop_dt: date, new_batch_urls: set[str]) -> Optional[str]:
        """Return stop reason if batch triggers date_threshold or duplicate_content, else None.
        
        new_batch_urls must be computed BEFORE _filter_articles updates seen_urls.
        """
        reliable_dates = []
        for a in articles:
            if a.date_score is None or a.date_score < DateVoter.THRESHOLD or not a.publication_date:
                continue
            try:
                reliable_dates.append(datetime.strptime(a.publication_date, "%Y-%m-%d").date())
            except ValueError:
                continue
        if reliable_dates and min(reliable_dates) < stop_dt:
            return "date_threshold"
        if articles and not new_batch_urls:
            return "duplicate_content"
        return None

    def check_exhausted(self, consecutive_zero: int) -> Optional[str]:
        """Return 'exhausted_content' if no new articles for too many batches, else None."""
        if consecutive_zero >= self.ZERO_BATCH_THRESHOLD:
            return "exhausted_content"
        return None

    def check_href_failed(self, href: Optional[str], action: NavigationAction) -> Optional[str]:
        """Return 'href_parse_failed' if click action has no parseable href, else None."""
        if action.type == ActionType.CLICK and href is None:
            return "href_parse_failed"
        return None

    @staticmethod
    def reason_max_pages() -> str:
        """Reason when loop completes all iterations."""
        return "max_pages"
