"""
Base flow processor to eliminate code duplication across pipeline flows.

Provides common patterns for processing items through pipeline stages with
consistent error handling, persistence, and state management.
"""

from typing import Dict, Any, Callable
from prefect import task

from tasks.orchestration import get_items
from src.pipeline_config import pipeline_stages, PipelineStageStatus
from src.shared.pipeline_state import PipelineStateManager
from src.shared.persistence import save_data
from src.shared.logging_utils import get_logger


class FlowProcessor:
    """Base processor for pipeline flows with common patterns."""
    
    def __init__(self, flow_name: str):
        self.flow_name = flow_name
        self.logger = get_logger(flow_name)
    
    def process_items(self, stage: str, task_func: Callable, data_type: str):
        """
        Process items through a pipeline stage with consistent error handling.
        
        Args:
            stage: Pipeline stage name (e.g., 'summarize', 'categorize')
            task_func: Prefect task function to execute
            data_type: Data type for persistence (e.g., 'summary', 'categorization')
        """
        items = get_items(stage)
        self.logger.info(f"Found {len(items)} items to process for stage {stage}")
        
        manager = PipelineStateManager()
        
        for item in items:
            self._process_single_item(item, task_func, stage, data_type, manager)
        
        self.logger.info(f"Completed {self.flow_name} for {len(items)} items")
    
    def _process_single_item(self, item: Dict[str, Any], task_func: Callable, 
                           stage: str, data_type: str, manager: PipelineStateManager):
        """Process a single item with error handling and state management."""
        try:
            # Process the item
            result = task_func.submit(item)
            result_data = result.result()
            
            if result_data['success']:
                # Save the result
                output_file = save_data(result_data['item_id'], result_data['result'], data_type)
                
                # Update pipeline state
                manager.update_stage_status(
                    result_data['item_id'], 
                    stage, 
                    PipelineStageStatus.COMPLETED
                )
                
                self.logger.info(f"Completed {stage} for item {result_data['item_id']} -> {output_file}")
            else:
                # Handle failure
                manager.update_stage_status(
                    result_data['item_id'], 
                    stage, 
                    PipelineStageStatus.FAILED,
                    error_message=result_data['error']
                )
                self.logger.error(f"Failed {stage} for item {result_data['item_id']}: {result_data['error']}")
                
        except Exception as e:
            item_id = item.get('id', 'unknown')
            self.logger.error(f"Unexpected error processing item {item_id} in {stage}: {str(e)}")
            
            # Update state to failed
            manager.update_stage_status(
                item_id, 
                stage, 
                PipelineStageStatus.FAILED,
                error_message=str(e)
            )
