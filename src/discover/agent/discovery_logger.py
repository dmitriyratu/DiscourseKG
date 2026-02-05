"""Compact rich console logging for discovery agent visibility."""

from datetime import date, datetime

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table

from src.discover.agent.models import Article, NavigationAction, PageExtraction
from src.discover.agent.page_discoverer import PageDiscoverer

console = Console()


class DiscoveryLogger:
    """Lightweight logger for discovery agent thinking visibility."""
    
    def __init__(self):
        self.seen_urls: set[str] = set()
    
    def page_start(self, url: str, page_num: int, action: NavigationAction | None) -> None:
        """Log page processing start."""
        action_str = self._format_action(action)
        console.print(Panel(
            f"[bold]Step {page_num + 1}[/bold] | {url[:80]}...\n[cyan]{action_str}[/cyan]",
            border_style="blue"
        ))
    
    async def observe_with_logging(
        self,
        page_discoverer: PageDiscoverer,
        url: str,
        action: NavigationAction | None = None,
        reuse_session: bool = False,
    ) -> tuple[PageExtraction, int, dict[str, int | float] | None]:
        """Wrapper around PageDiscoverer.observe() that captures token usage."""
        llm_info: dict[str, int | float] | None = None
        
        def log_result(result, extraction_strategy, llm_time: float):
            nonlocal llm_info
            total_usage = getattr(extraction_strategy, "total_usage", None)
            if total_usage:
                input_tokens = getattr(total_usage, "prompt_tokens", 0)
                output_tokens = getattr(total_usage, "completion_tokens", 0)
                total = getattr(total_usage, "total_tokens", input_tokens + output_tokens)
                llm_info = {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": total,
                    "llm_time": llm_time
                }

        extraction, markdown_len = await page_discoverer.observe(url, action, reuse_session, result_callback=log_result)
        return extraction, markdown_len, llm_info
    
    def extraction_result(self, articles: list[Article], valid: list[Article],
                          next_action: NavigationAction | None, start_dt: date, end_dt: date,
                          extraction_issues: list[str] | None = None,
                          dropped: list[Article] | None = None,
                          llm_info: dict[str, int | float] | None = None) -> None:
        """Log extraction results with article summary."""
        new_articles = [a for a in articles if a.url not in self.seen_urls]
        self.seen_urls.update(a.url for a in articles)

        page_date_range = self._get_date_range(articles)

        summary = Text()
        summary.append(f"Discovered Range ", style="white")
        if page_date_range:
            summary.append(f"[{page_date_range['min']} - {page_date_range['max']}]: ", style="white")
        else:
            summary.append(": ", style="white")
        summary.append(f"{len(articles)}", style="white")
        summary.append(" articles", style="white")
        if len(new_articles) != len(articles):
            summary.append(f" ({len(new_articles)} new)", style="dim")

        summary.append(f"\nTarget Range [{start_dt} - {end_dt}]: ", style="white")
        summary.append(f"{len(valid)}", style="green bold")
        summary.append(" articles", style="white")

        if dropped:
            summary.append(f"\nDropped ", style="yellow")
            summary.append(f"{len(dropped)}", style="yellow bold")
            summary.append(" date outlier(s)", style="yellow")

        if next_action:
            summary.append(f"\nNext: ", style="white")
            summary.append(self._format_action(next_action), style="cyan")

        if extraction_issues:
            summary.append(f"\nIssues: {', '.join(extraction_issues)}", style="red")

        if llm_info:
            summary.append(f"\nLLM: {llm_info['input_tokens']:,} in + {llm_info['output_tokens']:,} out = {llm_info['total_tokens']:,} tokens | time: {llm_info['llm_time']:.2f}s", style="dim")

        console.print(Panel(summary, title="Results", title_align="left", border_style="white"))

        if dropped:
            drop_table = Table(show_header=True, header_style="bold yellow", border_style="yellow", title="Dropped Articles", title_justify="left")
            drop_table.add_column("Title", width=50)
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
    
    def stopping(self, reason: str, total_collected: int, pages_processed: int) -> None:
        """Log stop condition."""
        console.print(Panel(
            f"[red bold]Stopping:[/red bold] {reason}\n"
            f"[white]Pages: {pages_processed} | Articles: [cyan bold]{total_collected}[/cyan bold][/white]",
            border_style="red"
        ))
    
    def complete(self, valid_articles: list[Article], all_articles: list[Article], pages: int, 
                  start_dt: date, end_dt: date) -> None:
        """Log final summary."""
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
        summary.append(" articles", style="white")
        
        console.print(Panel(summary, border_style="green"))
    
    def _get_date_range(self, articles: list[Article]) -> dict[str, str | int] | None:
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
    
    def _format_action(self, action: NavigationAction | None) -> str:
        if not action:
            return "None"
        if action.type == "scroll":
            return "Scroll to bottom"
        return f"Click: {str(action.value)[:60]}"
