"""
Categorize endpoint for processing summarized content.
"""

from src.shared.base_endpoint import BaseEndpoint
from src.shared.pipeline_definitions import EndpointResponse
from src.shared.data_loaders import DataLoader
from src.categorize.pipeline import categorize_content
from src.categorize.models import CategorizationInput, CategorizeContext, CategorizationResult
from src.shared.pipeline_definitions import PipelineStages, PipelineState


class CategorizeEndpoint(BaseEndpoint):
    """Endpoint for categorizing summarized content."""
    
    def __init__(self) -> None:
        super().__init__("CategorizeEndpoint")
    
    def execute(self, state: PipelineState) -> EndpointResponse:
        """Execute the categorization process for a single item."""
        # Load summary artifact
        data_loader = DataLoader()
        current_file_path = state.get_current_file_path()
        if not current_file_path:
            raise ValueError(
                f"No file path found for latest completed stage {state.latest_completed_stage} "
                f"for item {state.id}"
            )

        # Validate content
        summary_text = data_loader.extract_stage_output(current_file_path, PipelineStages.SUMMARIZE)
        if not summary_text or not summary_text.strip():
            raise ValueError("Empty or invalid summary content")

        # Get title and publication_date from top-level state
        title = state.title or 'Unknown'
        content_date = state.publication_date or 'Unknown'

        # Build categorization input
        categorization_input = CategorizationInput(
            title=title,
            content_date=content_date,
            content=summary_text
        )

        # Build processing context
        processing_context = CategorizeContext(
            id=state.id,
            categorization_input=categorization_input,
            previous_error=state.error_message
        )

        # Execute categorization pipeline - returns StageResult
        stage_result = categorize_content(processing_context)
        
        # Parse artifact using CategorizationResult model
        categorization_result = CategorizationResult.model_validate(stage_result.artifact)
        
        self.logger.debug(
            f"Successfully categorized item {state.id} - {len(categorization_result.data.entities)} entities"
        )

        return self._create_success_response(
            result=stage_result.artifact,
            stage=PipelineStages.CATEGORIZE.value,
            state_update=stage_result.metadata
        )
