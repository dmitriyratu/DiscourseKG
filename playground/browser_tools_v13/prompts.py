"""LLM extraction prompt for article scraping."""

EXTRACTION_PROMPT = """
Extract all articles with publication dates from this page. Scan the ENTIRE document systematically.

Return a JSON object with this structure:
{
  "articles": [...list of article objects...],
  "next_action": {...action object or null...},
  "extraction_issues": [...list of issues encountered...]
}

For each article in the "articles" array:
- title: Article headline
- url: Full URL to the article
- date_candidates: Array of date candidates found for this article. Each candidate has:
  - date: YYYY-MM-DD format only (e.g., 2025-01-15)
  - source: One of: datetime_attr, schema_org, url_path, near_title, metadata

IMPORTANT: Extract ALL date candidates you find for each article from different sources. Do not pick just one - collect all available dates from:
1. <time datetime> attributes (source: datetime_attr)
2. schema.org datePublished (source: schema_org)
3. URL path dates like /2025/01/15/ (source: url_path)
4. "Published on..." text near titles (source: near_title)
5. Other metadata (source: metadata)

For "next_action" field, return one of:
- {"type": "click", "value": "a[href='...']"} for pagination/next page links
- {"type": "scroll"} to scroll down and load more content (for infinite scroll pages)
- null if no more content available or this is the last page

Pagination hints: Look for rel="next", aria-label with "next", "Load More", "Show More" buttons.
Prefer href-based selectors: a[href="full-url-here"]

For "extraction_issues", list any problems encountered (e.g., ["dates unclear for 3 articles"]).

IMPORTANT: Process the ENTIRE document.
"""

EXTRACTION_PROMPT_DELTA_SUFFIX = (
    "\n\nThe content above is only the NEW portion of an infinitely-scrolled page "
    "(previous content omitted). Extract articles from it."
)
