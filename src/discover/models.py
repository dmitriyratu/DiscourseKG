"""
Pydantic models for the discovery stage.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class DiscoveredItem(BaseModel):
    """Normalized representation of a discovered content source."""

    id: str = Field(..., description="Unique identifier for the discovered item")
    source_url: str = Field(..., description="Original source URL")
    speaker: str = Field(..., description="Primary speaker associated with the content")
    content_type: str = Field(..., description="Content type suggested by discovery")


class DiscoveryRequest(BaseModel):
    """Input parameters for the discovery stage."""

    speaker: str = Field(..., description="Speaker to discover content for")
    start_date: str = Field(..., description="Start of discovery date range (YYYY-MM-DD)")
    end_date: str = Field(..., description="End of discovery date range (YYYY-MM-DD)")


class DiscoveryData(BaseModel):
    """Discovery operation data."""
    discovery_id: str = Field(..., description="Unique identifier for this discovery run")
    discovered_items: List[DiscoveredItem] = Field(..., description="List of discovered content items")
    speaker: str = Field(..., description="Speaker for whom content was discovered")
    date_range: str = Field(..., description="Date range for discovery")
    item_count: int = Field(..., description="Number of items discovered")


class DiscoveryResult(BaseModel):
    """Result of discovery operation (artifact only, no metadata)."""
    success: bool = Field(..., description="Whether discovery was successful")
    data: Optional[DiscoveryData] = Field(None, description="Discovery data")
    error_message: Optional[str] = Field(None, description="Error message if discovery failed")

