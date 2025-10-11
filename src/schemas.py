"""
Data schemas for political communication categorization and sentiment analysis.

This module defines the core data structures used throughout the KG-Sentiment platform
for categorizing political communications, extracting entities, and analyzing sentiment.
"""

from pydantic import BaseModel, Field, constr
from enum import Enum
from typing import Optional, List


# ============================================================================
# ENUMS - Core Classification Types
# ============================================================================

class PolicyDomain(str, Enum):
    """Broad policy areas for categorizing communications"""
    ECONOMIC_POLICY = ("economic_policy", "taxes, trade, monetary policy, financial markets")
    TECHNOLOGY_POLICY = ("technology_policy", "AI regulation, data privacy, tech competition")
    FOREIGN_RELATIONS = ("foreign_relations", "diplomacy, international agreements, global conflicts")
    HEALTHCARE_POLICY = ("healthcare_policy", "health insurance, medical costs, public health")
    ENERGY_POLICY = ("energy_policy", "renewable energy, fossil fuels, climate change")
    DEFENSE_POLICY = ("defense_policy", "military spending, national security, defense contracts")
    SOCIAL_POLICY = ("social_policy", "education, welfare, social programs, inequality")
    REGULATORY_POLICY = ("regulatory_policy", "government oversight, regulations, compliance")
    
    def __new__(cls, value, description):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.description = description
        return obj


class EntityType(str, Enum):
    """What type of entity is mentioned"""
    COMPANY = ("company", "public/private companies")
    COUNTRY = ("country", "nations that create geopolitical risk")
    PERSON = ("person", "influential individuals")
    POLICY_TOOL = ("policy_tool", "mechanisms like tariffs, sanctions")
    OTHER = ("other", "anything else")
    
    def __new__(cls, value, description):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.description = description
        return obj


class SentimentLevel(str, Enum):
    """How the speaker feels about this entity - only when clearly expressed"""
    POSITIVE = ("positive", "excellent, great, support")
    NEGATIVE = ("negative", "terrible, bad, oppose")
    NEUTRAL = ("neutral", "factual mention without emotion")
    UNCLEAR = ("unclear", "can't determine from text")
    
    def __new__(cls, value, description):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.description = description
        return obj


class PipelineStageStatus(str, Enum):
    """Status of a pipeline stage"""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS" 
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    INVALIDATED = "INVALIDATED"




# ============================================================================
# PYDANTIC MODELS - Core Data Structures
# ============================================================================

class EntityMention(BaseModel):
    """Single entity mentioned in communication"""
    
    entity_name: constr(min_length=1, max_length=200, strip_whitespace=True) = Field(
        ..., 
        description="Canonical/standard name for this entity (e.g., 'Apple', 'China', 'Joe Biden')"
    )
    
    entity_type: EntityType = Field(..., description="Type of entity")
    
    sentiment: SentimentLevel = Field(..., description="Speaker's feeling toward entity")
    
    context: constr(min_length=10, max_length=500, strip_whitespace=True) = Field(
        ..., 
        description="Summary of how this entity was discussed"
    )
    
    quotes: List[str] = Field(
        default_factory=list,
        description="Direct quotes from the original text mentioning this entity (1-3 most relevant excerpts)"
    )


class CategoryWithEntities(BaseModel):
    """A category containing entities"""
    category: str = Field(description="Policy domain category")
    entities: List[EntityMention] = Field(description="List of entities in this category")


class CategorizationOutput(BaseModel):
    """Output schema for the entire categorization"""
    categories: List[CategoryWithEntities] = Field(description="List of categories with entities")


class SummarizationResult(BaseModel):
    """Result of summarization operation with metrics and metadata."""
    
    summary: str = Field(..., description="The summarized text")
    original_text: str = Field(..., description="The original text that was summarized")
    original_word_count: int = Field(..., description="Word count of original text")
    summary_word_count: int = Field(..., description="Word count of summary")
    compression_ratio: float = Field(..., description="Ratio of summary length to original length")
    processing_time_seconds: float = Field(..., description="Time taken to process in seconds")
    target_word_count: int = Field(..., description="Target word count for summary")
    success: bool = Field(..., description="Whether summarization was successful")
    error_message: Optional[str] = Field(None, description="Error message if summarization failed")


class PipelineState(BaseModel):
    """Pipeline processing state for a single data point"""
    
    # Core identifiers
    id: str = Field(..., description="Unique ID from raw data (matches the 'id' field in raw JSON files)")
    scrape_cycle: str = Field(..., description="Hourly timestamp when scraped (YYYY-MM-DD_HH:00:00)")
    raw_file_path: Optional[str] = Field(None, description="Path to raw JSON file (relative to project root)")
    source_url: Optional[str] = Field(None, description="Original source URL (for deduplication and audit trail)")
    
    # Simple stage tracking
    latest_completed_stage: Optional[str] = Field(None, description="Latest successfully completed stage (None, 'raw', 'summarize', 'categorize')")
    next_stage: Optional[str] = Field(..., description="Next stage that needs to be processed")
    
    # Metadata
    created_at: str = Field(..., description="ISO timestamp when record was created")
    updated_at: str = Field(..., description="ISO timestamp of last update")
    error_message: Optional[str] = Field(None, description="Error message if current stage failed")
    
    # Processing metrics
    processing_time_seconds: Optional[float] = Field(None, description="Total processing time across all stages")
    retry_count: int = Field(default=0, description="Number of times this record has been retried")