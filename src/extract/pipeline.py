"""Extraction pipeline component for DiscourseKG platform."""

from src.extract.extractor import Extractor
from src.extract.models import ExtractContext
from src.shared.pipeline_definitions import StageResult


def extract_entities(processing_context: ExtractContext) -> StageResult:
    """Extract entities and passages from content."""
    return Extractor().extract_entities(processing_context)
