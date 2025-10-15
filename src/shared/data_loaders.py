"""
Data loaders for different pipeline stages.

Provides clean abstractions for loading data at each stage of the pipeline.
"""

from pathlib import Path
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass

from src.app_config import config
from src.shared.logging_utils import get_logger
from src.pipeline_config import PipelineStages

logger = get_logger(__name__)


@dataclass
class RawData:
    """Raw transcript data structure."""
    id: str
    title: str
    date: str
    type: str
    source_url: str
    speakers: list
    transcript: str


@dataclass
class SummaryData:
    """Summary data structure."""
    id: str
    summary_text: str


class BaseDataLoader:
    """Base class for data loaders."""
    
    def load_json_file(self, file_path: str) -> Dict[str, Any]:
        """Load JSON data from file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {file_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {file_path}: {e}")
    
    def find_latest_file(self, directory: str, pattern: str) -> str:
        """Find the most recent file matching pattern in directory (recursive search)."""
        search_dir = Path(directory)
        if not search_dir.exists():
            raise FileNotFoundError(f"Directory does not exist: {directory}")
        
        # Search recursively through subdirectories
        files = list(search_dir.rglob(pattern))
        if not files:
            raise FileNotFoundError(f"No files found matching {pattern} in {directory}")
        
        latest_file = max(files, key=lambda f: f.stat().st_mtime)
        return str(latest_file)


class RawDataLoader(BaseDataLoader):
    """Loads raw transcript data."""
    
    def load(self, file_path: str) -> RawData:
        """Load raw data from file path."""
        logger.info(f"Loading raw data from {file_path}")
        
        data = self.load_json_file(file_path)
        
        # Validate required fields
        required_fields = ['id', 'title', 'date', 'type', 'source_url', 'speakers', 'transcript']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field '{field}' in raw data")
        
        return RawData(
            id=data['id'],
            title=data['title'],
            date=data['date'],
            type=data['type'],
            source_url=data['source_url'],
            speakers=data['speakers'],
            transcript=data['transcript']
        )


class SummaryDataLoader(BaseDataLoader):
    """Loads summary data for categorization."""
    
    def load(self, id: str) -> SummaryData:
        """
        Load summary data for given item ID.
        
        Args:
            id: Unique identifier for the data item
            
        Returns:
            SummaryData object with loaded data
        """
        logger.info(f"Loading summary data for item {id}")
        
        # Simple ID-based search across all directories
        search_path = str(Path(config.DATA_ROOT) / config.ENVIRONMENT)
        summary_file = self.find_latest_file(
            search_path,
            f"*{id}*.json"
        )
        
        data = self.load_json_file(summary_file)
        
        # Validate required fields - check for both 'summary' and 'summary_text' for compatibility
        summary_text = data.get('summary_text') or data.get('summary')
        if not summary_text:
            raise ValueError(f"Missing 'summary' or 'summary_text' field in summary data")
        
        return SummaryData(
            id=data.get('id', id),
            summary_text=summary_text
        )
