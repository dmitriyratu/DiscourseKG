"""
Categorize endpoint for processing summarized content.
"""

from typing import Dict, Any

from src.shared.base_endpoint import BaseEndpoint
from src.shared.data_loaders import DataLoader
from src.categorize.pipeline import categorize_content
from src.categorize.models import CategorizationInput, CategorizeItem, CategorizeContext
from src.shared.pipeline_definitions import PipelineStages


class CategorizeEndpoint(BaseEndpoint):
    """Endpoint for categorizing summarized content."""
    
    def __init__(self):
        super().__init__("CategorizeEndpoint")
    
    def execute(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the categorization process for a single item."""
        categorize_item = CategorizeItem(**item)

        # Load summary artifact
        data_loader = DataLoader()
        current_file_path = categorize_item.file_paths.get(categorize_item.latest_completed_stage)
        if not current_file_path:
            raise ValueError(
                f"No file path found for latest completed stage {categorize_item.latest_completed_stage} "
                f"for item {categorize_item.id}"
            )

        # Validate content
        summary_text = data_loader.extract_stage_output(current_file_path, PipelineStages.SUMMARIZE)
        if not summary_text or not summary_text.strip():
            raise ValueError("Empty or invalid summary content")

        # Build categorization input
        categorization_input = CategorizationInput(
            title=categorize_item.title or 'Unknown',
            content_date=categorize_item.content_date or 'Unknown',
            content=summary_text
        )

        # Build processing context
        processing_context = CategorizeContext(
            id=categorize_item.id,
            categorization_input=categorization_input,
            previous_error=categorize_item.error_message,
            previous_failed_output=categorize_item.failed_output
        )

        # Execute categorization pipeline - returns StageResult
        stage_result = categorize_content(processing_context)
        
        self.logger.debug(
            f"Successfully categorized item {categorize_item.id} - {len(stage_result.artifact['data']['entities'])} entities"
        )

        return self._create_success_response(
            result=stage_result.artifact,
            stage=PipelineStages.CATEGORIZE.value,
            state_update=stage_result.metadata
        )
