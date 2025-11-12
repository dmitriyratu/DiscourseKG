"""
Summarize endpoint for processing raw transcripts.
"""

from typing import Dict, Any

from src.shared.base_endpoint import BaseEndpoint
from src.shared.data_loaders import DataLoader
from src.summarize.pipeline import summarize_content
from src.summarize.config import summarization_config
from src.shared.pipeline_definitions import PipelineStages
from src.summarize.models import SummarizeItem, SummarizeContext


class SummarizeEndpoint(BaseEndpoint):
    """Endpoint for summarizing raw transcripts."""
    
    def __init__(self):
        super().__init__("SummarizeEndpoint")
    
    def execute(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the summarization process for a single item."""
        summarize_item = SummarizeItem(**item)

        # Load scrape artifact
        data_loader = DataLoader()
        current_file_path = summarize_item.file_paths.get(summarize_item.latest_completed_stage)
        if not current_file_path:
            raise ValueError(
                f"No file path found for latest completed stage {summarize_item.latest_completed_stage} "
                f"for item {summarize_item.id}"
            )

        # Validate content
        scrape = data_loader.extract_stage_output(current_file_path, PipelineStages.SCRAPE)
        if not scrape or not scrape.strip():
            raise ValueError("Empty or invalid scrape content")

        # Build processing context
        processing_context = SummarizeContext(
            id=summarize_item.id,
            text=scrape,
            target_tokens=summarization_config.TARGET_SUMMARY_TOKENS
        )

        # Execute summarization pipeline - returns StageResult
        stage_result = summarize_content(processing_context)
        
        self.logger.debug(
            f"Successfully summarized item {summarize_item.id} - {stage_result.artifact['data']['summary_word_count']} words"
        )

        return self._create_success_response(
            result=stage_result.artifact,
            stage=PipelineStages.SUMMARIZE.value,
            state_update=stage_result.metadata
        )
