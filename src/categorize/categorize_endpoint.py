"""
Categorize endpoint for processing summarized content.
"""

from typing import Dict, Any

from src.shared.base_endpoint import BaseEndpoint
from src.shared.data_loaders import DataLoader
from src.categorize.pipeline import process_content
from src.schemas import CategorizationInput
from src.pipeline_config import PipelineStages


class CategorizeEndpoint(BaseEndpoint):
    """Endpoint for categorizing summarized content."""
    
    def __init__(self):
        super().__init__("CategorizeEndpoint")
    
    def execute(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the categorization process for a single item."""
        try:
            self.logger.debug(f"Processing categorization request for item: {item['id']}")
            
            # Load summary data
            data_loader = DataLoader()
            # Get file path for the latest completed stage (should be summarize)
            current_file_path = item.get('file_paths', {}).get(item.get('latest_completed_stage'))
            if not current_file_path:
                raise ValueError(f"No file path found for latest completed stage {item.get('latest_completed_stage')} for item {item['id']}")
            
            summary_text = data_loader.extract_stage_output(current_file_path, PipelineStages.SUMMARIZE)
            
            # Validate summary content
            if not summary_text or not summary_text.strip():
                raise ValueError("Empty or invalid summary content")
            
            # Create and validate input structure for categorization
            categorization_input = CategorizationInput(
                title=item.get('title', 'Unknown'),
                content_date=item.get('content_date', 'Unknown'),
                content=summary_text
            )
            
            # Create processing context (immutable)
            processing_context = {
                'id': item['id'],
                'categorization_input': categorization_input,
                'previous_error': item.get('error_message')
            }
            
            # Process through categorization
            result = process_content(processing_context)
            
            self.logger.debug(f"Successfully categorized item {item['id']}")
            
            return self._create_success_response(
                id=item['id'],
                result=result,
                stage=PipelineStages.CATEGORIZE.value
            )
            
        except Exception as e:
            self.logger.error(f"Categorization failed for item {item['id']}: {str(e)}", 
                             extra={'item_id': item['id'], 'stage': PipelineStages.CATEGORIZE.value, 'error_type': 'endpoint_error'})
            # Let exception bubble up to flow processor
            raise
