"""Compact rich console logging for agent visibility."""
from datetime import date, datetime
from typing import TYPE_CHECKING
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from playground.browser_tools_v13.models import Article, NavigationAction, PageExtraction

if TYPE_CHECKING:
    from playground.browser_tools_v13.crawler import PageCrawler

console = Console()


class AgentLogger:
    """Lightweight logger for agent thinking visibility."""
    
    def __init__(self):
        self.seen_urls: set[str] = set()
    
    def page_start(self, url: str, page_num: int, action: NavigationAction | None) -> None:
        """Log page processing start."""
        action_str = self._format_action(action)
        console.print(Panel(
            f"[bold]Page {page_num + 1}[/bold] | {url[:80]}...\n[cyan]{action_str}[/cyan]",
            border_style="blue"
        ))
    
    def _log_llm_context(self, content_size: int, estimated_tokens: int | None = None) -> None:
        """Log LLM context size being sent."""
        size_str = f"{content_size:,} chars"
        if estimated_tokens:
            size_str += f" (~{estimated_tokens:,} tokens)"
        console.print(f"[dim]LLM context: {size_str}[/dim]")
    
    async def observe_with_logging(
        self,
        page_crawler: "PageCrawler",
        url: str,
        action: NavigationAction | None = None,
        reuse_session: bool = False,
        last_markdown_length: int = 0,
    ) -> tuple[PageExtraction, int]:
        """Wrapper around PageCrawler.observe() that logs token usage. Returns (extraction, markdown_len)."""
        def log_result(result, extraction_strategy):
            total_usage = getattr(extraction_strategy, "total_usage", None)
            if total_usage:
                input_tokens = getattr(total_usage, "prompt_tokens", 0)
                output_tokens = getattr(total_usage, "completion_tokens", 0)
                total = getattr(total_usage, "total_tokens", input_tokens + output_tokens)
                if total > 0:
                    console.print(f"[dim]LLM context: {input_tokens:,} in + {output_tokens:,} out = {total:,} tokens[/dim]")

        return await page_crawler.observe(
            url, action, reuse_session, result_callback=log_result, last_markdown_length=last_markdown_length
        )
    
    def extraction_result(self, articles: list[Article], valid: list[Article], 
                          next_action: NavigationAction | None, start_dt: date, end_dt: date,
                          extraction_issues: list[str] | None = None) -> None:
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
        
        summary.append(f"\nNext: ", style="white")
        summary.append(self._format_action(next_action) if next_action else "None", style="cyan")
        
        if extraction_issues:
            summary.append(f"\n[red]Issues:[/red] {', '.join(extraction_issues)}", style="red")
        
        console.print(Panel(summary, border_style="white"))
        
        if valid:
            table = Table(show_header=True, header_style="bold", border_style="dim")
            table.add_column("#", width=3)
            table.add_column("Title", width=45)
            table.add_column("Date", width=12)
            table.add_column("Conf", width=6)
            
            for i, a in enumerate(valid[:5], 1):
                conf_style = {"HIGH": "green", "MEDIUM": "yellow"}.get(a.date_confidence, "red")
                table.add_row(str(i), a.title[:45], a.publication_date or "N/A", 
                              Text(a.date_confidence, style=conf_style))
            
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
        
        summary.append(f"\nTarget Range [{start_dt} - {end_dt}]: ", style="white")
        summary.append(f"{len(valid_articles)}", style="green bold")
        summary.append(" articles", style="white")
        
        if all_date_range:
            summary.append(f"\nDiscovered Range [{all_date_range['min']} - {all_date_range['max']}]: ", style="white")
            summary.append(f"{all_date_range['count']}", style="white")
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
            return "Initial load"
        if action.type == "scroll":
            return f"Scroll {action.value}x"
        return f"Click: {str(action.value)[:60]}"
