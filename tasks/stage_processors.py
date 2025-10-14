"""
Stage-specific processor tasks for the pipeline.

Each processor handles one specific stage with proper validation and error handling.
"""

from typing import Dict, Any
from prefect import task

from src.preprocessing.pipeline import preprocess_content
from src.processing.pipeline import process_content
from tasks.data_loaders import RawDataLoader, SummaryDataLoader, RawData, SummaryData
from src.shared.logging_utils import setup_logger

logger = setup_logger("stage_processors", "stage_processors.log")


@task
def summarize_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process raw data through summarization stage.
    
    Args:
        item: Pipeline state item containing raw_file_path
        
    Returns:
        Result dictionary with success status and processing result
    """
    try:
        logger.info(f"Starting summarization for item {item['id']}")
        
        # Load raw data
        raw_loader = RawDataLoader()
        raw_data = raw_loader.load(item['raw_file_path'])
        
        # Validate transcript content
        if not raw_data.transcript or not raw_data.transcript.strip():
            raise ValueError("Empty or invalid transcript content")
        
        # Process through summarization
        result = preprocess_content(raw_data.transcript, 1000)
        
        if not result.success:
            raise ValueError(f"Summarization failed: {result.error_message}")
        
        logger.info(f"Successfully summarized item {item['id']} - {result.summary_word_count} words")
        
        return {
            'success': True,
            'item_id': item['id'],
            'stage': 'summarize',
            'result': result,
            'input_data': raw_data
        }
        
    except Exception as e:
        logger.error(f"Summarization failed for item {item['id']}: {str(e)}")
        return {
            'success': False,
            'item_id': item['id'],
            'stage': 'summarize',
            'error': str(e)
        }


@task
def categorize_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process summary data through categorization stage.
    
    Args:
        item: Pipeline state item containing item ID
        
    Returns:
        Result dictionary with success status and processing result
    """
    try:
        logger.info(f"Starting categorization for item {item['id']}")
        
        # Load summary data
        summary_loader = SummaryDataLoader()
        summary_data = summary_loader.load(item['id'])
        
        # Validate summary content
        if not summary_data.summary_text or not summary_data.summary_text.strip():
            raise ValueError("Empty or invalid summary content")
        
        # Create input structure for categorization
        categorization_input = {
            "id": summary_data.id,
            "transcript": summary_data.summary_text,
            "title": f"Summary for {summary_data.id}",
            "speakers": ["Unknown"],  # TODO: Extract from original data
            "date": summary_data.processed_at or "2025-01-01"
        }
        
        # Process through categorization
        result = process_content(categorization_input)
        
        logger.info(f"Successfully categorized item {item['id']}")
        
        return {
            'success': True,
            'item_id': item['id'],
            'stage': 'categorize',
            'result': result,
            'input_data': summary_data
        }
        
    except Exception as e:
        logger.error(f"Categorization failed for item {item['id']}: {str(e)}")
        return {
            'success': False,
            'item_id': item['id'],
            'stage': 'categorize',
            'error': str(e)
        }
