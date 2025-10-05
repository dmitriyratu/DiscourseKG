#!/usr/bin/env python3
"""
Test script for the simplified next_stage pipeline tracking.

This demonstrates how much simpler the autonomous stages become
when the state itself tells us what to do next.
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
print("SIMPLIFIED NEXT_STAGE PIPELINE TEST")
print("=" * 60)

# %%
print("\n[INFO] Testing simplified next_stage approach...")
manager = PipelineStateManager()

# %%
print("\n[INFO] Creating test data points...")

# Create states for test data points
test_data_points = [
    {
        "id": "test_001",
        "scrape_cycle": "2025-01-15_14:00:00",
        "description": "Test data point 1"
    },
    {
        "id": "test_002", 
        "scrape_cycle": "2025-01-15_14:00:00",
        "description": "Test data point 2"
    }
]

created_states = []
for data_point in test_data_points:
    state = manager.create_state(data_point["id"], data_point["scrape_cycle"])
    created_states.append(state)
    print(f"✅ Created state for: {data_point['description']}")
    print(f"   - ID: {state.id}")
    print(f"   - Next stage: {state.next_stage}")

# %%
print("\n[INFO] Testing autonomous stage queries...")

# Each stage just asks: "What work is assigned to me?"
summarizer_tasks = manager.get_next_stage_tasks("summarized")
print(f"✅ Summarizer found {len(summarizer_tasks)} tasks assigned to it")

categorizer_tasks = manager.get_next_stage_tasks("categorized") 
print(f"✅ Categorizer found {len(categorizer_tasks)} tasks assigned to it")

# %%
print("\n[INFO] Simulating summarizer processing...")

# Summarizer processes its assigned work
for task in summarizer_tasks:
    print(f"📝 Summarizer processing: {task.id}")
    
    # Simulate work
    manager.update_stage_status(
        task.id, "summarized", PipelineStageStatus.IN_PROGRESS
    )
    
    # Simulate completion
    manager.update_stage_status(
        task.id, "summarized", PipelineStageStatus.COMPLETED,
        processing_time=2.5
    )
    
    # Check what the next_stage is now
    updated_state = manager.get_state(task.id)
    print(f"   ✅ Completed! Next stage: {updated_state.next_stage}")

# %%
print("\n[INFO] Testing categorizer after summarizer completes...")

# Now categorizer should have work
categorizer_tasks = manager.get_next_stage_tasks("categorized")
print(f"✅ Categorizer now has {len(categorizer_tasks)} tasks")

# Categorizer processes its work
for task in categorizer_tasks:
    print(f"🏷️  Categorizer processing: {task.id}")
    
    # Simulate work
    manager.update_stage_status(
        task.id, "categorized", PipelineStageStatus.IN_PROGRESS
    )
    
    # Simulate completion
    manager.update_stage_status(
        task.id, "categorized", PipelineStageStatus.COMPLETED,
        processing_time=3.2
    )
    
    # Check final state
    updated_state = manager.get_state(task.id)
    print(f"   ✅ Completed! Next stage: {updated_state.next_stage}")

# %%
print("\n[INFO] Testing failure and retry scenario...")

# Create a new test data point
test_state = manager.create_state("test_fail", "2025-01-15_15:00:00")
print(f"✅ Created test failure data point: {test_state.id}")

# Summarizer processes it
manager.update_stage_status(
    "test_fail", "summarized", PipelineStageStatus.IN_PROGRESS
)

# Simulate failure
manager.update_stage_status(
    "test_fail", "summarized", PipelineStageStatus.FAILED,
    error_message="OpenAI API timeout"
)

# Check what happened
failed_state = manager.get_state("test_fail")
print(f"❌ Failed summarization. Next stage: {failed_state.next_stage}")
print(f"   Categorized status: {failed_state.categorized_status}")

# Retry the failed work
retry_tasks = manager.get_next_stage_tasks("summarized")
print(f"🔄 Found {len(retry_tasks)} tasks to retry")

# %%
print("\n[INFO] Simple stage worker example...")

def simple_summarizer_worker():
    """Example of how simple a stage worker becomes"""
    tasks = manager.get_next_stage_tasks("summarized")
    
    for task in tasks:
        print(f"📝 Processing {task.id}")
        
        # Mark in progress
        manager.update_stage_status(task.id, "summarized", PipelineStageStatus.IN_PROGRESS)
        
        # Do work (simulated)
        import time
        time.sleep(0.1)  # Simulate processing
        
        # Mark complete
        manager.update_stage_status(task.id, "summarized", PipelineStageStatus.COMPLETED, processing_time=0.1)
        
        print(f"   ✅ Done! Next stage will be: {manager.get_state(task.id).next_stage}")

def simple_categorizer_worker():
    """Example categorizer worker"""
    tasks = manager.get_next_stage_tasks("categorized")
    
    for task in tasks:
        print(f"🏷️  Processing {task.id}")
        
        # Mark in progress
        manager.update_stage_status(task.id, "categorized", PipelineStageStatus.IN_PROGRESS)
        
        # Do work (simulated)
        import time
        time.sleep(0.1)  # Simulate processing
        
        # Mark complete
        manager.update_stage_status(task.id, "categorized", PipelineStageStatus.COMPLETED, processing_time=0.1)
        
        final_state = manager.get_state(task.id)
        print(f"   ✅ Done! Next stage: {final_state.next_stage}")

# Run the simple workers
print("\nRunning simple workers:")
simple_summarizer_worker()
simple_categorizer_worker()

# %%
print("\n" + "=" * 60)
print("SIMPLIFIED PIPELINE TEST COMPLETED")
print("=" * 60)

print("\n[SUMMARY]")
print("✅ Each stage just asks: 'What work is assigned to me?'")
print("✅ State automatically tracks what's next")
print("✅ No complex orchestration needed")
print("✅ Perfect for Dagster/Prefect/ECS workers")
print("✅ Super simple worker functions")

print("\n[EXAMPLE WORKER CODE]")
print("""
def summarizer_worker():
    tasks = manager.get_next_stage_tasks('summarized')
    for task in tasks:
        # Process the task
        manager.update_stage_status(task.id, 'summarized', PipelineStageStatus.COMPLETED)
        # next_stage automatically updates to 'categorized'
""")
