"""
Base flow processor to eliminate code duplication across pipeline flows.

Provides common patterns for processing items through pipeline stages with
consistent error handling, persistence, and state management.
"""

import time
from typing import Callable, Any, Optional
from prefect import task

from tasks.orchestration import get_items
from src.shared.pipeline_definitions import PipelineStageStatus, PipelineStages, PipelineState
from src.shared.pipeline_state import PipelineStateManager
from src.shared.persistence import save_data
from src.shared.models import StageOperationResult
from src.shared.pipeline_definitions import EndpointResponse
from src.utils.logging_utils import get_logger


class FlowProcessor:
    """Base processor for pipeline flows with common patterns."""
    
    def __init__(self, flow_name: str):
        self.flow_name = flow_name
        self.logger = get_logger(flow_name)
    
    def process_items(self, stage: PipelineStages, task_func: Callable[..., Any]) -> None:
        """Process items through a pipeline stage with consistent error handling."""
        items = get_items(stage)
        self.logger.info(f"Found {len(items)} items to process for stage {stage}")
        
        manager = PipelineStateManager()
        
        for i, item in enumerate(items, 1):
            self.logger.info(f"Processing item {i}/{len(items)}: {item.id}")
            self._process_single_item(item, task_func, stage, manager)
        
        self.logger.info(f"Completed {self.flow_name} for {len(items)} items")
    
    def _process_single_item(self, state: PipelineState, task_func: Callable[..., Any],
                             stage: PipelineStages, manager: PipelineStateManager) -> None:
        """Process a single item with error handling and state management."""
        start_time = time.time()
        try:
            # Process the item with timing
            result = task_func.submit(state)
            result_data = result.result()
            
            # Add timing to result_data using model_copy for immutability
            elapsed = max(0.01, time.time() - start_time)
            result_data = result_data.model_copy(update={'processing_time_seconds': round(elapsed, 2)})
            
            # Extract id from output using StageOperationResult model
            output = StageOperationResult[Any].model_validate(result_data.output)
            id = output.id
            
            # Save the result (speaker/search_url looked up from state automatically)
            output_file = save_data(id, result_data.output, stage.value)
            
            # Update pipeline state (handles metadata via result_data.state_update)
            manager.update_stage_status(
                status=PipelineStageStatus.COMPLETED,
                result_data=result_data,
                file_path=output_file
            )
            
            self.logger.debug(f"Successfully completed {stage} for item {id} -> {output_file}")
                
        except Exception as e:
            id = state.id
            elapsed = max(0.01, time.time() - start_time)
            self.logger.error(f"Error processing item {id} in {stage}: {str(e)}", 
                             extra={'id': id, 'stage': stage, 'error_type': 'component_error', 'item_url': state.source_url})
            
            # Try to extract failed output if available (for validation errors)
            failed_output = None
            if hasattr(e, 'failed_output'):
                failed_output = e.failed_output
                if failed_output:
                    self.logger.debug(f"Extracted failed output from exception for {id} - storing in pipeline state")
            
            # Create error result using StageOperationResult model
            error_output = StageOperationResult[Any](
                id=id,
                success=False,
                data=None,
                error_message=str(e)
            )
            
            # Include failed_output if available (not part of StageOperationResult model)
            output_dict = error_output.model_dump()
            if failed_output:
                output_dict['failed_output'] = failed_output
            
            error_result = EndpointResponse(
                success=True,
                stage=stage,
                output=output_dict,
                processing_time_seconds=round(elapsed, 2)
            )
            
            # Update state to failed
            manager.update_stage_status(
                status=PipelineStageStatus.FAILED,
                result_data=error_result
            )
