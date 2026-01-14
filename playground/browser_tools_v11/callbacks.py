"""LangChain callback handler for agent logging."""
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import ToolMessage, AIMessage
from langchain_core.outputs import LLMResult
from typing import Any, Dict, List
import json
import ast
import textwrap
from rich.console import Console
from rich.json import JSON
from rich.panel import Panel
from rich.text import Text

_TRUNCATE_LENGTH = 150
_MAX_ARRAY_ITEMS = 3

class AgentLogger(BaseCallbackHandler):
    """Clean terminal logging for agent actions."""
    
    def __init__(self):
        self._streaming = False
        self._buffer = []
        self._will_show_thinking = True
        self._console = Console()
        self._current_tool = None
    
    def _format_text(self, text: str) -> None:
        """Normalize whitespace and wrap text."""
        normalized = ' '.join(text.split())
        self._console.print(Panel(normalized, border_style="bright_blue"))
    
    def _truncate(self, text: str) -> str:
        """Truncate text with ellipsis if needed."""
        return textwrap.shorten(text, width=_TRUNCATE_LENGTH, placeholder="...")
    
    def _truncate_arrays(self, obj: Any) -> Any:
        """Truncate arrays to max items and long strings with ellipsis."""
        if isinstance(obj, dict):
            return {k: self._truncate_arrays(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            if len(obj) > _MAX_ARRAY_ITEMS:
                truncated = [self._truncate_arrays(item) for item in obj[:_MAX_ARRAY_ITEMS]]
                truncated.append(f"... ({len(obj) - _MAX_ARRAY_ITEMS} more)")
                return truncated
            return [self._truncate_arrays(item) for item in obj]
        elif isinstance(obj, str) and len(obj) > _TRUNCATE_LENGTH:
            return self._truncate(obj)
        return obj
    
    def _print_header(self, title: str) -> None:
        """Print a section header."""
        self._console.print()
        self._console.print(Panel(title, style="bold", border_style="bright_blue"))
    
    def _print_json(self, json_str: str) -> None:
        """Print formatted JSON."""
        try:
            self._console.print(JSON(json_str))
        except (json.JSONDecodeError, ValueError):
            self._console.print(json_str)
    
    def _process_content(self, content: str) -> None:
        """Process and display content (text and/or JSON)."""
        content = content.strip()
        if not content:
            return
        
        # Try parsing as pure JSON first
        try:
            json.loads(content)
            self._print_header("AGENT RESULT")
            self._print_json(content)
            return
        except json.JSONDecodeError:
            pass
        
        # Try extracting JSON from mixed content
        start = content.find('{')
        if start != -1:
            try:
                decoder = json.JSONDecoder()
                _, end = decoder.raw_decode(content, start)
                json_str = content[start:end]
                text_only = (content[:start] + content[end:]).strip()
                
                if text_only:
                    self._show_thinking_header()
                    self._format_text(text_only)
                self._print_header("RESULT")
                self._print_json(json_str)
                return
            except (json.JSONDecodeError, ValueError):
                pass
        
        # No JSON found, display as text
        self._show_thinking_header()
        self._format_text(content)
    
    def _show_thinking_header(self) -> None:
        """Show thinking header only once per generation."""
        if self._will_show_thinking:
            self._print_header("AGENT THINKING...")
            self._will_show_thinking = False
    
    def on_chat_model_start(
        self, 
        serialized: Dict[str, Any], 
        messages: List[Any], 
        **kwargs: Any
    ) -> None:
        """Log when chat model starts processing."""
        self._streaming = False
        self._buffer = []
        self._will_show_thinking = True
    
    def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        """Capture tokens as they're generated."""
        self._streaming = True
        self._buffer.append(token)
    
    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Display agent reasoning from LLM response."""
        if self._streaming:
            full_text = ''.join(self._buffer).strip()
            if full_text:
                self._process_content(full_text)
            self._buffer = []
            self._streaming = False
            return
        
        for gen_list in response.generations or []:
            for gen in gen_list:
                message = getattr(gen, 'message', None)
                if not isinstance(message, AIMessage):
                    continue
                
                content = message.content
                if isinstance(content, str) and content.strip():
                    self._process_content(content)
    
    def on_tool_start(
        self, 
        serialized: Dict[str, Any], 
        input_str: str, 
        **kwargs: Any
    ) -> None:
        """Log when a tool starts executing."""
        tool_name = serialized.get('name', 'unknown')
        self._current_tool = tool_name
        self._console.print()
        
        # First panel: USING TOOL indicator
        self._console.print(Panel(
            Text(f"USING TOOL: {tool_name}", style="bold white"),
            border_style="white"
        ))
        
        # Second panel: Tool input content
        try:
            data = json.loads(input_str)
            self._console.print(Panel(JSON(json.dumps(data)), border_style="white"))
        except (json.JSONDecodeError, ValueError, TypeError):
            try:
                data = ast.literal_eval(input_str)
                self._console.print(Panel(JSON(json.dumps(data)), border_style="white"))
            except (ValueError, SyntaxError):
                self._console.print(Panel(
                    Text(self._truncate(input_str), style="dim white"),
                    border_style="white"
                ))
    
    def on_tool_end(self, output: Any, **kwargs: Any) -> None:
        """Log tool execution results."""
        result_str = output.content if isinstance(output, ToolMessage) else str(output)
        tool_name = self._current_tool or "unknown"
        self._current_tool = None
        
        self._console.print()
        self._console.print(Panel(
            Text(f"TOOL RESULT: {tool_name}", style="bold white"),
            border_style="white"
        ))
        
        try:
            data = json.loads(result_str)
            if not data.get("success"):
                error_msg = data.get('error', 'Unknown error')
                content = Text(f"Failed: {error_msg}", style="red")
                self._console.print(Panel(content, border_style="white"))
                return
            
            truncated_data = self._truncate_arrays(data)
            self._console.print(Panel(JSON(json.dumps(truncated_data)), border_style="white"))
            
        except (json.JSONDecodeError, ValueError, TypeError):
            content = Text(self._truncate(result_str))
            self._console.print(Panel(content, border_style="white"))
    
    def on_tool_error(self, error: BaseException, **kwargs: Any) -> None:
        """Log tool execution errors."""
        tool_name = self._current_tool or "unknown"
        self._current_tool = None
        self._console.print()
        self._console.print(Panel(
            Text(f"TOOL RESULT: {tool_name}", style="bold white"),
            border_style="white"
        ))
        content = Text(f"Error: {error}", style="red")
        self._console.print(Panel(content, border_style="white"))
