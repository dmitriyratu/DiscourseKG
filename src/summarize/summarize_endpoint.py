"""
Summarize endpoint for processing raw transcripts.
"""

from src.shared.base_endpoint import BaseEndpoint
from src.shared.pipeline_definitions import EndpointResponse, PipelineStages, PipelineState
from src.shared.data_loaders import DataLoader
from src.summarize.pipeline import summarize_content
from src.summarize.config import summarization_config
from src.summarize.models import SummarizeContext, SummarizationResult


class SummarizeEndpoint(BaseEndpoint):
    """Endpoint for summarizing raw transcripts."""
    
    def __init__(self) -> None:
        super().__init__("SummarizeEndpoint")
    
    def execute(self, state: PipelineState) -> EndpointResponse:
        """Execute the summarization process for a single item."""
        content = DataLoader.load_content_input(state, PipelineStages.SCRAPE)

        # Build processing context
        processing_context = SummarizeContext(
            id=state.id,
            text=content,
            target_tokens=summarization_config.TARGET_SUMMARY_TOKENS
        )

        # Execute summarization pipeline - returns StageResult
        stage_result = summarize_content(processing_context)
        
        # Parse artifact using SummarizationResult model
        summarization_result = SummarizationResult.model_validate(stage_result.artifact)
        
        return self._create_success_response(
            result=stage_result.artifact,
            stage=PipelineStages.SUMMARIZE.value,
            state_update=stage_result.metadata
        )
