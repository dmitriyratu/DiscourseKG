"""
Pipeline state management utilities for KG-Sentiment platform.

This module provides state tracking for the data processing pipeline,
following the same patterns as the existing logging utilities.
"""

import json
from pathlib import Path
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

from src.app_config import config
from src.shared.logging_utils import get_logger
from src.pipeline_config import pipeline_config, pipeline_stages, PipelineStageStatus

logger = get_logger(__name__)


class PipelineState(BaseModel):
    """Pipeline processing state for a single data point"""
    
    # Core identifiers
    id: str = Field(..., description="Unique ID from raw data (matches the 'id' field in raw JSON files)")
    scrape_cycle: str = Field(..., description="Hourly timestamp when scraped (YYYY-MM-DD_HH:00:00)")
    raw_file_path: Optional[str] = Field(None, description="Path to raw JSON file (relative to project root)")
    source_url: Optional[str] = Field(None, description="Original source URL (for deduplication and audit trail)")
    
    # Simple stage tracking
    latest_completed_stage: Optional[str] = Field(None, description="Latest successfully completed stage (None, 'raw', 'summarize', 'categorize')")
    next_stage: Optional[str] = Field(..., description="Next stage that needs to be processed")
    
    # Metadata
    created_at: str = Field(..., description="ISO timestamp when record was created")
    updated_at: str = Field(..., description="ISO timestamp of last update")
    error_message: Optional[str] = Field(None, description="Error message if current stage failed")
    
    # Processing metrics
    processing_time_seconds: Optional[float] = Field(None, description="Total processing time across all stages")
    retry_count: int = Field(default=0, description="Number of times this record has been retried")


class PipelineStateManager:
    """Manages pipeline state tracking for data processing"""
    
    def __init__(self, state_file_path: str = None):
        self.state_file_path = Path(state_file_path or config.PIPELINE_STATE_FILE)
        self.state_file_path.parent.mkdir(parents=True, exist_ok=True)
    
    def create_state(self, data_point_id: str, scrape_cycle: str, raw_file_path: str = None, 
                    source_url: str = None) -> PipelineState:
        """Create a new pipeline state for a data point"""
        now = datetime.now().isoformat()
        
        state = PipelineState(
            id=data_point_id,
            scrape_cycle=scrape_cycle,
            raw_file_path=raw_file_path,
            source_url=source_url,
            latest_completed_stage=pipeline_stages.RAW,
            next_stage=pipeline_config.FIRST_PROCESSING_STAGE,
            created_at=now,
            updated_at=now
        )
        
        # Append to state file
        self._append_state(state)
        logger.info(f"Created pipeline state for data point: {data_point_id}")
        
        return state
    
    def get_by_source_url(self, source_url: str) -> Optional[PipelineState]:
        """Check if source URL already exists in pipeline"""
        states = self._read_all_states()
        for state_dict in states:
            if state_dict.get("source_url") == source_url:
                return PipelineState(**state_dict)
        return None
    
    def get_state(self, data_point_id: str) -> Optional[PipelineState]:
        """Get current state for a data point"""
        if not self.state_file_path.exists():
            return None
            
        with open(self.state_file_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    record = json.loads(line.strip())
                    if record["id"] == data_point_id:
                        return PipelineState(**record)
        return None
    
    def update_stage_status(self, data_point_id: str, stage: str, status: PipelineStageStatus, 
                           error_message: str = None, processing_time: float = None):
        """Update status of a specific stage for a data point"""
        # Read all existing states
        states = self._read_all_states()
        
        # Find and update the matching state
        updated = False
        for state_dict in states:
            if state_dict["id"] == data_point_id:
                state_dict["updated_at"] = datetime.now().isoformat()
                
                if processing_time:
                    if state_dict["processing_time_seconds"]:
                        state_dict["processing_time_seconds"] += processing_time
                    else:
                        state_dict["processing_time_seconds"] = processing_time
                
                # Handle stage completion or failure
                if status == PipelineStageStatus.COMPLETED:
                    # Stage completed successfully - update latest_completed_stage and next_stage
                    state_dict["latest_completed_stage"] = stage
                    state_dict["next_stage"] = pipeline_config.get_next_stage(stage)
                    state_dict["error_message"] = None  # Clear any previous errors
                elif status == PipelineStageStatus.FAILED:
                    # Stage failed - don't update latest_completed_stage, keep next_stage the same for retry
                    state_dict["error_message"] = error_message
                    # next_stage stays the same (retry the failed stage)
                
                updated = True
                break
        
        if updated:
            # Rewrite the entire file with updated states
            self._write_all_states(states)
            logger.info(f"Updated {stage} status to {status.value} for data point: {data_point_id}")
        else:
            logger.warning(f"Data point not found for update: {data_point_id}")
    
    def get_next_stage_tasks(self, stage: str) -> List[PipelineState]:
        """Get all data points where the next_stage matches the requested stage"""
        tasks = []
        states = self._read_all_states()
        
        for state_dict in states:
            if state_dict.get("next_stage") == stage:
                tasks.append(PipelineState(**state_dict))
        
        return tasks
    
    def get_failed_tasks(self) -> List[PipelineState]:
        """Get all data points that have failed (have error_message)"""
        failed = []
        states = self._read_all_states()
        
        for state_dict in states:
            if state_dict.get("error_message"):
                failed.append(PipelineState(**state_dict))
        
        return failed
    
    
    def _append_state(self, state: PipelineState):
        """Append a new state to the file"""
        with open(self.state_file_path, "a", encoding="utf-8") as f:
            f.write(state.model_dump_json() + "\n")
    
    def _read_all_states(self) -> List[dict]:
        """Read all states from the file"""
        states = []
        if not self.state_file_path.exists():
            return states
            
        with open(self.state_file_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    states.append(json.loads(line.strip()))
        
        return states
    
    def _write_all_states(self, states: List[dict]):
        """Write all states to the file"""
        with open(self.state_file_path, "w", encoding="utf-8") as f:
            for state_dict in states:
                f.write(json.dumps(state_dict) + "\n")
    
    
