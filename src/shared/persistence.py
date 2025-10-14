"""
Simple persistence utilities for saving pipeline data.
"""

from pathlib import Path
import json
from datetime import datetime
from typing import Any

from src.app_config import config
from src.shared.logging_utils import setup_logger

logger = setup_logger("persistence", "persistence.log")


def save_data(item_id: str, data: Any, data_type: str) -> str:
    """
    Save data with timestamp and automatic subdirectory.
    
    Args:
        item_id: Unique identifier for the item
        data: Data to save
        data_type: Type of data (e.g., 'raw', 'summary', 'categorization')
        
    Returns:
        Path to saved file
    """
    # Generate timestamp and filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{data_type}_{item_id}_{timestamp}.json"
    
    # Auto-generate subdirectory from data_type
    subdirectories = {
        'summary': 'summaries',
        'categorization': 'categories', 
        'raw': 'test'
    }
    subdirectory = subdirectories[data_type]
    
    # Build file path
    base_path = config.RAW_DATA_PATH if data_type == 'raw' else config.PROCESSED_DATA_PATH
    file_path = Path(base_path) / subdirectory / filename
    
    # Create parent directories and save
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved {data_type} data to {file_path}")
    return str(file_path)
