"""Agent-driven web scraping with atomic tools.

The agent gets 5 simple tools and decides its own strategy:
- FetchPage: Load URL, extract links, get hints about page structure
- ScrollPage: Scroll N times, get updated content  
- ClickElement: Click button/link, get new page
- AnalyzeLinks: Compare old/new links, get progress analysis
- FilterLinks: Filter by URL pattern and date range

Agent explores the page, detects if it's paginated or scroll-based,
collects data efficiently, and stops when confident it's done.
"""

from crewai import Agent, Task, Crew, LLM
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from playground.browser_tools_v3 import (
    FetchPage, ScrollPage, ClickElement, AnalyzeLinks, FilterLinks
)

load_dotenv()

# Create traces directory
TRACES_DIR = Path(__file__).parent / "agent_traces"
TRACES_DIR.mkdir(exist_ok=True, parents=True)

def log_agent_step(step_output):
    """Log steps to file AND print useful summary to terminal."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = TRACES_DIR / f"scraper_run_{timestamp}.jsonl"
    
    # Extract data for logging
    step_data = {
        "timestamp": datetime.now().isoformat(),
        "type": type(step_output).__name__
    }
    
    for attr in ['tool_name', 'tool_input', 'tool_output', 'log', 'action', 'output']:
        if hasattr(step_output, attr):
            value = getattr(step_output, attr)
            step_data[attr] = str(value) if not isinstance(value, (str, int, float, bool, list, dict, type(None))) else value
    
    # Write to file
    with open(log_file, "a", encoding="utf-8") as f:
        json.dump(step_data, f, ensure_ascii=False, default=str)
        f.write("\n")
    
    # Print useful summary to terminal (since crew verbose=False)
    if hasattr(step_output, 'tool_name'):
        tool_name = step_output.tool_name
        print(f"\n🔧 {tool_name}", end="")
        
        # Show key metrics from output
        if hasattr(step_output, 'tool_output'):
            output_str = str(step_output.tool_output)
            try:
                output_json = json.loads(output_str)
                if isinstance(output_json, dict):
                    # Extract useful metrics
                    metrics = []
                    if 'total_links' in output_json:
                        metrics.append(f"{output_json['total_links']} links")
                    if 'links_with_dates' in output_json:
                        metrics.append(f"{output_json['links_with_dates']} with dates")
                    if 'new_unique' in output_json:
                        metrics.append(f"{output_json['new_unique']} new")
                    if 'scrolled' in output_json:
                        metrics.append(f"scrolled {output_json['scrolled']}x")
                    if 'recommendation' in output_json.get('analysis', {}):
                        rec = output_json['analysis']['recommendation']
                        print(f" → {' | '.join(metrics)}")
                        print(f"   💡 {rec}")
                    elif metrics:
                        print(f" → {' | '.join(metrics)}")
                    else:
                        print()
            except:
                print()
    elif hasattr(step_output, 'log'):
        # Show thinking/reasoning
        log = str(step_output.log)
        if "Thought:" in log or "Reasoning" in log:
            print(f"\n💭 Thinking...")
    
    return step_output

# Agent with atomic scraping tools - it decides the strategy
scraper_agent = Agent(
    role="Web Scraping Specialist",
    goal="{goal}",
    backstory=(
        "Expert at web scraping. You intelligently explore pages using available tools. "
        "You analyze page structure (pagination, infinite scroll, static), decide optimal approach, "
        "and collect data efficiently. You know when to continue and when to stop."
    ),
    llm=LLM(model="gpt-4o-mini"),
    tools=[FetchPage(), ScrollPage(), ClickElement(), AnalyzeLinks(), FilterLinks()],
    verbose=True,
    reasoning=True,  # NEW: Shows agent's planning/reasoning process
    max_iter=25
)

crew = Crew(
    agents=[scraper_agent],
    tasks=[],
    verbose=False,  # Disable crew spam (status updates, boxes)
    step_callback=log_agent_step
)


def find_content_in_date_range(url: str, url_filter: str, start_date: str, end_date: str):
    """Find content in a date range - agent decides the strategy."""
    
    task = Task(
        description=f"""
        Extract ALL available links from {url} matching:
        - URL contains: '{url_filter}'
        - Date range: {start_date} to {end_date}
        
        CRITICAL: Be thorough, not efficient. Many sites hide their loading mechanisms.
        
        MANDATORY EXPLORATION STEPS:
        1. fetch_page(url) - Get initial content and hints
        
        2. ALWAYS try scrolling (even if no scroll indicators):
           - scroll_page(url, scroll_count=5) at least 2-3 times
           - After each scroll: analyze_links(all_previous, new_results)
           - Stop scrolling only if analyze_links shows 0 new unique links 2x in a row
        
        3. Look for pagination controls:
           - Check hints for has_next_button, has_pagination
           - If found: use click_element with appropriate selector
           - Continue until element not found or disabled
        
        4. Cross-check results against criteria:
           - If NO links match your date range yet, but you see OTHER dates → KEEP EXPLORING
           - Example: You need Nov 2024, but see Dec 2025 → scroll more for older content
           - Don't give up until you find matches OR exhausted all strategies
        
        5. Final filtering:
           - Once you've collected everything (tried scroll + pagination + no new links)
           - Use filter_links to extract matches
        
        STOPPING CONDITIONS (must meet ALL):
        - ✓ Tried scrolling at least 3 times
        - ✓ Tried clicking pagination if hints suggested it
        - ✓ analyze_links shows no new content after 2 consecutive attempts
        - ✓ OR found sufficient matches (20+ matching links)
        
        Don't be conservative. Try everything. Many sites lazy-load without obvious indicators.
        """,
        expected_output="JSON with matched links (url, text, date) and summary of collection process",
        agent=scraper_agent
    )
    
    crew.tasks = [task]
    result = crew.kickoff(inputs={"goal": f"Extract dated content from {url}"})
    
    return result


if __name__ == "__main__":
    print("\n" + "="*60)
    print(f"📝 Logging full agent steps to: {TRACES_DIR}/")
    print("="*60 + "\n")
    
    result = find_content_in_date_range(
        url='https://rollcall.com/factbase/trump/search/',
        url_filter='transcript',
        start_date='2024-11-23',
        end_date='2024-11-29'
    )
    
    print("\n" + "="*60)
    print("FINAL RESULT:")
    print("="*60)
    print(result)
    
    print("\n" + "="*60)
    print(f"📋 Full logs saved: {list(TRACES_DIR.glob('*.jsonl'))[-1] if list(TRACES_DIR.glob('*.jsonl')) else 'N/A'}")
    print("="*60)
