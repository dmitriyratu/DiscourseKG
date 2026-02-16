"""Compact rich console logging for discovery agent visibility."""

from datetime import date, datetime
from typing import Dict, List, Optional, Union

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from src.discover.agent.models import Article, NavigationAction
from src.shared.pipeline_state import PipelineStateManager

console = Console()


def get_existing_source_urls(speaker: Optional[str] = None) -> set[str]:
    """Return set of source URLs already in pipeline (for display)."""
    states = PipelineStateManager().get_all_states()
    urls = set()
    for s in states:
        if speaker and s.get("speaker") != speaker:
            continue
        if url := s.get("source_url"):
            urls.add(url)
    return urls


class DiscoveryLogger:
    """Lightweight logger for discovery agent thinking visibility."""

    def page_start(self, url: str, page_num: int, action: NavigationAction) -> None:
        """Log page processing start."""
        action_str = self._format_action(action)
        console.print(Panel(
            f"[bold]Step {page_num + 1}[/bold] | {url[:80]}...\n[cyan]{action_str}[/cyan]",
            border_style="blue"
        ))
    
    def extraction_result(self, articles: List[Article], valid: List[Article],
                          next_action: NavigationAction, start_dt: date, end_dt: date,
                          batch_num: int = 1, already_saved: int = 0,
                          extraction_issues: Optional[List[str]] = None,
                          dropped: Optional[List[Article]] = None,
                          llm_info: Optional[Dict[str, Union[int, float]]] = None) -> None:
        """Log extraction results with article summary."""
        page_date_range = self._get_date_range(articles)

        summary = Text()
        summary.append(f"Discovered Range ", style="white")
        if page_date_range:
            summary.append(f"[{page_date_range['min']} - {page_date_range['max']}]: ", style="white")
        else:
            summary.append(": ", style="white")
        summary.append(f"{len(articles)}", style="white")
        summary.append(" articles", style="white")

        summary.append(f"\nTarget Range [{start_dt} - {end_dt}]: ", style="white")
        summary.append(f"{len(valid)}", style="green bold")
        summary.append(" articles", style="white")
        if already_saved:
            summary.append(f" ({already_saved} already saved)", style="dim")

        if dropped:
            summary.append(f"\nDropped ", style="yellow")
            summary.append(f"{len(dropped)}", style="yellow bold")
            summary.append(" date outlier(s)", style="yellow")

        summary.append(f"\nNext: ", style="white")
        summary.append(self._format_action(next_action), style="cyan")

        if extraction_issues:
            summary.append(f"\nIssues: {', '.join(extraction_issues)}", style="red")

        if llm_info:
            summary.append(f"\nLLM: {llm_info['input_tokens']:,} in + {llm_info['output_tokens']:,} out = {llm_info['total_tokens']:,} tokens | time: {llm_info['llm_time']:.2f}s", style="dim")

        console.print(Panel(summary, title=f"Results Batch-{batch_num}", title_align="left", border_style="white"))

        if dropped:
            drop_table = Table(show_header=True, header_style="bold yellow", border_style="yellow")
            drop_table.add_column("Dropped Articles", width=50)
            drop_table.add_column("Date", width=12)
            for a in dropped[:5]:
                drop_table.add_row(a.title[:50], a.publication_date or "N/A")
            if len(dropped) > 5:
                drop_table.add_row("...", f"({len(dropped) - 5} more)")
            console.print(drop_table)

        if valid:
            table = Table(show_header=True, header_style="bold", border_style="dim")
            table.add_column("#", width=3)
            table.add_column("Title", width=45)
            table.add_column("Date", width=12)
            table.add_column("Score", width=6)
            
            for i, a in enumerate(valid[:5], 1):
                if a.date_score is None:
                    score_text = Text("N/A", style="red")
                else:
                    score_style = "red" if a.date_score <= 1 else "yellow" if a.date_score <= 5 else "green"
                    score_text = Text(str(a.date_score), style=score_style)
                table.add_row(str(i), a.title[:45], a.publication_date or "N/A", score_text)
            
            if len(valid) > 5:
                table.add_row("...", f"({len(valid) - 5} more)", "", "")
            
            console.print(table)
    
    def stopping(self, reason: str) -> None:
        """Log stop condition."""
        summary = Text()
        summary.append("Stopping: ", style="red bold")
        summary.append(reason, style="white")
        console.print(Panel(summary, border_style="red"))
    
    def complete(self, valid_articles: List[Article], all_articles: List[Article], pages: int,
                  start_dt: date, end_dt: date, duplicates_skipped: int = 0) -> None:
        """Log final summary (per-URL agent run)."""
        all_date_range = self._get_date_range(all_articles)
        summary = Text()
        summary.append("Complete", style="green bold")

        if all_date_range:
            summary.append(f"\nDiscovered Range [{all_date_range['min']} - {all_date_range['max']}]: ", style="white")
            summary.append(f"{all_date_range['count']}", style="white")
            summary.append(" articles", style="white")
        else:
            summary.append("\nDiscovered Range: ", style="white")
            summary.append("0", style="white")
            summary.append(" articles", style="white")

        summary.append(f"\nTarget Range [{start_dt} - {end_dt}]: ", style="white")
        summary.append(f"{len(valid_articles)}", style="green bold")
        summary.append(" new articles", style="white")
        if duplicates_skipped:
            summary.append(f" ({duplicates_skipped} duplicates skipped)", style="dim")
        
        console.print(Panel(summary, border_style="green"))

    def aggregate_complete(
        self,
        discovered: List,
        total_found: int,
        total_all: int,
        duplicates_skipped: int,
        processing_time: float,
        start_date: str,
        end_date: str,
        date_range_min: Optional[str] = None,
        date_range_max: Optional[str] = None,
    ) -> None:
        """Log final discovery summary (aggregate across URLs)."""
        dates = [date_range_min, date_range_max] if date_range_min and date_range_max else []
        summary = Text()
        summary.append("Complete", style="green bold")
        if dates:
            summary.append(f"\nDiscovered Range [{min(dates)} - {max(dates)}]: ", style="white")
            summary.append(f"{total_all}", style="white")
        else:
            summary.append("\nDiscovered Range: ", style="white")
            summary.append(f"{total_all}", style="white")
        summary.append(" articles", style="white")
        summary.append(f"\nTarget Range [{start_date} - {end_date}]: ", style="white")
        new_count = total_found - duplicates_skipped
        summary.append(f"{new_count}", style="green bold")
        summary.append(" new", style="white")
        if duplicates_skipped:
            summary.append(f", {duplicates_skipped} already saved", style="dim")
        summary.append(f" ({processing_time}s)", style="dim")
        console.print(Panel(summary, border_style="green"))
    
    def _get_date_range(self, articles: List[Article]) -> Optional[Dict[str, Union[str, int]]]:
        """Get min-max date range from articles with valid dates."""
        dates = []
        for article in articles:
            if article.publication_date:
                try:
                    dates.append(datetime.strptime(article.publication_date, "%Y-%m-%d").date())
                except ValueError:
                    continue
        if not dates:
            return None
        return {
            "min": min(dates).isoformat(),
            "max": max(dates).isoformat(),
            "count": len(dates)
        }
    
    def _format_action(self, action: NavigationAction) -> str:
        if action.type == "scroll":
            return "Scroll to bottom"
        return f"Click: {str(action.value)[:60]}"
