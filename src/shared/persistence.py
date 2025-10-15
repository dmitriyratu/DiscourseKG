"""
Simple persistence utilities for saving pipeline data.
"""

from pathlib import Path
import json
from datetime import datetime
from typing import Any, Optional

from src.app_config import config
from src.shared.logging_utils import get_logger
from src.pipeline_config import PipelineStages

logger = get_logger(__name__)


def save_data(id: str, data: Any, data_type: str, speaker: Optional[str] = None, content_type: Optional[str] = None) -> str:
    """
    Save data with speaker and content-type organized directory structure.
    
    Directory structure: {environment}/{speaker}/{data_type}/{content_type}/{id}_{timestamp}.json
    
    Args:
        id: Unique identifier for the data item
        data: Data to save (dict or any serializable object)
        data_type: Pipeline stage type (scrape, summarize, categorize)
        speaker: Speaker name (extracted from data if not provided)
        content_type: Content type (speech, debate, interview, etc.)
        
    Returns:
        Path to the saved file
    """
    # Use DATA_ROOT as base path
    base_path = config.DATA_ROOT
    
    # Generate file path with speaker/content-type structure
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Extract metadata - use provided content_type or fallback to data
    if not content_type:
        content_type = data.get('type', 'unknown') if isinstance(data, dict) else 'unknown'
    
    # Get speaker from parameter or extract from data
    if not speaker and isinstance(data, dict):
        speakers = data.get('speakers', [])
        speaker = speakers[0] if speakers else 'unknown'
    
    speaker = speaker or 'unknown'
    
    # Create path: {environment}/{speaker}/{data_type}/{content_type}/
    filename = f"{id}_{timestamp}.json"
    file_path = Path(base_path) / config.ENVIRONMENT / speaker / data_type / content_type / filename
    
    # Save file
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved {data_type} data to {file_path}")
    return str(file_path)
