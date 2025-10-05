#!/usr/bin/env python3
"""
Test script showing the configurable stage flow.

This demonstrates how easy it is to modify the pipeline stages.
"""

# %%
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from src.utils.pipeline_state import PipelineStateManager
from src.schemas import PipelineStageStatus

# %%
print("=" * 60)
print("CONFIGURABLE STAGE FLOW TEST")
print("=" * 60)

# %%
print("\n[INFO] Current stage configuration:")
manager = PipelineStateManager()

print(f"✅ First stage: {manager.FIRST_STAGE}")
print(f"✅ Stage flow: {manager.STAGE_FLOW}")
print(f"✅ Stage order: {manager.get_stage_order()}")

# %%
print("\n[INFO] Testing stage flow methods:")

# Test getting next stage
print(f"✅ After 'summarized' comes: {manager.get_next_stage('summarized')}")
print(f"✅ After 'categorized' comes: {manager.get_next_stage('categorized')}")
print(f"✅ After 'analyzed' comes: {manager.get_next_stage('analyzed')}")

# %%
print("\n[INFO] Example: How to modify stages for different pipelines:")

print("""
# Example 1: Simple 2-stage pipeline
class SimplePipelineManager(PipelineStateManager):
    STAGE_FLOW = {
        "summarized": "categorized",
        "categorized": None  # Stop after categorization
    }
    FIRST_STAGE = "summarized"

# Example 2: Different order
class ReorderedPipelineManager(PipelineStateManager):
    STAGE_FLOW = {
        "categorized": "summarized", 
        "summarized": "analyzed",
        "analyzed": None
    }
    FIRST_STAGE = "categorized"

# Example 3: More stages
class ExtendedPipelineManager(PipelineStateManager):
    STAGE_FLOW = {
        "summarized": "categorized",
        "categorized": "sentiment",
        "sentiment": "analyzed", 
        "analyzed": "exported",
        "exported": None
    }
    FIRST_STAGE = "summarized"
""")

# %%
print("\n[INFO] Testing with current configuration:")

# Create a test state
test_state = manager.create_state("config_test", "2025-01-15_16:00:00")
print(f"✅ Created test state: {test_state.id}")
print(f"   Next stage: {test_state.next_stage}")

# Simulate going through the pipeline
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

print(f"🎉 Pipeline complete! Final state: {manager.is_pipeline_complete(updated_state)}")

# %%
print("\n" + "=" * 60)
print("CONFIGURABLE STAGES TEST COMPLETED")
print("=" * 60)

print("\n[BENEFITS]")
print("✅ Easy to modify stage order")
print("✅ Easy to add/remove stages") 
print("✅ Clear stage flow definition")
print("✅ No hard-coded stage names")
print("✅ Subclassable for different pipelines")
