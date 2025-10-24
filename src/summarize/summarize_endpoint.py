"""
Summarize endpoint for processing raw transcripts.
"""

from typing import Dict, Any

from src.shared.base_endpoint import BaseEndpoint
from src.shared.data_loaders import DataLoader
from src.summarize.pipeline import preprocess_content
from src.app_config import config
from src.pipeline_config import PipelineStages


class SummarizeEndpoint(BaseEndpoint):
    """Endpoint for summarizing raw transcripts."""
    
    def __init__(self):
        super().__init__("SummarizeEndpoint")
    
    def execute(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the summarization process for a single item."""
        try:
            self.logger.info(f"Processing summarization request for item: {item['id']}")
            self.logger.debug(f"Summarizing item: {item['id']}")
            
            # Load raw data
            data_loader = DataLoader()
            # Get file path for the latest completed stage (should be scrape)
            current_file_path = item.get('file_paths', {}).get(item.get('latest_completed_stage'))
            if not current_file_path:
                raise ValueError(f"No file path found for latest completed stage {item.get('latest_completed_stage')} for item {item['id']}")
            
            scrape = data_loader.extract_stage_output(current_file_path, PipelineStages.SCRAPE)
            
            # Validate scrape content
            if not scrape or not scrape.strip():
                raise ValueError("Empty or invalid scrape content")
            
            # Process through summarization
            result = preprocess_content(item['id'], scrape, config.TARGET_SUMMARY_TOKENS)
            
            self.logger.debug(f"Successfully summarized item {item['id']} - {result['data']['summary_word_count']} words")
            
            return self._create_success_response(
                id=item['id'],
                result=result,
                stage=PipelineStages.SUMMARIZE.value
            )
            
        except Exception as e:
            self.logger.error(f"Summarization failed for item {item['id']}: {str(e)}", 
                             extra={'item_id': item['id'], 'stage': PipelineStages.SUMMARIZE.value, 'error_type': 'endpoint_error'})
            # Let exception bubble up to flow processor
            raise
