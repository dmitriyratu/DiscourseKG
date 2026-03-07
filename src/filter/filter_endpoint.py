"""Filter endpoint for identifying tracked speakers in scraped content."""

from src.filter.models import FilterContext, FilterResult
from src.filter.pipeline import filter_content
from src.shared.base_endpoint import BaseEndpoint
from src.shared.data_loaders import DataLoader
from src.shared.pipeline_definitions import EndpointResponse, PipelineStageStatus, PipelineStages, PipelineState
from src.speakers.registry import get_display_name_to_id


class FilterEndpoint(BaseEndpoint):
    """Endpoint for filtering content by tracked speaker presence."""

    def __init__(self) -> None:
        super().__init__("FilterEndpoint")

    def execute(self, state: PipelineState) -> EndpointResponse:
        """Execute the filter process for a single item."""
        content = DataLoader.load_content_input(state, PipelineStages.SCRAPE)

        display_name_to_id = get_display_name_to_id()
        context = FilterContext(
            id=state.id,
            title=state.title,
            content=content,
            tracked_speaker_hints=list(display_name_to_id.keys()),
            display_name_to_id=display_name_to_id,
        )

        stage_result = filter_content(context)
        filter_result = FilterResult.model_validate(stage_result.artifact)

        self.logger.debug(
            f"Filter result for {state.id}: is_relevant={filter_result.data.is_relevant}, "
            f"matched={filter_result.data.matched_speakers}"
        )

        status = PipelineStageStatus.COMPLETED if filter_result.data.is_relevant else PipelineStageStatus.FILTERED
        return self._create_success_response(
            result=stage_result.artifact,
            stage=PipelineStages.FILTER.value,
            state_update=stage_result.metadata,
            pipeline_status=status,
        )
