"""
Pipeline state management utilities for DiscourseKG platform.

This module provides state tracking for the data processing pipeline,
following the same patterns as the existing logging utilities.
"""

import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from src.config import config
from src.utils.logging_utils import get_logger
from src.shared.pipeline_definitions import (
    PipelineConfig,
    PipelineStages,
    PipelineStageStatus,
    PipelineState,
    StageMetadata,
)
from src.shared.models import StageOperationResult
from src.shared.pipeline_definitions import EndpointResponse
from src.discover.models import DiscoveredArticle, DiscoverStageMetadata

logger = get_logger(__name__)


class PipelineStateManager:
    """Manages pipeline state tracking for data processing"""
    
    def __init__(self, state_file_path: Optional[str] = None) -> None:
        self.state_file_path = Path(state_file_path or config.PIPELINE_STATE_FILE)
        self.state_file_path.parent.mkdir(parents=True, exist_ok=True)
        self.pipeline_config = PipelineConfig()
    
    def create_state(self, discovered_article: DiscoveredArticle, run_timestamp: str,
                     file_path: Optional[str] = None, search_url: Optional[str] = None) -> PipelineState:
        """Create a new pipeline state for a discovered article"""
        now = datetime.now().isoformat()
        
        # Extract metadata from discovered article (only stage-specific fields)
        discover_metadata = DiscoverStageMetadata(
            date_score=discovered_article.date_score,
            date_source=discovered_article.date_source
        )
        
        # Initialize stages with discover stage
        discover_stage = StageMetadata(
            completed_at=now,
            file_path=file_path,
            metadata=discover_metadata.model_dump()
        )
        stages = {
            PipelineStages.DISCOVER.value: discover_stage
        }
        
        state = PipelineState(
            id=discovered_article.id,
            run_timestamp=run_timestamp,
            source_url=discovered_article.url,
            search_url=search_url,
            speaker=discovered_article.speaker,
            title=discovered_article.title,
            publication_date=discovered_article.publication_date,
            latest_completed_stage=PipelineStages.DISCOVER.value,
            next_stage=PipelineStages.SCRAPE.value,
            created_at=now,
            updated_at=now,
            stages=stages
        )
        
        self._append_state(state)
        logger.debug(f"Created pipeline state for data point: {discovered_article.id}")
        
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
    
    def update_stage_status(self, status: PipelineStageStatus, result_data: EndpointResponse, file_path: Optional[str] = None) -> None:
        """Update status of a specific stage for a data point."""
        # Derive id and stage from result_data
        stage = result_data.stage
        output = StageOperationResult[Any].model_validate(result_data.output)
        id = output.id
        
        states = self._read_all_states()
        
        updated = False
        for i, state_dict in enumerate(states):
            if state_dict["id"] == id:
                # Parse state dict into PipelineState model
                state = PipelineState(**state_dict)
                now = datetime.now().isoformat()
                state.updated_at = now
                
                # Get or create stage metadata
                if stage not in state.stages:
                    stage_meta = StageMetadata()
                else:
                    stage_meta = state.stages[stage]
                
                # Extract data from result_data
                processing_time = result_data.processing_time_seconds
                custom_metadata = result_data.state_update or {}
                error_message = output.error_message
                
                # Update stage-specific processing time
                if processing_time:
                    stage_meta.processing_time_seconds = round(processing_time, 2)
                    
                    # Update top-level total processing time
                    current_total = state.processing_time_seconds or 0
                    state.processing_time_seconds = round(current_total + processing_time, 2)
                
                # Store stage-specific custom metadata
                if custom_metadata:
                    stage_meta.metadata.update(custom_metadata)
                
                # Store error if present
                if error_message:
                    stage_meta.error_message = error_message
                    state.error_message = error_message
                
                # Update file path (nested only)
                if file_path:
                    stage_meta.file_path = file_path
                
                # Handle stage completion or failure
                if status == PipelineStageStatus.COMPLETED:
                    stage_meta.completed_at = now
                    stage_meta.error_message = None
                    state.latest_completed_stage = stage
                    state.next_stage = self.pipeline_config.get_next_stage(stage)
                    state.error_message = None
                    
                elif status == PipelineStageStatus.FAILED:
                    stage_meta.retry_count += 1
                    state.retry_count = (state.retry_count or 0) + 1
                
                # Update stages dict with modified stage_meta
                state.stages[stage] = stage_meta
                
                # Convert back to dict and replace in list
                states[i] = state.model_dump()
                
                updated = True
                break
        
        if updated:
            self._write_all_states(states)
            if status == PipelineStageStatus.FAILED:
                logger.error(f"Stage {stage} failed for data point: {id}")
            elif status == PipelineStageStatus.COMPLETED:
                logger.debug(f"Completed {stage} for data point: {id}")
        else:
            logger.warning(f"Data point not found for update: {id}")
    
    
    def get_next_stage_tasks(self, stage: PipelineStages) -> List[PipelineState]:
        """Get all data points where the next_stage matches the requested stage"""
        tasks = []
        states = self._read_all_states()
        stage_value = stage.value
        
        for state_dict in states:
            if state_dict.get("next_stage") == stage_value:
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
    
    
    def _append_state(self, state: PipelineState) -> None:
        """Append a new state to the file"""
        with open(self.state_file_path, "a", encoding="utf-8") as f:
            f.write(state.model_dump_json() + "\n")
    
    def _read_all_states(self) -> List[Dict[str, Any]]:
        """Read all states from the file"""
        states = []
        if not self.state_file_path.exists():
            return states
            
        with open(self.state_file_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    states.append(json.loads(line.strip()))
        
        return states
    
    def _write_all_states(self, states: List[Dict[str, Any]]) -> None:
        """Write all states to the file"""
        with open(self.state_file_path, "w", encoding="utf-8") as f:
            for state_dict in states:
                state = PipelineState(**state_dict)
                f.write(state.model_dump_json() + "\n")

