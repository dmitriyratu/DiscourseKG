"""Categorize endpoint for processing extracted entity data."""

from src.shared.base_endpoint import BaseEndpoint
from src.shared.data_loaders import DataLoader
from src.shared.pipeline_definitions import EndpointResponse, PipelineStages, PipelineState
from src.categorize.pipeline import categorize_content
from src.categorize.models import (
    CategorizationInput, CategorizeContext, CategorizationResult, ExtractedEntityInput,
)
from src.extract.models import ExtractionResult


class CategorizeEndpoint(BaseEndpoint):
    """Endpoint for categorizing extracted entity data."""

    def __init__(self) -> None:
        super().__init__("CategorizeEndpoint")

    def execute(self, state: PipelineState) -> EndpointResponse:
        """Execute the categorization process for a single item."""
        entities = self._load_extracted_entities(state)

        categorization_input = CategorizationInput(
            title=state.title,
            content_date=state.publication_date,
            entities=entities,
            matched_speakers=state.matched_speakers,
        )
        processing_context = CategorizeContext(
            id=state.id,
            categorization_input=categorization_input,
            previous_error=state.error_message,
            previous_failed_output=state.previous_failed_output,
        )

        stage_result = categorize_content(processing_context)

        categorization_result = CategorizationResult.model_validate(stage_result.artifact)

        self.logger.debug(
            f"Successfully categorized item {state.id} - {len(categorization_result.data.entities)} entities"
        )

        return self._create_success_response(
            result=stage_result.artifact,
            stage=PipelineStages.CATEGORIZE.value,
            state_update=stage_result.metadata,
        )

    def _load_extracted_entities(self, state: PipelineState) -> list[ExtractedEntityInput]:
        """Load entities from the extract stage output."""
        extract_path = state.get_file_path_for_stage(PipelineStages.EXTRACT.value)
        if not extract_path:
            raise ValueError(f"No extract stage output found for {state.id}")

        output = DataLoader.load(extract_path)
        result = ExtractionResult.model_validate(output)
        if not result.data or not result.data.entities:
            raise ValueError(f"No entities found in extract output for {state.id}")

        return [
            ExtractedEntityInput(entity_name=e.entity_name, passages=e.passages)
            for e in result.data.entities
        ]
