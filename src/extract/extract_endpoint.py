"""Extract endpoint for entity-passage pre-processing."""

from src.shared.base_endpoint import BaseEndpoint
from src.shared.pipeline_definitions import EndpointResponse, PipelineStages, PipelineState
from src.shared.data_loaders import DataLoader
from src.extract.pipeline import extract_entities
from src.extract.models import ExtractContext


class ExtractEndpoint(BaseEndpoint):

    def __init__(self) -> None:
        super().__init__("ExtractEndpoint")

    def execute(self, state: PipelineState) -> EndpointResponse:
        content = DataLoader.load_content_input(state, PipelineStages.SUMMARIZE, PipelineStages.SCRAPE)

        processing_context = ExtractContext(
            id=state.id,
            content=content,
            content_type=state.content_type,
            matched_speakers=state.matched_speakers,
        )

        stage_result = extract_entities(processing_context)
        return self._success(stage_result, PipelineStages.EXTRACT)
