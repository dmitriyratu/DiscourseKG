"""Date voting utilities for weighted consensus-based date selection."""

from collections import defaultdict
from datetime import date

import pandas as pd

from src.discover.agent.models import Article, DateCandidate, DateSource, DateVoteResult


class DateVoter:
    """Votes on date candidates using weighted consensus."""
    THRESHOLD = 2

    @staticmethod
    def inlier_articles(articles: list[Article]) -> tuple[list[Article], list[Article]]:
        """Keep articles whose publication_date is within [p05 - 5d, min(p95 + 5d, today)]. Returns (inliers, dropped)."""
        if not articles:
            return [], []
        df = pd.DataFrame([
            {"article": a, "date": pd.to_datetime(a.publication_date, errors="coerce")}
            for a in articles
        ])
        valid = df["date"].notna()
        dates = df.loc[valid, "date"]
        if dates.empty:
            return list(articles), []
        low, high = dates.quantile([0.05, 0.95])
        low -= pd.Timedelta(days=5)
        high = min(high + pd.Timedelta(days=5), pd.Timestamp(date.today()))
        is_inlier = ~valid | df["date"].between(low, high)
        return df.loc[is_inlier, "article"].tolist(), df.loc[~is_inlier, "article"].tolist()

    @staticmethod
    def vote(candidates: list[DateCandidate]) -> DateVoteResult:
        """Vote on date candidates and return the winning date."""
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
            base_score = sum(DateSource.weight_for(c.source.value) for c in group)
            total_score = base_score + len(group) - 1
            
            # Find highest-weighted source for this date (for date_source return value)
            highest_source = max(group, key=lambda c: DateSource.weight_for(c.source.value))
            
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
