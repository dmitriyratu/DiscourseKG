"""Shared data models used across multiple domains."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field



class LLMValidationError(Exception):
    """LLM output failed validation. Carries failed_output for retry context."""
    def __init__(self, message: str, *, failed_output: Optional[str] = None):
        super().__init__(message)
        self.failed_output = failed_output


class TokenUsage(BaseModel):
    """LLM token usage for a single invocation."""
    input_tokens: int = 0
    output_tokens: int = 0


class ContentType(str, Enum):
    """Type of communication content."""
    SPEECH = "speech"
    DEBATE = "debate"
    INTERVIEW = "interview"
    PRESENTATION = "presentation"
    OTHER = "other"
    UNKNOWN = "unknown"
