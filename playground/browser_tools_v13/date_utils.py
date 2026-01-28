"""Date voting utilities for weighted consensus-based date selection."""
from collections import defaultdict
from playground.browser_tools_v13.models import DateCandidate, DateVoteResult


class DateVoter:
    """Votes on date candidates using weighted consensus."""
    
    SOURCE_WEIGHTS = {
        "datetime_attr": 7,
        "schema_org": 5,
        "url_path": 3,
        "near_title": 2,
        "metadata": 1
    }
    
    THRESHOLD = 5
    
    @staticmethod
    def vote(candidates: list[DateCandidate]) -> DateVoteResult:
        """
        Vote on date candidates and return the winning date.
        
        Args:
            candidates: List of date candidates from different sources
            
        Returns:
            DateVoteResult with publication_date, date_score, and date_source (all None if no valid date)
        """
        if not candidates:
            return DateVoteResult()
        
        # Group candidates by date value
        date_groups: dict[str, list[DateCandidate]] = defaultdict(list)
        for candidate in candidates:
            date_groups[candidate.date].append(candidate)
        
        # Calculate score for each date
        date_scores: dict[str, tuple[int, str]] = {}
        for date_str, group in date_groups.items():
            # Sum base weights + consensus bonus (number_of_sources - 1)
            base_score = sum(DateVoter.SOURCE_WEIGHTS.get(c.source, 0) for c in group)
            total_score = base_score + len(group) - 1
            
            # Find highest-weighted source for this date (for date_source return value)
            highest_source = max(group, key=lambda c: DateVoter.SOURCE_WEIGHTS.get(c.source, 0))
            
            date_scores[date_str] = (total_score, highest_source.source)
        
        # Select winner (highest score, must be >= threshold)
        winner_date, (winner_score, winner_source) = max(date_scores.items(), key=lambda x: x[1][0])
        
        if winner_score < DateVoter.THRESHOLD:
            return DateVoteResult()
        
        return DateVoteResult(
            publication_date=winner_date,
            date_score=winner_score,
            date_source=winner_source
        )
