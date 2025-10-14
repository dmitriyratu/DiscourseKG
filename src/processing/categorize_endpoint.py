"""
Categorize endpoint for processing summarized content.
"""

from typing import Dict, Any
from pathlib import Path

from src.shared.data_loaders import SummaryDataLoader
from src.processing.pipeline import process_content
from src.shared.logging_utils import setup_logger

logger = setup_logger("CategorizeEndpoint", "processing_flow.log")


class CategorizeEndpoint:
    """Endpoint for categorizing summarized content."""
    
    def __init__(self):
        pass
    
    def execute(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the categorization process for a single item."""
        try:
            logger.info(f"Categorizing item: {item['id']}")
            
            # Load summary data
            summary_loader = SummaryDataLoader()
            summary_data = summary_loader.load(item['id'])
            
            # Validate summary content
            if not summary_data.summary_text or not summary_data.summary_text.strip():
                raise ValueError("Empty or invalid summary content")
            
            # Create input structure for categorization
            categorization_input = {
                "id": summary_data.id,
                "transcript": summary_data.summary_text,
                "title": f"Summary for {summary_data.id}",
                "speakers": ["Unknown"],  # TODO: Extract from original data
                "date": summary_data.processed_at or "2025-01-01"
            }
            
            # Process through categorization
            result = process_content(categorization_input)
            
            logger.info(f"Successfully categorized item {item['id']}")
            
            return {
                'success': True,
                'item_id': item['id'],
                'stage': 'categorize',
                'result': result,
                'input_data': summary_data
            }
            
        except Exception as e:
            logger.error(f"Categorization failed for item {item['id']}: {str(e)}")
            return {
                'success': False,
                'item_id': item['id'],
                'stage': 'categorize',
                'error': str(e)
            }
