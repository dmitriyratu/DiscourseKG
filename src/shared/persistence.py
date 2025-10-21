"""
Simple persistence utilities for saving pipeline data.
"""

from pathlib import Path
import json
from datetime import datetime
from typing import Any, Optional

from src.app_config import config
from src.shared.logging_utils import get_logger

logger = get_logger(__name__)


def save_data(id: str, data: Any, data_type: str, speaker: str, content_type: str) -> str:
    """Save data with speaker and content-type organized directory structure."""
    # Use DATA_ROOT as base path
    base_path = config.DATA_ROOT
    
    # Generate file path with speaker/content-type structure
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Use provided speaker and content_type
    
    # Create path: {environment}/{speaker}/{data_type}/{content_type}/
    filename = f"{id}_{timestamp}.json"
    file_path = Path(base_path) / config.ENVIRONMENT / speaker / data_type / content_type / filename
    
    # Save file
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    logger.debug(f"Saved {data_type} data to {file_path}")
    return str(file_path)
