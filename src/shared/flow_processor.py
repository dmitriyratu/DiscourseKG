"""
Base flow processor to eliminate code duplication across pipeline flows.

Provides common patterns for processing items through pipeline stages with
consistent error handling, persistence, and state management.
"""

import time
from typing import Callable, Any

from tasks.orchestration import get_items
from src.shared.pipeline_definitions import (
    EndpointResponse,
    PipelineStageStatus,
    PipelineStages,
    PipelineState,
)
from src.shared.pipeline_state import PipelineStateManager
from src.shared.persistence import save_data
from src.shared.models import StageOperationResult
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
            result = task_func.submit(state)
            result_data = result.result()
            elapsed = max(0.01, time.time() - start_time)
            result_data = result_data.model_copy(update={'processing_time_seconds': round(elapsed, 2)})
            output = StageOperationResult[Any].model_validate(result_data.output)
            output_file = save_data(state, result_data.output, stage.value)
            
            status = result_data.pipeline_status or PipelineStageStatus.COMPLETED
            manager.record_stage_result(
                status=status,
                result_data=result_data,
                file_path=output_file
            )
            
            self.logger.debug(f"Successfully completed {stage} for item {output.id} -> {output_file}")
                
        except Exception as e:
            elapsed = max(0.01, time.time() - start_time)
            self.logger.error(f"Error processing item {state.id} in {stage}: {str(e)}")
            manager.record_stage_result(
                status=PipelineStageStatus.FAILED,
                result_data=EndpointResponse.for_error(state.id, stage.value, str(e), elapsed)
            )
