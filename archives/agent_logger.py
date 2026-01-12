"""Logger for agent tool interactions and reasoning."""

import asyncio
import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict
from functools import wraps

class AgentLogger:
    """Logs agent interactions with tools for debugging and optimization."""
    
    def __init__(self, log_dir: str = "nuagent_traces"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
    def log_tool_call(self, tool_name: str, inputs: Dict, output: Any, metadata: Dict = None):
        """Log a tool invocation with inputs and outputs."""
        timestamp = datetime.now().isoformat()
        
        log_entry = {
            "timestamp": timestamp,
            "session_id": self.session_id,
            "tool": tool_name,
            "inputs": inputs,
            "output": output if isinstance(output, (dict, list)) else str(output),
            "output_size": len(str(output)),
            "metadata": metadata or {}
        }
        
        # Append to session log file (JSONL format)
        log_file = self.log_dir / f"session_{self.session_id}.jsonl"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        
        # Also save individual tool outputs for easy review
        output_file = self.log_dir / f"{tool_name}_{timestamp.replace(':', '-')}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(log_entry, f, indent=2, ensure_ascii=False)
        
        return log_entry
    
    def log_agent_thought(self, thought: str, context: Dict = None):
        """Log agent reasoning/thought process."""
        timestamp = datetime.now().isoformat()
        
        log_entry = {
            "timestamp": timestamp,
            "session_id": self.session_id,
            "type": "agent_thought",
            "thought": thought,
            "context": context or {}
        }
        
        log_file = self.log_dir / f"session_{self.session_id}.jsonl"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

def log_tool_execution(logger: AgentLogger):
    """Decorator to automatically log tool executions."""
    def decorator(func):
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            tool_name = getattr(args[0], 'name', func.__name__) if args else func.__name__
            inputs = {**kwargs}
            if args and len(args) > 1:
                inputs.update({"args": args[1:]})
            
            try:
                result = func(*args, **kwargs)
                logger.log_tool_call(
                    tool_name=tool_name,
                    inputs=inputs,
                    output=result,
                    metadata={"status": "success"}
                )
                return result
            except Exception as e:
                logger.log_tool_call(
                    tool_name=tool_name,
                    inputs=inputs,
                    output={"error": str(e)},
                    metadata={"status": "error", "error_type": type(e).__name__}
                )
                raise
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            tool_name = getattr(args[0], 'name', func.__name__) if args else func.__name__
            inputs = {**kwargs}
            if args and len(args) > 1:
                inputs.update({"args": args[1:]})
            
            try:
                result = await func(*args, **kwargs)
                logger.log_tool_call(
                    tool_name=tool_name,
                    inputs=inputs,
                    output=result,
                    metadata={"status": "success"}
                )
                return result
            except Exception as e:
                logger.log_tool_call(
                    tool_name=tool_name,
                    inputs=inputs,
                    output={"error": str(e)},
                    metadata={"status": "error", "error_type": type(e).__name__}
                )
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

# Global logger instance
_global_logger = None

def get_logger() -> AgentLogger:
    """Get or create global logger instance."""
    global _global_logger
    if _global_logger is None:
        _global_logger = AgentLogger()
    return _global_logger

