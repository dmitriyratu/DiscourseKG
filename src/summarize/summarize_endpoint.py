"""
Summarize endpoint for processing raw transcripts.
"""

from typing import Dict, Any

from src.shared.base_endpoint import BaseEndpoint
from src.shared.data_loaders import RawDataLoader
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
            self.logger.info(f"Summarizing item: {item['id']}")
            
            # Load raw data
            raw_loader = RawDataLoader()
            raw_data = raw_loader.load(item['raw_file_path'])
            
            # Validate transcript content
            if not raw_data.transcript or not raw_data.transcript.strip():
                raise ValueError("Empty or invalid transcript content")
            
            # Process through summarization
            result = preprocess_content(item['id'], raw_data.transcript, config.TARGET_SUMMARY_TOKENS)
            
            if not result['success']:
                raise ValueError(f"Summarization failed: {result['error_message']}")
            
            self.logger.info(f"Successfully summarized item {item['id']} - {result['summary_word_count']} words")
            
            return self._create_success_response(
                id=item['id'],
                result=result,
                stage=PipelineStages.SUMMARIZE
            )
            
        except Exception as e:
            self.logger.error(f"Summarization failed for item {item['id']}: {str(e)}")
            return self._create_error_response(
                id=item['id'],
                stage=PipelineStages.SUMMARIZE,
                error=str(e)
            )
