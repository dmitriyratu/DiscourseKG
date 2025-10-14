"""
Summarize endpoint for processing raw transcripts.
"""

from typing import Dict, Any
from pathlib import Path

from src.shared.data_loaders import RawDataLoader
from src.preprocessing.pipeline import preprocess_content
from src.shared.logging_utils import setup_logger

logger = setup_logger("SummarizeEndpoint", "preprocessing_flow.log")


class SummarizeEndpoint:
    """Endpoint for summarizing raw transcripts."""
    
    def __init__(self):
        pass
    
    def execute(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the summarization process for a single item."""
        try:
            logger.info(f"Summarizing item: {item['id']}")
            
            # Load raw data
            raw_loader = RawDataLoader()
            raw_data = raw_loader.load(item['raw_file_path'])
            
            # Validate transcript content
            if not raw_data.transcript or not raw_data.transcript.strip():
                raise ValueError("Empty or invalid transcript content")
            
            # Process through summarization
            result = preprocess_content(raw_data.transcript, 1000)
            
            if not result.success:
                raise ValueError(f"Summarization failed: {result.error_message}")
            
            logger.info(f"Successfully summarized item {item['id']} - {result.summary_word_count} words")
            
            return {
                'success': True,
                'item_id': item['id'],
                'stage': 'summarize',
                'result': result,
                'input_data': raw_data
            }
            
        except Exception as e:
            logger.error(f"Summarization failed for item {item['id']}: {str(e)}")
            return {
                'success': False,
                'item_id': item['id'],
                'stage': 'summarize',
                'error': str(e)
            }
