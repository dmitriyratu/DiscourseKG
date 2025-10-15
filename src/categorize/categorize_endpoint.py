"""
Categorize endpoint for processing summarized content.
"""

from typing import Dict, Any

from src.shared.base_endpoint import BaseEndpoint
from src.shared.data_loaders import SummaryDataLoader, RawDataLoader
from src.categorize.pipeline import process_content
from src.pipeline_config import PipelineStages


class CategorizeEndpoint(BaseEndpoint):
    """Endpoint for categorizing summarized content."""
    
    def __init__(self):
        super().__init__("CategorizeEndpoint")
    
    def execute(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the categorization process for a single item."""
        try:
            self.logger.info(f"Categorizing item: {item['id']}")
            
            # Load summary data with metadata
            summary_loader = SummaryDataLoader()
            speaker = item.get('speaker')
            content_type = item.get('content_type')
            summary_data = summary_loader.load(item['id'])
            
            # Validate summary content
            if not summary_data.summary_text or not summary_data.summary_text.strip():
                raise ValueError("Empty or invalid summary content")
            
            # Load raw data to get metadata (title, speakers, date)
            raw_loader = RawDataLoader()
            raw_data = raw_loader.load(item['raw_file_path'])
            
            # Create input structure for categorization with all required fields
            categorization_input = {
                "id": item['id'],
                "transcript": summary_data.summary_text,
                "title": raw_data.title,
                "speakers": raw_data.speakers,
                "date": raw_data.date
            }
            
            # Process through categorization
            result = process_content(categorization_input)
            
            self.logger.info(f"Successfully categorized item {item['id']}")
            
            return self._create_success_response(
                id=item['id'],
                result=result,
                stage=PipelineStages.CATEGORIZE
            )
            
        except Exception as e:
            self.logger.error(f"Categorization failed for item {item['id']}: {str(e)}")
            return self._create_error_response(
                id=item['id'],
                stage=PipelineStages.CATEGORIZE,
                error=str(e)
            )
