"""Shared data models used across multiple domains."""

from enum import Enum
from typing import TypeVar, Generic, Optional
from pydantic import BaseModel, Field


class ContentType(str, Enum):
    """Type of communication content."""
    SPEECH = "speech"
    DEBATE = "debate"
    INTERVIEW = "interview"
    PRESENTATION = "presentation"
    OTHER = "other"
    UNKNOWN = "unknown"


T = TypeVar('T')


class StageOperationResult(BaseModel, Generic[T]):
    """Base result model for all pipeline stage operations."""
    id: str = Field(..., description="Unique identifier")
    success: bool = Field(..., description="Whether operation was successful")
    data: Optional[T] = Field(None, description="Operation data if successful")
    error_message: Optional[str] = Field(None, description="Error message if failed")
