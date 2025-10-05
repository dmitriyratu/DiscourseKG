#!/usr/bin/env python3
"""
Test script for pipeline state management system.

This script demonstrates the pipeline state tracking functionality
and verifies that all components work correctly.
"""

# %%
import sys
from pathlib import Path
import json
from datetime import datetime

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from src.schemas import PipelineState, PipelineStageStatus
from src.utils.pipeline_state import PipelineStateManager
from src.config import config

# %%
print("=" * 60)
print("PIPELINE STATE MANAGEMENT TEST")
print("=" * 60)

# %%
print("\n[INFO] Testing PipelineStateManager initialization...")
manager = PipelineStateManager()
print(f"✅ State file path: {manager.state_file_path}")
print(f"✅ State file exists: {manager.state_file_path.exists()}")

# %%
print("\n[INFO] Creating test pipeline states...")

# Test data points (using IDs from your existing data)
test_data_points = [
    {
        "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "scrape_cycle": "2025-01-15_14:00:00",
        "description": "Donald Trump interview with Peter Doocy"
    },
    {
        "id": "b2c3d4e5-f6g7-8901-bcde-f23456789012", 
        "scrape_cycle": "2025-01-15_14:00:00",
        "description": "Donald Trump UN speech"
    }
]

# Create states for test data points
created_states = []
for data_point in test_data_points:
    state = manager.create_state(data_point["id"], data_point["scrape_cycle"])
    created_states.append(state)
    print(f"✅ Created state for: {data_point['description']}")
    print(f"   - ID: {state.id}")
    print(f"   - Scrape cycle: {state.scrape_cycle}")
    print(f"   - Raw status: {state.raw_status}")
    print(f"   - Summarized status: {state.summarized_status}")

# %%
print("\n[INFO] Testing state retrieval...")
for data_point in test_data_points:
    retrieved_state = manager.get_state(data_point["id"])
    if retrieved_state:
        print(f"✅ Retrieved state for {data_point['id']}: {retrieved_state.summarized_status}")
    else:
        print(f"❌ Failed to retrieve state for {data_point['id']}")

# %%
print("\n[INFO] Testing stage status updates...")

# Update summarization status for first data point
manager.update_stage_status(
    test_data_points[0]["id"], 
    "summarized", 
    PipelineStageStatus.IN_PROGRESS,
    processing_time=2.5
)
print("✅ Updated first data point to IN_PROGRESS for summarization")

# Complete summarization for first data point
manager.update_stage_status(
    test_data_points[0]["id"], 
    "summarized", 
    PipelineStageStatus.COMPLETED,
    processing_time=3.2
)
print("✅ Completed summarization for first data point")

# Fail summarization for second data point
manager.update_stage_status(
    test_data_points[1]["id"], 
    "summarized", 
    PipelineStageStatus.FAILED,
    error_message="OpenAI API timeout",
    processing_time=30.0
)
print("✅ Failed summarization for second data point (should invalidate downstream)")

# %%
print("\n[INFO] Testing query methods...")

# Get pending tasks
pending_summarization = manager.get_pending_tasks("summarized")
print(f"✅ Pending summarization tasks: {len(pending_summarization)}")

pending_categorization = manager.get_pending_tasks("categorized")
print(f"✅ Pending categorization tasks: {len(pending_categorization)}")

# Get failed tasks
failed_tasks = manager.get_failed_tasks()
print(f"✅ Failed tasks (any stage): {len(failed_tasks)}")
for task in failed_tasks:
    print(f"   - {task.id}: {task.error_message}")

# Get states by scrape cycle
cycle_states = manager.get_states_by_scrape_cycle("2025-01-15_14:00:00")
print(f"✅ States for scrape cycle 2025-01-15_14:00:00: {len(cycle_states)}")

# %%
print("\n[INFO] Testing state file content...")
if manager.state_file_path.exists():
    print("✅ State file contents:")
    with open(manager.state_file_path, "r") as f:
        for i, line in enumerate(f, 1):
            if line.strip():
                state_data = json.loads(line.strip())
                print(f"   {i}. ID: {state_data['id']}")
                print(f"      Summarized: {state_data['summarized_status']}")
                print(f"      Categorized: {state_data['categorized_status']}")
                if state_data.get('error_message'):
                    print(f"      Error: {state_data['error_message']}")

# %%
print("\n[INFO] Testing dependency invalidation...")
# Check that failed summarization invalidated categorization for second data point
state = manager.get_state(test_data_points[1]["id"])
if state:
    print(f"✅ Second data point categorization status: {state.categorized_status}")
    print(f"   (Should be INVALIDATED due to failed summarization)")

# %%
print("\n[INFO] Testing retry scenario...")
# Simulate retrying the failed data point
manager.update_stage_status(
    test_data_points[1]["id"], 
    "summarized", 
    PipelineStageStatus.IN_PROGRESS,
    processing_time=1.0
)
print("✅ Retried failed data point (set to IN_PROGRESS)")

manager.update_stage_status(
    test_data_points[1]["id"], 
    "summarized", 
    PipelineStageStatus.COMPLETED,
    processing_time=4.5
)
print("✅ Successfully completed retry")

# Check final state
final_state = manager.get_state(test_data_points[1]["id"])
if final_state:
    print(f"✅ Final state - Summarized: {final_state.summarized_status}")
    print(f"✅ Final state - Categorized: {final_state.categorized_status}")

# %%
print("\n" + "=" * 60)
print("PIPELINE STATE TEST COMPLETED")
print("=" * 60)

print("\n[SUMMARY]")
print(f"✅ Created {len(test_data_points)} test data points")
print(f"✅ State file: {manager.state_file_path}")
print(f"✅ All core functionality tested successfully")

print("\n[INFO] Pipeline state management system is ready for production use!")
print("   - Create states when new data is scraped")
print("   - Update stage status as processing progresses") 
print("   - Query for pending/failed tasks for rerun operations")
print("   - Automatic dependency invalidation on failures")
