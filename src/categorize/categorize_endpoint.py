"""Categorize endpoint for processing extracted entity data."""

from src.shared.base_endpoint import BaseEndpoint
from src.shared.data_loaders import DataLoader
from src.shared.pipeline_definitions import EndpointResponse, PipelineStages, PipelineState
from src.categorize.pipeline import categorize_content
from src.categorize.models import CategorizationInput, CategorizeContext, CategorizationResult
from src.extract.models import ExtractionResult


class CategorizeEndpoint(BaseEndpoint):

    def __init__(self) -> None:
        super().__init__("CategorizeEndpoint")

    def execute(self, state: PipelineState) -> EndpointResponse:
        passages = self._load_passages(state)

        categorization_input = CategorizationInput(
            title=state.title,
            content_date=state.publication_date,
            passages=passages,
            matched_speakers=state.matched_speakers,
        )
        processing_context = CategorizeContext(
            id=state.id,
            categorization_input=categorization_input,
        )

        stage_result = categorize_content(processing_context)
        categorization_result = CategorizationResult.model_validate(stage_result.artifact)

        self.logger.debug(
            f"Successfully categorized item {state.id} - {len(categorization_result.data.entities)} entities"
        )
        return self._success(stage_result, PipelineStages.CATEGORIZE)

    def _load_passages(self, state: PipelineState) -> list[dict]:
        """Traverse extract by_speaker and build flat passage list (0-indexed)."""
        extract_path = state.get_file_path_for_stage(PipelineStages.EXTRACT.value)
        if not extract_path:
            raise ValueError(f"No extract stage output found for {state.id}")
        result = ExtractionResult.model_validate(DataLoader.load(extract_path))
        if not result.data or not result.data.by_speaker:
            raise ValueError(f"No entities found in extract output for {state.id}")
        return [
            {"entity_name": e, "speaker": s, "verbatim": p.verbatim}
            for s, entities in result.data.by_speaker.items()
            for e, passages in entities.items()
            for p in passages
        ]
