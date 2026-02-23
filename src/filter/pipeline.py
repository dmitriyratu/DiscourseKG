"""Filter pipeline component for DiscourseKG platform."""

from src.filter.filterer import Filterer
from src.filter.models import FilterContext
from src.shared.pipeline_definitions import StageResult


def filter_content(processing_context: FilterContext) -> StageResult:
    """Filter content by identifying active tracked speakers."""
    return Filterer().filter_content(processing_context)
