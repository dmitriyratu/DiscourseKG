from prefect import flow
from pathlib import Path
import json
from datetime import datetime
from tasks.orchestration import get_items, process_item
from src.shared.config import pipeline_stages
from src.shared.pipeline_state import PipelineStateManager
from src.schemas import PipelineStageStatus
from src.config import config
from src.shared.logging_utils import setup_logger

logger = setup_logger("processing_flow", "processing_flow.log")


def save_categorization(item_id: str, categorization_result: dict) -> str:
    """Save categorization to processed/categories/ directory."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"categorized_{item_id}_{timestamp}.json"
    file_path = Path(config.PROCESSED_DATA_PATH) / "categories" / filename
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Simple structure - just the essential data
    data = {
        "id": item_id,
        "categorization": categorization_result,
        "processed_at": datetime.now().isoformat()
    }
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved categorization to {file_path}")
    return str(file_path)


@flow
def processing_flow():
    """Process items through categorization stage."""
    items = get_items(pipeline_stages.CATEGORIZE)
    logger.info(f"Found {len(items)} items to categorize")
    
    manager = PipelineStateManager()
    
    for item in items:
        # Process the item
        result = process_item.submit(item, pipeline_stages.CATEGORIZE)
        
        # Wait for result and handle persistence/state updates
        if result.result()['success']:
            # Save the categorization
            output_file = save_categorization(
                result.result()['item_id'],
                result.result()['result']
            )
            
            # Update pipeline state
            manager.update_stage_status(
                result.result()['item_id'], 
                pipeline_stages.CATEGORIZE, 
                PipelineStageStatus.COMPLETED
            )
            
            logger.info(f"Completed categorization for item {result.result()['item_id']} -> {output_file}")
        else:
            # Handle failure
            manager.update_stage_status(
                result.result()['item_id'], 
                pipeline_stages.CATEGORIZE, 
                PipelineStageStatus.FAILED,
                error_message=result.result()['error']
            )
            logger.error(f"Failed categorization for item {result.result()['item_id']}: {result.result()['error']}")
    
    logger.info(f"Completed processing flow for {len(items)} items")
