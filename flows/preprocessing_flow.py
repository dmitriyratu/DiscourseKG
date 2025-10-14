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

logger = setup_logger("preprocessing_flow", "preprocessing_flow.log")


def save_summary(item_id: str, summary_result) -> str:
    """Save summary to processed/summaries/ directory."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"summary_{item_id}_{timestamp}.json"
    file_path = Path(config.PROCESSED_DATA_PATH) / "summaries" / filename
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Simple structure - just the essential data
    data = {
        "id": item_id,
        "summary_text": summary_result.summary,
        "processed_at": datetime.now().isoformat()
    }
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved summary to {file_path}")
    return str(file_path)


@flow
def preprocessing_flow():
    """Process items through preprocessing stage."""
    items = get_items(pipeline_stages.SUMMARIZE)
    logger.info(f"Found {len(items)} items to summarize")
    
    manager = PipelineStateManager()
    
    for item in items:
        # Process the item
        result = process_item.submit(item, pipeline_stages.SUMMARIZE)
        
        # Wait for result and handle persistence/state updates
        if result.result()['success']:
            # Save the summary
            output_file = save_summary(
                result.result()['item_id'],
                result.result()['result']
            )
            
            # Update pipeline state
            manager.update_stage_status(
                result.result()['item_id'], 
                pipeline_stages.SUMMARIZE, 
                PipelineStageStatus.COMPLETED
            )
            
            logger.info(f"Completed summarization for item {result.result()['item_id']} -> {output_file}")
        else:
            # Handle failure
            manager.update_stage_status(
                result.result()['item_id'], 
                pipeline_stages.SUMMARIZE, 
                PipelineStageStatus.FAILED,
                error_message=result.result()['error']
            )
            logger.error(f"Failed summarization for item {result.result()['item_id']}: {result.result()['error']}")
    
    logger.info(f"Completed preprocessing flow for {len(items)} items")
