"""
Summarize endpoint for processing raw transcripts.
"""

from src.shared.base_endpoint import BaseEndpoint
from src.shared.pipeline_definitions import EndpointResponse
from src.shared.data_loaders import DataLoader
from src.summarize.pipeline import summarize_content
from src.summarize.config import summarization_config
from src.shared.pipeline_definitions import PipelineStages, PipelineState
from src.summarize.models import SummarizeContext, SummarizationResult


class SummarizeEndpoint(BaseEndpoint):
    """Endpoint for summarizing raw transcripts."""
    
    def __init__(self) -> None:
        super().__init__("SummarizeEndpoint")
    
    def execute(self, state: PipelineState) -> EndpointResponse:
        """Execute the summarization process for a single item."""
        # Load scrape artifact
        data_loader = DataLoader()
        current_file_path = state.get_current_file_path()
        if not current_file_path:
            raise ValueError(
                f"No file path found for latest completed stage {state.latest_completed_stage} "
                f"for item {state.id}"
            )

        # Validate content
        scrape = data_loader.extract_stage_output(current_file_path, PipelineStages.SCRAPE)
        if not scrape or not scrape.strip():
            raise ValueError("Empty or invalid scrape content")

        # Build processing context
        processing_context = SummarizeContext(
            id=state.id,
            text=scrape,
            target_tokens=summarization_config.TARGET_SUMMARY_TOKENS
        )

        # Execute summarization pipeline - returns StageResult
        stage_result = summarize_content(processing_context)
        
        # Parse artifact using SummarizationResult model
        summarization_result = SummarizationResult.model_validate(stage_result.artifact)
        
        self.logger.debug(
            f"Successfully summarized item {state.id} - {summarization_result.data.summary_word_count} words"
        )

        return self._create_success_response(
            result=stage_result.artifact,
            stage=PipelineStages.SUMMARIZE.value,
            state_update=stage_result.metadata
        )
