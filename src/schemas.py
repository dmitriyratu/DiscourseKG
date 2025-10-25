"""
Data schemas for political communication categorization and sentiment analysis.

This module defines the core data structures used throughout the DiscourseKG platform
for categorizing political communications, extracting entities, and analyzing sentiment.
"""

from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional, List, Dict, Any


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


# ============================================================================
# PYDANTIC MODELS - Core Data Structures
# ============================================================================

class EntityMention(BaseModel):
    """Single entity mentioned in communication"""
    
    entity_name: str = Field(
        ..., 
        min_length=1, 
        max_length=200,
        description="Canonical/standard name for this entity (e.g., 'Apple', 'China', 'Joe Biden')"
    )
    
    entity_type: EntityType = Field(..., description="Type of entity")
    
    sentiment: SentimentLevel = Field(..., description="Speaker's feeling toward entity")
    
    context: str = Field(
        ..., 
        min_length=10, 
        max_length=500,
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
    categorize: List[CategoryWithEntities] = Field(description="List of categories with entities")


class ScrapingData(BaseModel):
    """Scraped content data."""
    title: str = Field(..., description="Title of the scraped content")
    date: str = Field(..., description="Date of the content")
    event_date: str = Field(..., description="Event date")
    type: str = Field(..., description="Type of content (speech, interview, debate)")
    source_url: str = Field(..., description="Original source URL")
    timestamp: str = Field(..., description="Content timestamp")
    scrape: str = Field(..., description="The scraped content text")


class ScrapingResult(BaseModel):
    """Result of scraping operation with metrics and metadata."""
    id: str = Field(..., description="Unique identifier for the scraped content")
    success: bool = Field(..., description="Whether scraping was successful")
    data: Optional[ScrapingData] = Field(None, description="Scraped content data")
    error_message: Optional[str] = Field(None, description="Error message if scraping failed")


class SummarizationData(BaseModel):
    """Summarized content data."""
    summarize: str = Field(..., description="The summarized text")
    original_word_count: int = Field(..., description="Word count of original text")
    summary_word_count: int = Field(..., description="Word count of summary")
    compression_ratio: float = Field(..., description="Ratio of summary length to original length")
    target_word_count: int = Field(..., description="Target word count for summary")


class SummarizationResult(BaseModel):
    """Result of summarization operation with metrics and metadata."""
    id: str = Field(..., description="Unique identifier for the summarized content")
    success: bool = Field(..., description="Whether summarization was successful")
    data: Optional[SummarizationData] = Field(None, description="Summarized content data")
    error_message: Optional[str] = Field(None, description="Error message if summarization failed")


class CategorizationResult(BaseModel):
    """Result of categorization operation with metrics and metadata."""
    id: str = Field(..., description="Unique identifier for the categorized content")
    success: bool = Field(..., description="Whether categorization was successful")
    data: Optional[CategorizationOutput] = Field(None, description="Categorized content data")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    error_message: Optional[str] = Field(None, description="Error message if categorization failed")


