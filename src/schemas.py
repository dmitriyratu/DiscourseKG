"""
Data schemas for political communication categorization and sentiment analysis.

This module defines the core data structures used throughout the DiscourseKG platform
for categorizing political communications, extracting entities, and analyzing sentiment.
"""

from pydantic import BaseModel, Field, field_validator
from enum import Enum
from typing import Optional, List, Dict, Any


# ============================================================================
# ENUMS - Core Classification Types
# ============================================================================

class TopicCategory(str, Enum):
    """Broad topic categories for categorizing communications across any domain"""
    ECONOMICS = ("economics", "taxes, trade, monetary policy, financial markets")
    TECHNOLOGY = ("technology", "AI, data privacy, tech competition, innovation")
    FOREIGN_AFFAIRS = ("foreign_affairs", "diplomacy, international agreements, global conflicts")
    HEALTHCARE = ("healthcare", "health insurance, medical costs, public health")
    ENERGY = ("energy", "renewable energy, fossil fuels, climate change")
    DEFENSE = ("defense", "military spending, national security, defense")
    SOCIAL = ("social", "education, welfare, social programs, inequality")
    REGULATION = ("regulation", "oversight, regulations, compliance, standards")
    
    def __new__(cls, value, description):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.description = description
        return obj


class EntityType(str, Enum):
    """Type of entity mentioned in communications"""
    ORGANIZATION = ("organization", "companies, institutions, government bodies")
    LOCATION = ("location", "countries, regions, cities")
    PERSON = ("person", "individuals, public figures")
    PROGRAM = ("program", "initiatives, policies, projects, mechanisms")
    PRODUCT = ("product", "products, services, tools, platforms")
    EVENT = ("event", "conferences, summits, incidents, launches")
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

class Subject(BaseModel):
    """Specific subject discussed within a topic mention"""
    
    subject_name: str = Field(
        ..., 
        min_length=4,
        max_length=50,
        description="2-3 word description of the specific subject discussed"
    )
    
    sentiment: SentimentLevel = Field(..., description="Speaker's feeling toward this specific subject")
    
    quotes: List[str] = Field(
        ...,
        min_items=1,
        description="Direct quotes about this subject (1-6 quotes recommended)"
    )
    
    @field_validator('subject_name')
    @classmethod
    def validate_word_count(cls, v: str) -> str:
        """Ensure subject_name is 2-3 words"""
        word_count = len(v.split())
        if word_count < 2 or word_count > 3:
            raise ValueError(f"subject_name must be 2-3 words, got {word_count} words: '{v}'")
        return v


class SentimentAggregation(BaseModel):
    """Aggregated sentiment statistics for a topic mention"""
    count: int = Field(..., description="Number of subjects with this sentiment")
    prop: float = Field(..., description="Proportion of subjects with this sentiment")


class TopicMention(BaseModel):
    """Single mention of an entity within a specific topic"""
    
    topic: TopicCategory = Field(..., description="Topic category where entity was discussed")
    
    context: str = Field(
        ..., 
        min_length=10, 
        max_length=500,
        description="Summary of how this entity was discussed in this topic"
    )
    
    subjects: List[Subject] = Field(
        ...,
        min_items=1,
        description="List of specific subjects discussed about this entity in this topic"
    )
    
    aggregated_sentiment: Optional[Dict[str, SentimentAggregation]] = Field(
        default=None,
        description="Computed aggregation of sentiment across all subjects in this mention"
    )


class EntityMention(BaseModel):
    """Entity with all its topic mentions"""
    
    entity_name: str = Field(
        ..., 
        min_length=1, 
        max_length=200,
        description="Canonical name for this entity (e.g., 'Apple', 'China', 'Joe Biden')"
    )
    
    entity_type: EntityType = Field(..., description="Type of entity")
    
    mentions: List[TopicMention] = Field(
        ...,
        min_items=1,
        description="List of mentions, one per unique topic where entity was discussed"
    )
    
    @field_validator('mentions')
    @classmethod
    def validate_unique_topics(cls, mentions: List[TopicMention]) -> List[TopicMention]:
        """Ensure each topic appears only once per entity"""
        topics = [m.topic for m in mentions]
        if len(topics) != len(set(topics)):
            duplicates = [topic for topic in topics if topics.count(topic) > 1]
            raise ValueError(f"Duplicate topics found: {set(duplicates)}. Each entity must have ONE mention per unique topic.")
        return mentions


class CategorizationInput(BaseModel):
    """Input fields for categorization with descriptions."""
    title: str = Field(..., description="Title of the scraped content")
    content_date: str = Field(..., description="Date when the content was created/published")
    content: str = Field(..., description="The summarized content to analyze")


class CategorizationOutput(BaseModel):
    """Output schema for the entire categorization"""
    entities: List[EntityMention] = Field(description="List of entities with their topic mentions")
    
    @field_validator('entities')
    @classmethod
    def validate_unique_entity_names(cls, entities: List[EntityMention]) -> List[EntityMention]:
        """Ensure each entity name appears only once (case-insensitive)"""
        entity_names = [e.entity_name.lower() for e in entities]
        if len(entity_names) != len(set(entity_names)):
            duplicates = [name for name in entity_names if entity_names.count(name) > 1]
            raise ValueError(f"Duplicate entity names found: {set(duplicates)}. Each entity should appear only once.")
        return entities


class ScrapingData(BaseModel):
    """Scraped content data."""
    scrape: str = Field(..., description="The scraped content text")


class ScrapingResult(BaseModel):
    """Result of scraping operation with metrics and metadata."""
    id: str = Field(..., description="Unique identifier for the scraped content")
    success: bool = Field(..., description="Whether scraping was successful")
    data: Optional[ScrapingData] = Field(None, description="Scraped content data")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
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
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    error_message: Optional[str] = Field(None, description="Error message if summarization failed")


class CategorizationResult(BaseModel):
    """Result of categorization operation with metrics and metadata."""
    id: str = Field(..., description="Unique identifier for the categorized content")
    success: bool = Field(..., description="Whether categorization was successful")
    data: Optional[CategorizationOutput] = Field(None, description="Categorized content data")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    error_message: Optional[str] = Field(None, description="Error message if categorization failed")


