from prefect import task
from pathlib import Path
import json
from pipeline.pipeline_state import PipelineStateManager
from pipeline.config import pipeline_stages
from pipeline.preprocessing_pipeline import preprocess_content
from pipeline.processing_pipeline import process_content
from src.schemas import PipelineStageStatus


def get_items(stage: str):
    """Get items needing processing for a stage."""
    manager = PipelineStateManager()
    items = manager.get_next_stage_tasks(stage)
    return [item.model_dump() for item in items]


def load_raw_data(raw_file_path: str) -> dict:
    """Load raw data from JSON file."""
    with open(raw_file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


@task
def process_item(item, stage: str):
    """Process one item through a stage."""
    try:
        # Load raw data file
        raw_data = load_raw_data(item['raw_file_path'])
        
        if stage == pipeline_stages.SUMMARIZE:
            result = preprocess_content(raw_data['transcript'], 1000)
        elif stage == pipeline_stages.CATEGORIZE:
            result = process_content(raw_data)
        
        manager = PipelineStateManager()
        manager.update_stage_status(item['id'], stage, PipelineStageStatus.COMPLETED)
        return {'success': True, 'item_id': item['id']}
        
    except Exception as e:
        manager = PipelineStateManager()
        manager.update_stage_status(item['id'], stage, PipelineStageStatus.FAILED, error_message=str(e))
        return {'success': False, 'item_id': item['id'], 'error': str(e)}
