"""
Categorization pipeline component for DiscourseKG platform.

Simple categorization function that will be called by an orchestrator.
"""

from src.categorize.categorizer import Categorizer
from src.categorize.models import CategorizeContext
from src.shared.pipeline_definitions import StageResult


def categorize_content(processing_context: CategorizeContext) -> StageResult:
    """Categorize content data."""
    return Categorizer().categorize_content(processing_context)
