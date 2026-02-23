"""
Simple persistence utilities for saving pipeline data.

Implements unified hierarchical file structure across all stages:
{date}/{source_slug}/{id}/{stage}.json
"""

import json
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

import pyprojroot

from src.config import config
from src.utils.logging_utils import get_logger
from src.utils.string_utils import slugify

logger = get_logger(__name__)


def _source_slug(search_url: Optional[str]) -> str:
    """Convert search URL to source slug (e.g., 'rollcall.com/factbase/trump/' -> 'rollcall-factbase')."""
    if not search_url:
        return "unknown-source"
    try:
        parsed = urlparse(search_url)
        domain = parsed.netloc.replace('www.', '').split('.')[0]
        path_parts = [p for p in parsed.path.split('/') if p]
        path_slug = path_parts[0] if path_parts else ""
        return f"{domain}-{slugify(path_slug)}" if path_slug else domain
    except Exception:
        return "unknown-source"


def save_data(context: Any, data: Any, stage: str) -> str:
    """
    Save data with unified hierarchical directory structure.

    Path pattern: {date}/{source_slug}/{id}/{stage}.json

    Context must have: id, publication_date, search_url.
    """
    date = context.publication_date
    url = context.search_url
    file_path = Path(config.DATA_ROOT) / date / _source_slug(url) / context.id / f"{stage}.json"

    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    relative_path = file_path.relative_to(pyprojroot.here())
    logger.debug(f"Saved {stage} data to {relative_path}")
    return str(relative_path).replace('\\', '/')
