"""Speaker data models for the DiscourseKG platform."""

from pydantic import BaseModel
from typing import Dict
from enum import Enum


class Industry(str, Enum):
    """Industry/domain classification for speakers."""
    POLITICS = "politics"
    TECHNOLOGY = "technology"
    FINANCE = "finance"
    HEALTHCARE = "healthcare"
    ENERGY = "energy"
    MEDIA = "media"
    ACADEMIA = "academia"


class Speaker(BaseModel):
    """Individual speaker profile."""
    display_name: str
    role: str
    organization: str
    industry: Industry
    region: str
    date_of_birth: str
    bio: str


class SpeakerRegistry(BaseModel):
    """Registry of all speakers in the system."""
    speakers: Dict[str, Speaker]

