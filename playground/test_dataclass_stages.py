#!/usr/bin/env python3
"""
Test script for dataclass-based pipeline stages.

This demonstrates the clean dataclass approach with proper stage names.
"""

# %%
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from pipeline.config import pipeline_config, pipeline_stages
from pipeline.pipeline_state import PipelineStateManager
from src.schemas import PipelineStageStatus

# %%
print("=" * 60)
print("DATACLASS PIPELINE STAGES TEST")
print("=" * 60)

# %%
print("\n[INFO] Pipeline stages from dataclass:")
print(f"✅ Raw stage: {pipeline_stages.RAW}")
print(f"✅ Summarize stage: {pipeline_stages.SUMMARIZE}")
print(f"✅ Categorize stage: {pipeline_stages.CATEGORIZE}")

print("\n[INFO] Stage flow:")
print(f"✅ Stage flow: {pipeline_config.STAGE_FLOW}")
print(f"✅ First processing stage: {pipeline_config.FIRST_PROCESSING_STAGE}")

# %%
print("\n[INFO] Testing stage flow:")
print(f"✅ After '{pipeline_stages.RAW}' comes: {pipeline_config.get_next_stage(pipeline_stages.RAW)}")
print(f"✅ After '{pipeline_stages.SUMMARIZE}' comes: {pipeline_config.get_next_stage(pipeline_stages.SUMMARIZE)}")
print(f"✅ After '{pipeline_stages.CATEGORIZE}' comes: {pipeline_config.get_next_stage(pipeline_stages.CATEGORIZE)}")

# %%
print("\n[INFO] Testing with PipelineStateManager:")
manager = PipelineStateManager()

# Create a test state
test_state = manager.create_state("dataclass_test", "2025-01-15_18:00:00")
print(f"✅ Created test state: {test_state.id}")
print(f"   Next stage: {test_state.next_stage}")

# Show all stages
print(f"✅ Manager stage order: {manager.get_stage_order()}")

# %%
print("\n[INFO] Simulating pipeline flow:")
current_stage = test_state.next_stage
while current_stage:
    print(f"📝 Processing stage: {current_stage}")
    
    # Complete the stage
    manager.update_stage_status(
        test_state.id, current_stage, PipelineStageStatus.COMPLETED
    )
    
    # Get updated state
    updated_state = manager.get_state(test_state.id)
    current_stage = updated_state.next_stage
    
    print(f"   ✅ Completed! Next stage: {current_stage}")

print(f"🎉 Pipeline complete: {manager.is_pipeline_complete(updated_state)}")

# %%
print("\n[INFO] Testing worker queries:")
summarize_tasks = manager.get_next_stage_tasks(pipeline_stages.SUMMARIZE)
categorize_tasks = manager.get_next_stage_tasks(pipeline_stages.CATEGORIZE)

print(f"✅ Tasks for {pipeline_stages.SUMMARIZE}: {len(summarize_tasks)}")
print(f"✅ Tasks for {pipeline_stages.CATEGORIZE}: {len(categorize_tasks)}")

# %%
print("\n" + "=" * 60)
print("DATACLASS STAGES TEST COMPLETED")
print("=" * 60)

print("\n[BENEFITS]")
print("✅ No hard-coded strings")
print("✅ Proper verb stage names (summarize, categorize)")
print("✅ Type-safe stage references")
print("✅ Easy to extend with new stages")
print("✅ Clear stage definitions")

print("\n[EXAMPLE WORKER CODE]")
print("""
from pipeline.config import pipeline_stages

def summarize_worker():
    tasks = manager.get_next_stage_tasks(pipeline_stages.SUMMARIZE)
    for task in tasks:
        # Process the task
        manager.update_stage_status(task.id, pipeline_stages.SUMMARIZE, PipelineStageStatus.COMPLETED)

def categorize_worker():
    tasks = manager.get_next_stage_tasks(pipeline_stages.CATEGORIZE)
    for task in tasks:
        # Process the task
        manager.update_stage_status(task.id, pipeline_stages.CATEGORIZE, PipelineStageStatus.COMPLETED)
""")
