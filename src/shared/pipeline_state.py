"""
Pipeline state management utilities for DiscourseKG platform.

This module provides state tracking for the data processing pipeline,
following the same patterns as the existing logging utilities.
"""

import json
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime
from pydantic import BaseModel, Field

from src.config import config
from src.utils.logging_utils import get_logger
from src.pipeline_config import pipeline_config, PipelineStages, PipelineStageStatus

logger = get_logger(__name__)


class PipelineState(BaseModel):
    """Pipeline processing state for a single data point"""
    
    # Core identifiers
    id: str = Field(..., description="Unique ID from raw data (matches the 'id' field in raw JSON files)")
    run_timestamp: str = Field(..., description="Hourly timestamp when scraped (YYYY-MM-DD_HH:00:00)")
    file_paths: Dict[str, str] = Field(default_factory=dict, description="File paths for each completed stage (stage_name -> file_path)")
    
    # Content metadata
    speaker: Optional[str] = Field(None, description="Primary speaker name")
    content_type: Optional[str] = Field(None, description="Type of content (speech, debate, interview, etc.)")
    title: Optional[str] = Field(None, description="Title of the scraped content")
    content_date: Optional[str] = Field(None, description="Date when the content was created/published")
    source_url: Optional[str] = Field(None, description="Original source URL")
    
    # Simple stage tracking
    latest_completed_stage: Optional[str] = Field(None, description="Latest successfully completed stage")
    next_stage: Optional[str] = Field(..., description="Next stage that needs to be processed")
    
    # Metadata
    created_at: str = Field(..., description="ISO timestamp when record was created")
    updated_at: str = Field(..., description="ISO timestamp of last update")
    error_message: Optional[str] = Field(None, description="Error message if current stage failed")
    failed_output: Optional[str] = Field(None, description="Failed output from previous attempt (for retry context)")
    
    # Processing metrics
    processing_time_seconds: Optional[float] = Field(None, description="Total processing time across all stages")
    retry_count: int = Field(default=0, description="Number of times this record has been retried")

    def get_current_file_path(self) -> Optional[str]:
        """Get file path for the latest completed stage"""
        if self.latest_completed_stage:
            return self.file_paths.get(self.latest_completed_stage)
        return None
    
    def get_file_path_for_stage(self, stage: str) -> Optional[str]:
        """Get file path for a specific stage"""
        return self.file_paths.get(stage)


class PipelineStateManager:
    """Manages pipeline state tracking for data processing"""
    
    def __init__(self, state_file_path: str = None):
        self.state_file_path = Path(state_file_path or config.PIPELINE_STATE_FILE)
        self.state_file_path.parent.mkdir(parents=True, exist_ok=True)
    
    def create_state(self, id: str, run_timestamp: str, file_path: str = None, 
                    source_url: str = None, speaker: str = None, content_type: str = None) -> PipelineState:
        """Create a new pipeline state for a data point"""
        now = datetime.now().isoformat()
        
        # Initialize file_paths with initial file_path if provided
        file_paths = {}
        if file_path:
            file_paths[PipelineStages.DISCOVER.value] = file_path
        
        state = PipelineState(
            id=id,
            run_timestamp=run_timestamp,
            file_paths=file_paths,
            source_url=source_url,
            speaker=speaker,
            content_type=content_type,
            latest_completed_stage=PipelineStages.DISCOVER.value,
            next_stage=PipelineStages.SCRAPE.value,
            created_at=now,
            updated_at=now
        )
        
        # Append to state file
        self._append_state(state)
        logger.debug(f"Created pipeline state for data point: {id}")
        
        return state
    
    def get_by_source_url(self, source_url: str) -> Optional[PipelineState]:
        """Check if source URL already exists in pipeline"""
        states = self._read_all_states()
        for state_dict in states:
            if state_dict.get("source_url") == source_url:
                return PipelineState(**state_dict)
        return None
    
    def get_state(self, id: str) -> Optional[PipelineState]:
        """Get current state for a data point"""
        if not self.state_file_path.exists():
            return None
            
        with open(self.state_file_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    record = json.loads(line.strip())
                    if record["id"] == id:
                        return PipelineState(**record)
        return None
    
    def update_stage_status(self, id: str, stage: str, status: PipelineStageStatus, 
                           result_data: dict = None, file_path: str = None):
        """Update status of a specific stage for a data point"""
        # Read all existing states
        states = self._read_all_states()
        
        # Find and update the matching state
        updated = False
        for state_dict in states:
            if state_dict["id"] == id:
                state_dict["updated_at"] = datetime.now().isoformat()
                
                processing_time = None
                error_message = None
                failed_output = None
                if result_data:
                    processing_time = result_data.get('processing_time_seconds')
                    output = result_data.get('output', {})
                    error_message = output.get('error_message')
                    failed_output = output.get('failed_output')
                
                if processing_time:
                    if state_dict["processing_time_seconds"]:
                        state_dict["processing_time_seconds"] = round(state_dict["processing_time_seconds"] + processing_time, 2)
                    else:
                        state_dict["processing_time_seconds"] = round(processing_time, 2)
                
                # Update file_paths for the specific stage
                if file_path:
                    if "file_paths" not in state_dict:
                        state_dict["file_paths"] = {}
                    state_dict["file_paths"][stage] = file_path
                
                # Handle stage completion or failure
                if status == PipelineStageStatus.COMPLETED:
                    # Stage completed successfully - update latest_completed_stage and next_stage
                    state_dict["latest_completed_stage"] = stage
                    state_dict["next_stage"] = pipeline_config.get_next_stage(stage)
                    state_dict["error_message"] = None  # Clear any previous errors
                    state_dict["failed_output"] = None  # Clear any previous failed output
                elif status == PipelineStageStatus.FAILED:
                    # Stage failed - don't update latest_completed_stage, keep next_stage the same for retry
                    state_dict["error_message"] = error_message
                    state_dict["failed_output"] = failed_output
                    # next_stage stays the same (retry the failed stage)
                
                updated = True
                break
        
        if updated:
            # Rewrite the entire file with updated states
            self._write_all_states(states)
            if status == PipelineStageStatus.FAILED:
                logger.error(f"Stage {stage} failed for data point: {id}")
            elif status == PipelineStageStatus.COMPLETED:
                logger.debug(f"Completed {stage} for data point: {id}")
            else:
                logger.debug(f"Updated {stage} status to {status.value} for data point: {id}")
        else:
            logger.warning(f"Data point not found for update: {id}")
    
    def _update_metadata_naturally(self, id: str, **metadata):
        """Naturally update metadata fields as stages extract information"""
        states = self._read_all_states()
        
        for state_dict in states:
            if state_dict["id"] == id:
                state_dict["updated_at"] = datetime.now().isoformat()
                
                # Update any provided metadata fields (only if they exist in PipelineState schema)
                valid_fields = set(PipelineState.model_fields.keys())
                updated_fields = []
                
                for field, value in metadata.items():
                    if field in valid_fields and value is not None:
                        state_dict[field] = value
                        updated_fields.append(field)
                
                if updated_fields:
                    self._write_all_states(states)
                    logger.debug(f"Naturally updated metadata for {id}: {updated_fields}")
                else:
                    logger.debug(f"No valid metadata fields to update for {id}: {list(metadata.keys())}")
                return
        
        logger.warning(f"Data point not found for natural metadata update: {id}")
    
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

