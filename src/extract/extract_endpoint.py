"""Extract endpoint for entity-passage pre-processing."""

from src.shared.base_endpoint import BaseEndpoint
from src.shared.pipeline_definitions import EndpointResponse, PipelineStages, PipelineState
from src.shared.data_loaders import DataLoader
from src.extract.pipeline import extract_entities
from src.extract.models import ExtractContext, ExtractionResult


class ExtractEndpoint(BaseEndpoint):
    """Endpoint for extracting entities and passages from content."""

    def __init__(self) -> None:
        super().__init__("ExtractEndpoint")

    def execute(self, state: PipelineState) -> EndpointResponse:
        """Execute entity extraction for a single item."""
        content = DataLoader.load_content_input(state, PipelineStages.SUMMARIZE, PipelineStages.SCRAPE)

        processing_context = ExtractContext(
            id=state.id,
            content=content,
            active_speakers=state.active_speakers,
            previous_error=state.error_message,
            previous_failed_output=state.previous_failed_output,
        )

        stage_result = extract_entities(processing_context)

        extraction_result = ExtractionResult.model_validate(stage_result.artifact)

        self.logger.debug(
            f"Extracted {len(extraction_result.data.entities)} entities for {state.id}"
        )

        return self._create_success_response(
            result=stage_result.artifact,
            stage=PipelineStages.EXTRACT.value,
            state_update=stage_result.metadata,
        )
