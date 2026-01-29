"""LLM extraction prompt for article scraping."""
from playground.browser_tools_v13.models import DateSource


def build_extraction_prompt(delta_mode: bool = False) -> str:
    """Build extraction instruction; date source data from DateSource.for_prompt()."""
    enum_values, source_bullets = DateSource.for_prompt()
    date_sources = (
        f"source (exactly one of: {enum_values}).\n\n"
        f"Date sources — use one candidate per source that applies; do not merge:\n{source_bullets}"
    )
    prompt = f"""
Extract all articles from this page. Return JSON:
{{"articles": [...], "next_action": {{... or null}}, "extraction_issues": [...]}}

Each article: title (headline), url (full URL), date_candidates (array).
Each date_candidate: date (YYYY-MM-DD only), {date_sources}

Rule: If both the URL and the title (or adjacent line) contain a date for the same article, output two candidates — one with source "url_path", one with source "near_title". Same date, two entries.

Example (one article, two sources):
"date_candidates": [
  {{"date": "2026-01-28", "source": "url_path"}},
  {{"date": "2026-01-28", "source": "near_title"}}
]

next_action: {{"type": "click", "value": "a[href='...']"}} for pagination; {{"type": "scroll"}} for load-more; null if done.
Prefer href selectors: a[href="full-url"]. extraction_issues: list any problems.

Process the ENTIRE document.
"""
    if delta_mode:
        prompt += EXTRACTION_PROMPT_DELTA_SUFFIX
    return prompt.strip()


EXTRACTION_PROMPT_DELTA_SUFFIX = (
    "\n\nThe content above is only the NEW portion of an infinitely-scrolled page "
    "(previous content omitted). Extract articles from it."
)
