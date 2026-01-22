"""Simple callback handler for agent logging."""
from typing import Any, Dict, List, Optional
from datetime import date as date_type
import json
import textwrap
from rich.console import Console
from rich.json import JSON
from rich.panel import Panel
from rich.text import Text
from rich.table import Table

_TRUNCATE_LENGTH = 300
_MAX_ARTICLES_TO_SHOW = 10

class CallbackManager:
    """Manages callback routing from generic events to specific methods."""
    
    def __init__(self, callbacks: Optional[List[Any]] = None):
        self.callbacks = callbacks or []
    
    def emit(self, event: str, **data: Any) -> None:
        """Emit an event to all callbacks."""
        if not self.callbacks:
            return
        for cb in self.callbacks:
            method = getattr(cb, f'on_{event}', None)
            if method:
                method(**data)

class AgentLogger:
    """Rich terminal logging for agent actions with detailed information."""
    
    def __init__(self):
        self._console = Console()
        self._seen_urls = set()
    
    def _truncate(self, text: str, length: int = _TRUNCATE_LENGTH) -> str:
        """Truncate text with ellipsis if needed."""
        if not text:
            return ""
        return textwrap.shorten(str(text), width=length, placeholder="...")
    
    def _print_header(self, title: str) -> None:
        """Print a section header."""
        self._console.print()
        self._console.print(Panel(title, style="bold", border_style="bright_blue"))
    
    def _format_date_range(self, start_dt: Optional[date_type], end_dt: Optional[date_type], stop_dt: Optional[date_type] = None) -> str:
        """Format date range for display."""
        start = str(start_dt) if start_dt else 'N/A'
        end = str(end_dt) if end_dt else 'N/A'
        stop = str(stop_dt) if stop_dt else 'N/A'
        return f"{start} to {end} (stop before {stop})"
    
    def _calculate_reliable_dates(self, articles: List[Dict[str, Any]]) -> List[date_type]:
        """Calculate reliable dates from articles."""
        from datetime import datetime
        
        reliable_dates = []
        for article in articles:
            confidence = article.get('date_confidence', 'NONE')
            if confidence not in ['HIGH', 'MEDIUM']:
                continue
            
            date_str = article.get('publication_date')
            if not date_str:
                continue
            
            try:
                article_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                reliable_dates.append(article_date)
            except (ValueError, TypeError):
                continue
        
        return reliable_dates
    
    def _format_action(self, action: Optional[Dict[str, Any]]) -> str:
        """Format action for display."""
        if not action:
            return "Initial page load"
        action_type = action.get('type', 'unknown')
        if action_type == 'click':
            value = self._truncate(str(action.get('value', '')), 80)
            return f"click → {value}"
        elif action_type == 'scroll':
            return f"scroll → {action.get('value', 0)} times"
        return f"{action_type}: {action}"
    
    def on_page_start(self, url: str, page_num: int, action: Optional[Dict[str, Any]], 
                     start_dt: Optional[date_type] = None, end_dt: Optional[date_type] = None, 
                     stop_dt: Optional[date_type] = None) -> None:
        """Log when page processing starts."""
        self._print_header(f"PAGE {page_num + 1}: PROCESSING")
        
        content = Text()
        content.append("URL: ", style="bold dim")
        content.append(self._truncate(url), style="white")
        
        if action:
            content.append("\n\n", style="white")
            content.append("▶ Action: ", style="white bold")
            action_str = self._format_action(action)
            if action.get('type') == 'scroll':
                content.append(action_str, style="cyan bold")
            elif action.get('type') == 'click':
                content.append(action_str, style="green bold")
            else:
                content.append(action_str, style="yellow bold")
        else:
            content.append("\n\n", style="white")
            content.append("▶ Action: ", style="white bold")
            content.append("Initial page load", style="green bold")
        
        self._console.print(Panel(content, border_style="white"))
    
    def on_page_complete(
        self, 
        url: str, 
        articles: List[Dict[str, Any]],
        navigation_options: List[Dict[str, Any]],
        extraction_error: Optional[str] = None,
        failed_output: Optional[str] = None,
        html_stats: Optional[Dict[str, Any]] = None,
        start_dt: Optional[date_type] = None,
        end_dt: Optional[date_type] = None
    ) -> None:
        """Log when page observation completes."""
        self._print_header("PAGE RESULT")
        
        if extraction_error:
            error_content = Text()
            error_content.append("Extraction Error: ", style="bold red")
            error_content.append(extraction_error, style="red")
            self._console.print(Panel(error_content, border_style="red"))
            
            if failed_output:
                self._console.print(Panel(
                    Text(f"Failed Output (first 500 chars):\n{failed_output[:500]}", style="dim"),
                    border_style="red",
                    title="Failed Output"
                ))
            return
        
        # Filter to only show new articles
        new_articles = [a for a in articles if a.get('url') and a.get('url') not in self._seen_urls]
        new_urls = {a.get('url') for a in new_articles if a.get('url')}
        self._seen_urls.update(new_urls)
        
        if not new_articles and articles:
            pass
        
        # Calculate date range found
        reliable_dates = self._calculate_reliable_dates(articles)
        date_range_found = None
        min_date = None
        max_date = None
        if reliable_dates:
            min_date = min(reliable_dates)
            max_date = max(reliable_dates)
            date_range_found = f"{min_date} to {max_date}"
        
        summary = Text()
        summary.append(f"Articles Found: ", style="bold")
        summary.append(str(len(articles)), style="white")
        if len(articles) != len(new_articles):
            summary.append(f" (", style="dim")
            summary.append(f"{len(new_articles)} new", style="green")
            summary.append(f", {len(articles) - len(new_articles)} already seen)", style="dim")
        
        if date_range_found and min_date and max_date:

            
            summary.append(f"\nTarget Range: ", style="bold")
            summary.append(f"{start_dt} to {end_dt}", style="yellow")

            summary.append(f"\nDate Range Found: ", style="bold")
            summary.append(date_range_found, style="cyan")

        
        summary.append(f"\nNavigation Options: ", style="bold")
        summary.append(str(len(navigation_options)), style="cyan")
        
        if html_stats:
            summary.append(f"\n\nHTML Statistics:", style="bold")
            cleaned_len = html_stats.get('cleaned_html_length', 0)
            markdown_len = html_stats.get('markdown_length', 0)
            summary.append(f"\n  Cleaned HTML: ", style="dim")
            summary.append(f"{cleaned_len:,} chars", style="cyan")
            summary.append(f"\n  Markdown: ", style="dim")
            summary.append(f"{markdown_len:,} chars", style="cyan")
            if html_stats.get('media_count', 0) > 0:
                summary.append(f"\n  Media: ", style="dim")
                summary.append(f"{html_stats.get('media_count', 0)}", style="cyan")
        
        self._console.print(Panel(summary, border_style="white"))
        
        if new_articles:
            self._console.print()
            table = Table(show_header=True, header_style="bold", border_style="white")
            table.add_column("#", style="dim", width=3)
            table.add_column("Title", style="white", width=40)
            table.add_column("Date", style="cyan", width=12)
            table.add_column("Confidence", width=10)
            table.add_column("Source", style="dim", width=15)
            
            for idx, article in enumerate(new_articles[:_MAX_ARTICLES_TO_SHOW], 1):
                title = self._truncate(article.get('title', 'N/A'), 40)
                date = article.get('publication_date', 'N/A')
                confidence = article.get('date_confidence', 'NONE')
                source = article.get('date_source', 'N/A')
                
                conf_style = {
                    'HIGH': 'green',
                    'MEDIUM': 'yellow',
                    'LOW': 'red',
                    'NONE': 'dim'
                }.get(confidence, 'white')
                
                table.add_row(
                    str(idx),
                    title,
                    date,
                    Text(confidence, style=conf_style),
                    source
                )
            
            if len(new_articles) > _MAX_ARTICLES_TO_SHOW:
                table.add_row("...", f"({len(new_articles) - _MAX_ARTICLES_TO_SHOW} more new)", "", "", "")
            elif len(articles) > len(new_articles):
                self._console.print(f"[dim]({len(articles) - len(new_articles)} articles already seen, not shown)[/dim]")
            
            self._console.print(table)
        
        if navigation_options:
            self._console.print()
            nav_text = Text("Navigation Options:\n", style="bold")
            for idx, nav in enumerate(navigation_options, 1):
                nav_text.append(f"  {idx}. ", style="dim")
                nav_text.append(f"{nav.get('kind', 'unknown')}", style="cyan")
                nav_text.append(f": {self._truncate(nav.get('description', ''), 60)}\n", style="white")
            self._console.print(Panel(nav_text, border_style="white"))
    
    def on_articles_filtered(
        self, 
        all_articles: List[Dict[str, Any]],
        valid_articles: List[Dict[str, Any]],
        filter_stats: Dict[str, Any],
        start_dt: Optional[date_type],
        end_dt: Optional[date_type],
        stop_dt: Optional[date_type],
        total_collected: int
    ) -> None:
        """Log article filtering results."""
        self._print_header("ARTICLE FILTERING")
        
        stats = filter_stats
        rejected_counts = stats.get('rejected_counts', {})
        
        summary = Text()
        summary.append("Filtering Results:\n", style="bold")
        summary.append(f"  Total articles: ", style="white")
        summary.append(f"{stats.get('total', 0)}\n", style="cyan")
        summary.append(f"  Valid: ", style="white")
        summary.append(f"{stats.get('valid', 0)}\n", style="green")
        summary.append(f"  Duplicate URL: ", style="white")
        summary.append(f"{rejected_counts.get('duplicate_url', 0)}\n", style="red")
        summary.append(f"  Low confidence: ", style="white")
        summary.append(f"{rejected_counts.get('low_confidence', 0)}\n", style="red")
        summary.append(f"  No date: ", style="white")
        summary.append(f"{rejected_counts.get('no_date', 0)}\n", style="red")
        summary.append(f"  Out of range: ", style="white")
        summary.append(f"{rejected_counts.get('out_of_range', 0)}\n", style="red")
        
        self._console.print(Panel(summary, border_style="white"))
        
        if valid_articles:
            self._console.print()
            valid_text = Text("Valid Articles Collected:\n", style="bold green")
            for idx, article in enumerate(valid_articles, 1):
                valid_text.append(f"  {idx}. ", style="dim")
                valid_text.append(f'"{self._truncate(article.get("title", "N/A"), 50)}"\n', style="white")
                valid_text.append(f"      URL: ", style="dim")
                valid_text.append(f"{self._truncate(article.get('url', ''), 70)}\n", style="cyan")
                valid_text.append(f"      Date: ", style="dim")
                date = article.get('publication_date', 'N/A')
                confidence = article.get('date_confidence', 'NONE')
                source = article.get('date_source', 'N/A')
                valid_text.append(f"{date} ({confidence}, {source})\n\n", style="white")
            self._console.print(Panel(valid_text, border_style="green"))
        
        rejected = stats.get('rejected', {})
        if any(rejected.values()):
            self._console.print()
            rejected_text = Text("Rejected Articles:\n", style="bold red")
            
            if rejected.get('low_confidence'):
                rejected_text.append("  Low Confidence:\n", style="yellow")
                for article in rejected['low_confidence'][:5]:
                    rejected_text.append(f"    - ", style="dim")
                    rejected_text.append(f'"{self._truncate(article.get("title", "N/A"), 50)}"', style="white")
                    rejected_text.append(f" ({article.get('date_confidence', 'NONE')} confidence", style="red")
                    if article.get('publication_date'):
                        rejected_text.append(f", date: {article.get('publication_date')}", style="dim")
                    rejected_text.append(")\n", style="red")
                if len(rejected['low_confidence']) > 5:
                    rejected_text.append(f"    ... ({len(rejected['low_confidence']) - 5} more)\n", style="dim")
            
            if rejected.get('no_date'):
                rejected_text.append("  No Date:\n", style="yellow")
                for article in rejected['no_date'][:5]:
                    rejected_text.append(f"    - ", style="dim")
                    rejected_text.append(f'"{self._truncate(article.get("title", "N/A"), 50)}"\n', style="white")
                if len(rejected['no_date']) > 5:
                    rejected_text.append(f"    ... ({len(rejected['no_date']) - 5} more)\n", style="dim")
            
            if rejected.get('out_of_range'):
                rejected_text.append("  Out of Range:\n", style="yellow")
                for article in rejected['out_of_range'][:5]:
                    rejected_text.append(f"    - ", style="dim")
                    rejected_text.append(f'"{self._truncate(article.get("title", "N/A"), 50)}"', style="white")
                    date = article.get('publication_date')
                    if date:
                        rejected_text.append(f" ({date})", style="dim")
                    rejected_text.append("\n", style="white")
                if len(rejected['out_of_range']) > 5:
                    rejected_text.append(f"    ... ({len(rejected['out_of_range']) - 5} more)\n", style="dim")
            
            if rejected.get('duplicate_url'):
                rejected_text.append(f"  Duplicate URL: {len(rejected['duplicate_url'])} articles\n", style="yellow")
            
            self._console.print(Panel(rejected_text, border_style="red"))
        
        total_text = Text()
        total_text.append("Total Collected So Far: ", style="bold")
        total_text.append(str(total_collected), style="cyan bold")
        self._console.print(Panel(total_text, border_style="white"))
    
    def on_navigation_decision(self, navigation_options: List[Dict[str, Any]], selected_action: Optional[Dict[str, Any]]) -> None:
        """Log navigation decision."""
        self._print_header("NAVIGATION DECISION")
        
        if navigation_options:
            nav_text = Text("Available Options:\n", style="bold")
            for idx, nav in enumerate(navigation_options, 1):
                nav_text.append(f"  Option {idx}: ", style="dim")
                nav_text.append(f"{nav.get('kind', 'unknown')}\n", style="cyan")
                nav_text.append(f"    Description: {self._truncate(nav.get('description', ''), 70)}\n", style="white")
                action = nav.get('action', {})
                if action:
                    nav_text.append(f"    Action: ", style="dim")
                    nav_text.append(self._format_action(action), style="white")
                    nav_text.append("\n", style="white")
            
            if selected_action:
                nav_text.append("\nSelected: ", style="bold green")
                for idx, nav in enumerate(navigation_options, 1):
                    if nav.get('action') == selected_action:
                        nav_text.append(f"Option {idx} ({nav.get('kind', 'unknown')})", style="green bold")
                        break
            else:
                nav_text.append("\nSelected: ", style="bold yellow")
                nav_text.append("None (stopping)", style="yellow")
            
            self._console.print(Panel(nav_text, border_style="white"))
        else:
            if selected_action:
                # Skip verbose message for fallback scrolls - action already shown in PAGE START
                if selected_action.get('type') == 'scroll':
                    pass  # Don't show redundant info
                else:
                    nav_text = Text("No navigation options detected by LLM\n", style="bold yellow")
                    nav_text.append("\nFallback: ", style="bold")
                    nav_text.append(f"Using {selected_action.get('type', 'unknown')} action\n", style="cyan")
                    nav_text.append("\nSelected: ", style="bold green")
                    nav_text.append(self._format_action(selected_action), style="green bold")
                    self._console.print(Panel(nav_text, border_style="yellow"))
            else:
                self._console.print(Panel(
                    Text("No navigation options available (stopping)", style="yellow"),
                    border_style="white"
                ))
    
    def on_action_skip(self, url: str, action: Dict[str, Any], reason: str) -> None:
        """Log when an action is skipped."""
        self._print_header("ACTION SKIPPED")
        
        content = Text()
        content.append("Reason: ", style="bold")
        content.append(reason, style="red")
        content.append(f"\nAction: ", style="bold")
        content.append(self._format_action(action), style="white")
        content.append(f"\nURL: ", style="bold")
        content.append(self._truncate(url), style="white")
        
        self._console.print(Panel(content, border_style="red"))
    
    def on_stop_condition(self, reason: str, pages_processed: int, articles_collected: int, 
                         current_page_articles: Optional[List[Dict[str, Any]]] = None,
                         stop_dt: Optional[date_type] = None, max_pages: Optional[int] = None) -> None:
        """Log stop condition."""
        self._print_header("STOPPING")
        
        content = Text()
        content.append("Stop Reason: ", style="bold")
        content.append(reason, style="red bold")
        
        if reason == "date_threshold" and current_page_articles and stop_dt:
            reliable_dates = self._calculate_reliable_dates(current_page_articles)
            oldest_date = min(reliable_dates) if reliable_dates else None
            
            content.append("\n\nCurrent Page:", style="bold")
            content.append(f"\n  Articles found: {len(current_page_articles)}", style="white")
            if oldest_date:
                content.append(f"\n  Oldest reliable date: ", style="white")
                content.append(str(oldest_date), style="cyan")
            content.append(f"\n  Date threshold: ", style="white")
            content.append(str(stop_dt), style="cyan")
            if oldest_date:
                content.append(f"\n\nReason: Oldest article date ({oldest_date}) is before", style="white")
                content.append(f"\n        threshold ({stop_dt}), stopping to avoid", style="white")
                content.append(f"\n        processing older content.", style="white")
        elif reason == "max_pages" and max_pages:
            content.append(f"\n\nReached maximum pages limit: {max_pages}", style="white")
        
        content.append(f"\n\nStatus:", style="bold")
        content.append(f"\n  Pages processed: {pages_processed}", style="white")
        content.append(f"\n  Articles collected: {articles_collected}", style="cyan bold")
        
        self._console.print(Panel(content, border_style="red"))
    
    def on_complete(self, pages_processed: int, articles_collected: int, stop_reason: str,
                   articles: List[Dict[str, Any]], start_dt: Optional[date_type], 
                   end_dt: Optional[date_type]) -> None:
        """Log final summary."""
        self._print_header("SCRAPING COMPLETE")
        
        summary = Text()
        summary.append("Final Results:\n", style="bold")
        summary.append(f"  Pages processed: {pages_processed}\n", style="white")
        summary.append(f"  Articles collected: ", style="white")
        summary.append(f"{articles_collected}\n", style="cyan bold")
        summary.append(f"  Stop reason: ", style="white")
        summary.append(f"{stop_reason}\n", style="yellow")
        if start_dt and end_dt:
            summary.append(f"  Date range: ", style="white")
            summary.append(f"{start_dt} to {end_dt}\n", style="cyan")
        
        self._console.print(Panel(summary, border_style="bright_blue"))
        
        if articles:
            self._console.print()
            articles_text = Text("Collected Articles:\n", style="bold")
            for idx, article in enumerate(articles, 1):
                articles_text.append(f"  {idx}. ", style="dim")
                articles_text.append(f'"{self._truncate(article.get("title", "N/A"), 50)}"\n', style="white")
                articles_text.append(f"      {self._truncate(article.get('url', ''), 70)}\n", style="cyan")
                date = article.get('publication_date', 'N/A')
                confidence = article.get('date_confidence', 'NONE')
                source = article.get('date_source', 'N/A')
                articles_text.append(f"      {date} ({confidence}, {source})\n\n", style="dim")
            
            self._console.print(Panel(articles_text, border_style="bright_blue"))
