#!/usr/bin/env python3
"""
Test script for simplified pipeline state tracking.

This demonstrates the new approach: just track latest_completed_stage and next_stage.
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
print("SIMPLIFIED PIPELINE STATE TEST")
print("=" * 60)

# %%
print("\n[INFO] Testing simplified state tracking:")
manager = PipelineStateManager()

# Create a test state
test_state = manager.create_state("simple_test", "2025-01-15_19:00:00")
print(f"✅ Created test state: {test_state.id}")
print(f"   Latest completed: {test_state.latest_completed_stage}")
print(f"   Next stage: {test_state.next_stage}")

# %%
print("\n[INFO] Testing stage progression:")

# Complete summarize stage
print("📝 Completing summarize stage...")
manager.update_stage_status(
    test_state.id, pipeline_stages.SUMMARIZE, PipelineStageStatus.COMPLETED,
    processing_time=2.5
)

updated_state = manager.get_state(test_state.id)
print(f"   ✅ Latest completed: {updated_state.latest_completed_stage}")
print(f"   ✅ Next stage: {updated_state.next_stage}")
print(f"   ✅ Error message: {updated_state.error_message}")

# Complete categorize stage
print("\n📝 Completing categorize stage...")
manager.update_stage_status(
    test_state.id, pipeline_stages.CATEGORIZE, PipelineStageStatus.COMPLETED,
    processing_time=3.2
)

final_state = manager.get_state(test_state.id)
print(f"   ✅ Latest completed: {final_state.latest_completed_stage}")
print(f"   ✅ Next stage: {final_state.next_stage}")
print(f"   ✅ Pipeline complete: {pipeline_config.is_pipeline_complete(final_state.next_stage)}")

# %%
print("\n[INFO] Testing failure scenario:")

# Create another test state
fail_state = manager.create_state("fail_test", "2025-01-15_19:00:00")
print(f"✅ Created failure test state: {fail_state.id}")

# Try to complete summarize but fail
print("📝 Failing summarize stage...")
manager.update_stage_status(
    fail_state.id, pipeline_stages.SUMMARIZE, PipelineStageStatus.FAILED,
    error_message="OpenAI API timeout", processing_time=30.0
)

failed_state = manager.get_state(fail_state.id)
print(f"   ❌ Latest completed: {failed_state.latest_completed_stage}")
print(f"   ❌ Next stage: {failed_state.next_stage} (should be same for retry)")
print(f"   ❌ Error message: {failed_state.error_message}")

# Retry the failed stage
print("\n📝 Retrying summarize stage...")
manager.update_stage_status(
    fail_state.id, pipeline_stages.SUMMARIZE, PipelineStageStatus.COMPLETED,
    processing_time=2.8
)

retry_state = manager.get_state(fail_state.id)
print(f"   ✅ Latest completed: {retry_state.latest_completed_stage}")
print(f"   ✅ Next stage: {retry_state.next_stage}")
print(f"   ✅ Error message: {retry_state.error_message} (should be cleared)")

# %%
print("\n[INFO] Testing worker queries:")

# Create multiple test states
for i in range(3):
    manager.create_state(f"worker_test_{i}", "2025-01-15_19:00:00")

summarize_tasks = manager.get_next_stage_tasks(pipeline_stages.SUMMARIZE)
categorize_tasks = manager.get_next_stage_tasks(pipeline_stages.CATEGORIZE)
failed_tasks = manager.get_failed_tasks()

print(f"✅ Tasks for {pipeline_stages.SUMMARIZE}: {len(summarize_tasks)}")
print(f"✅ Tasks for {pipeline_stages.CATEGORIZE}: {len(categorize_tasks)}")
print(f"✅ Failed tasks: {len(failed_tasks)}")

# %%
print("\n[INFO] Testing stage order:")
stage_order = ["raw", "summarize", "categorize"]
print(f"✅ Stage order: {stage_order}")

# %%
print("\n" + "=" * 60)
print("SIMPLIFIED PIPELINE STATE TEST COMPLETED")
print("=" * 60)

print("\n[BENEFITS OF SIMPLIFIED APPROACH]")
print("✅ Much simpler schema (2 fields instead of 4)")
print("✅ More flexible - easy to add new stages")
print("✅ Clearer logic - 'what's the furthest we've gotten?'")
print("✅ Failures don't promote latest_completed_stage")
print("✅ Easy queries - 'show me everything past X stage'")
print("✅ Less state to manage")

print("\n[EXAMPLE WORKER CODE]")
print("""
# Simple worker pattern:
def summarize_worker():
    tasks = manager.get_next_stage_tasks(pipeline_stages.SUMMARIZE)
    for task in tasks:
        try:
            # Do the work
            result = process_summarization(task)
            
            # Mark as completed
            manager.update_stage_status(
                task.id, pipeline_stages.SUMMARIZE, PipelineStageStatus.COMPLETED
            )
        except Exception as e:
            # Mark as failed - latest_completed_stage stays the same
            manager.update_stage_status(
                task.id, pipeline_stages.SUMMARIZE, PipelineStageStatus.FAILED,
                error_message=str(e)
            )
""")
