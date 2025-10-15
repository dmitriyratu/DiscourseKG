"""
Categorize endpoint for processing summarized content.
"""

from typing import Dict, Any
from pathlib import Path

from src.shared.base_endpoint import BaseEndpoint
from src.shared.data_loaders import SummaryDataLoader
from src.processing.pipeline import process_content
from src.app_config import config


class CategorizeEndpoint(BaseEndpoint):
    """Endpoint for categorizing summarized content."""
    
    def __init__(self):
        super().__init__("CategorizeEndpoint")
    
    def execute(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the categorization process for a single item."""
        try:
            self.logger.info(f"Categorizing item: {item['id']}")
            
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
                "date": summary_data.processed_at or "2025-01-01"  # TODO: Fix missing date handling
            }
            
            # Process through categorization
            result = process_content(categorization_input)
            
            self.logger.info(f"Successfully categorized item {item['id']}")
            
            return self._create_success_response(
                item_id=item['id'],
                result=result,
                stage='categorize',
                input_data=summary_data
            )
            
        except Exception as e:
            self.logger.error(f"Categorization failed for item {item['id']}: {str(e)}")
            return self._create_error_response(
                item_id=item['id'],
                stage='categorize',
                error=str(e)
            )
