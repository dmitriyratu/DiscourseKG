"""Shared data models used across multiple domains."""

from enum import Enum

from pydantic import BaseModel, Field



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
