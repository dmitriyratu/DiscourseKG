"""Compact rich console logging for agent visibility."""
from datetime import date
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
    
    async def observe_with_logging(self, page_crawler: "PageCrawler", url: str, 
                                   action: NavigationAction | None = None, 
                                   reuse_session: bool = False) -> PageExtraction:
        """Wrapper around PageCrawler.observe() that logs context size."""
        def log_result(result):
            """Callback to log context size from crawl result."""
            if hasattr(result, 'markdown') and result.markdown:
                content_size = len(result.markdown)
                estimated_tokens = content_size // 4
                self._log_llm_context(content_size, estimated_tokens)
        
        return await page_crawler.observe(url, action, reuse_session, result_callback=log_result)
    
    def extraction_result(self, articles: list[Article], valid: list[Article], 
                          next_action: NavigationAction | None, start_dt: date, end_dt: date,
                          extraction_issues: list[str] | None = None) -> None:
        """Log extraction results with article summary."""
        new_articles = [a for a in articles if a.url not in self.seen_urls]
        self.seen_urls.update(a.url for a in articles)
        
        summary = Text()
        summary.append(f"Found: {len(articles)} articles", style="white")
        if len(new_articles) != len(articles):
            summary.append(f" ({len(new_articles)} new)", style="dim")
        summary.append(f"\nValid (in {start_dt} to {end_dt}): ", style="white")
        summary.append(f"{len(valid)}", style="green bold")
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
    
    def complete(self, articles: list[Article], pages: int, reason: str) -> None:
        """Log final summary."""
        console.print(Panel(
            f"[green bold]Complete[/green bold] | {len(articles)} articles from {pages} pages\n"
            f"[dim]Stop reason: {reason}[/dim]",
            border_style="green"
        ))
    
    def _format_action(self, action: NavigationAction | None) -> str:
        if not action:
            return "Initial load"
        if action.type == "scroll":
            return f"Scroll {action.value}x"
        return f"Click: {str(action.value)[:60]}"
