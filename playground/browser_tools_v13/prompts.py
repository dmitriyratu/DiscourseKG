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
- publication_date: YYYY-MM-DD format only (e.g., 2025-01-15)
- date_confidence: HIGH (datetime attr, schema.org), MEDIUM (URL path, near title), LOW (inferred), NONE
- date_source: datetime_attr | schema_org | url_path | near_title | metadata

Date priority:
1. <time datetime> attributes (HIGH)
2. schema.org datePublished (HIGH)
3. URL path dates like /2025/01/15/ (MEDIUM)
4. "Published on..." text near titles (MEDIUM)
5. Other metadata (LOW)

For "next_action" field, return one of:
- {"type": "click", "value": "a[href='...']"} for pagination/next page links
- {"type": "scroll", "value": 3} for infinite scroll pages
- null if no more content available or this is the last page

Pagination hints: Look for rel="next", aria-label with "next", "Load More", "Show More" buttons.
Prefer href-based selectors: a[href="full-url-here"]

For "extraction_issues", list any problems encountered (e.g., ["dates unclear for 3 articles"]).

IMPORTANT: Process the ENTIRE document. For infinite scroll pages, older content appears further down.
"""
