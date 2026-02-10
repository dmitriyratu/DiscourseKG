"""
Simple persistence utilities for saving pipeline data.

Implements unified hierarchical file structure across all stages:
{environment}/{speaker}/{stage}/{date}/{source_slug}/{id}.json
"""

import json
import re
from pathlib import Path
from typing import Any, Optional, Tuple
from urllib.parse import urlparse

import pyprojroot

from src.config import config
from src.utils.logging_utils import get_logger
from src.utils.string_utils import slugify

logger = get_logger(__name__)


def _extract_date_from_id(id: str) -> str:
    """Extract YYYY-MM-DD from ID, return 'unknown-date' if invalid."""
    date_part = id[:10] if len(id) >= 10 else ""
    return date_part if re.match(r'^\d{4}-\d{2}-\d{2}$', date_part) else "unknown-date"


def _create_search_slug(search_url: Optional[str] = None) -> str:
    """Convert search URL to source slug (e.g., 'rollcall.com/factbase/trump/' -> 'rollcall-factbase')."""
    if not search_url:
        return "unknown-source"
    
    try:
        parsed = urlparse(search_url)
        # Get domain without www
        domain = parsed.netloc.replace('www.', '').split('.')[0]
        
        # Get first meaningful path segment
        path_parts = [p for p in parsed.path.split('/') if p]
        path_slug = path_parts[0] if path_parts else ""
        
        # Combine domain and first path segment
        if path_slug:
            return f"{domain}-{slugify(path_slug)}"
        return domain
    except Exception:
        return "unknown-source"


def _get_state_info(id: str) -> Tuple[Optional[str], Optional[str]]:
    """Look up speaker and search_url from PipelineState. Returns (speaker, search_url)."""
    # Import here to avoid circular imports
    from src.shared.pipeline_state import PipelineStateManager
    
    try:
        manager = PipelineStateManager()
        state = manager.get_state(id)
        if state:
            return state.speaker, state.search_url
    except Exception as e:
        logger.debug(f"Could not look up state for {id}: {e}")
    
    return None, None


def save_data(id: str, data: Any, data_type: str, **kwargs) -> str:
    """
    Save data with unified hierarchical directory structure.
    
    Path pattern: {environment}/{speaker}/{data_type}/{date}/{source_slug}/{id}.json
    
    Args:
        id: Unique identifier (format: YYYY-MM-DD-title-slug-hash)
        data: Data to save (will be JSON serialized)
        data_type: Stage name (discover/scrape/categorize/summarize/graph)
        **kwargs: Optional fallbacks for discover stage:
            - speaker: Speaker name (looked up from state if not provided)
            - search_url: Search URL for source slug (looked up from state if not provided)
    
    Returns:
        Relative file path from project root
    """
    # Extract date from ID
    date = _extract_date_from_id(id)
    
    # Try to get speaker and search_url from state first, fall back to kwargs
    state_speaker, state_search_url = _get_state_info(id)
    
    speaker = state_speaker or kwargs.get('speaker') or 'unknown-speaker'
    search_url = state_search_url or kwargs.get('search_url')
    
    # Convert search_url to source slug
    source_slug = _create_search_slug(search_url)
    
    # Build path: {environment}/{speaker}/{data_type}/{date}/{source_slug}/{id}.json
    base_path = config.DATA_ROOT
    filename = f"{id}.json"
    file_path = Path(base_path) / config.ENVIRONMENT / speaker / data_type / date / source_slug / filename
    
    # Save file
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    # Return path relative to project root
    relative_path = file_path.relative_to(pyprojroot.here())
    logger.debug(f"Saved {data_type} data to {relative_path}")
    return str(relative_path).replace('\\', '/')
