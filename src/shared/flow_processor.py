"""
Base flow processor to eliminate code duplication across pipeline flows.

Provides common patterns for processing items through pipeline stages with
consistent error handling, persistence, and state management.
"""

import time
from typing import Dict, Any, Callable
from prefect import task

from tasks.orchestration import get_items
from src.pipeline_config import PipelineStageStatus, PipelineStages
from src.shared.pipeline_state import PipelineStateManager
from src.shared.persistence import save_data
from src.utils.logging_utils import get_logger


class FlowProcessor:
    """Base processor for pipeline flows with common patterns."""
    
    def __init__(self, flow_name: str):
        self.flow_name = flow_name
        self.logger = get_logger(flow_name)
    
    def process_items(self, stage: str, task_func: Callable, data_type: str):
        """Process items through a pipeline stage with consistent error handling."""
        items = get_items(stage)
        self.logger.info(f"Found {len(items)} items to process for stage {stage}")
        
        manager = PipelineStateManager()
        
        for i, item in enumerate(items, 1):
            self.logger.info(f"Processing item {i}/{len(items)}: {item.get('id', 'unknown')}")
            self._process_single_item(item, task_func, stage, data_type, manager)
        
        self.logger.info(f"Completed {self.flow_name} for {len(items)} items")
    
    def _process_single_item(self, item: Dict[str, Any], task_func: Callable, 
                           stage: str, data_type: str, manager: PipelineStateManager):
        """Process a single item with error handling and state management."""
        try:
            # Process the item with timing
            start_time = time.time()
            result = task_func.submit(item)
            result_data = result.result()
            
            # Add timing to result_data
            elapsed = max(0.01, time.time() - start_time)
            result_data['processing_time_seconds'] = round(elapsed, 2)
            
            # Extract metadata from pipeline state
            speaker = item.get('speaker')
            content_type = item.get('content_type', 'unknown')
            
            # Save the result
            output_file = save_data(
                result_data['id'], 
                result_data['result'],  # Save the complete result including id field
                data_type, 
                speaker=speaker,
                content_type=content_type
            )
            
            # Update pipeline state
            manager.update_stage_status(
                result_data['id'], 
                stage, 
                PipelineStageStatus.COMPLETED,
                result_data=result_data,
                file_path=output_file
            )
            
            self.logger.debug(f"Successfully completed {stage} for item {result_data['id']} -> {output_file}")
                
        except Exception as e:
            id = item.get('id', 'unknown')
            self.logger.error(f"Error processing item {id} in {stage}: {str(e)}", 
                             extra={'item_id': id, 'stage': stage, 'error_type': 'component_error', 'item_url': item.get('source_url')})
            
            # Create error result for pipeline state (consistent with endpoint structure)
            error_result = {
                'success': True,
                'id': id,
                'stage': stage,
                'result': {
                    'id': id,
                    'success': False,
                    'data': None,
                    'error_message': str(e)
                },
                'processing_time_seconds': round(time.time() - start_time, 2) if 'start_time' in locals() else 0.01
            }
            
            # Update state to failed
            manager.update_stage_status(
                id, 
                stage, 
                PipelineStageStatus.FAILED,
                result_data=error_result
            )
