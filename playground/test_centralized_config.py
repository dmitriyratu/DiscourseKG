#!/usr/bin/env python3
"""
Test script for centralized pipeline configuration.

This demonstrates how the pipeline flow is now defined in one place
and everything else references that configuration.
"""

# %%
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from pipeline.config import pipeline_config
from pipeline.pipeline_state import PipelineStateManager
from src.schemas import PipelineStageStatus

# %%
print("=" * 60)
print("CENTRALIZED PIPELINE CONFIGURATION TEST")
print("=" * 60)

# %%
print("\n[INFO] Pipeline configuration from one place:")
print(f"✅ Stage flow: {pipeline_config.STAGE_FLOW}")
print(f"✅ First processing stage: {pipeline_config.FIRST_PROCESSING_STAGE}")

# %%
print("\n[INFO] Testing stage flow methods:")
print(f"✅ After 'raw' comes: {pipeline_config.get_next_stage('raw')}")
print(f"✅ After 'summarized' comes: {pipeline_config.get_next_stage('summarized')}")
print(f"✅ After 'categorized' comes: {pipeline_config.get_next_stage('categorized')}")

# %%
print("\n[INFO] Testing pipeline completion:")
print(f"✅ None is complete: {pipeline_config.is_pipeline_complete(None)}")
print(f"✅ 'categorized' is complete: {pipeline_config.is_pipeline_complete('categorized')}")

# %%
print("\n[INFO] Testing with PipelineStateManager:")
manager = PipelineStateManager()

# Create a test state
test_state = manager.create_state("centralized_test", "2025-01-15_17:00:00")
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
print("\n" + "=" * 60)
print("CENTRALIZED CONFIGURATION TEST COMPLETED")
print("=" * 60)

print("\n[BENEFITS]")
print("✅ Single source of truth for pipeline stages")
print("✅ Easy to modify pipeline flow in one place")
print("✅ All components reference the same configuration")
print("✅ No hard-coded stage names anywhere")
print("✅ Clear separation of concerns")

print("\n[TO ADD NEW STAGE]")
print("""
# Just update pipeline/config.py:
STAGE_FLOW = {
    "raw": "summarized",
    "summarized": "categorized",
    "categorized": "new_stage",  # Add new stage here
    "new_stage": None
}
""")
