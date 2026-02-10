"""Data models for categorization domain."""

from pydantic import BaseModel, Field, field_validator
from enum import Enum
from typing import Optional, List, Dict, Any
from src.shared.models import StageOperationResult


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
    OTHER = ("other", "anything else")
    
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


class Subject(BaseModel):
    """Specific subject discussed within a topic mention"""
    
    subject_name: str = Field(
        ..., 
        min_length=2,
        max_length=50,
        description="1-3 word description of the specific subject discussed (2 words preferred)"
    )
    
    sentiment: SentimentLevel = Field(..., description="Speaker's feeling toward this specific subject")
    
    quotes: List[str] = Field(
        ...,
        min_items=1,
        max_items=6,
        description="Direct quotes about this subject (minimum 1, 1-2 recommended)"
    )
    
    @field_validator('subject_name')
    @classmethod
    def validate_word_count(cls, v: str) -> str:
        """Ensure subject_name is 1-3 words"""
        word_count = len(v.split())
        if word_count < 1 or word_count > 3:
            raise ValueError(f"subject_name must be 1-3 words, got {word_count} words: '{v}'")
        return v


class TopicMention(BaseModel):
    """Single mention of an entity within a specific topic"""
    
    topic: TopicCategory = Field(..., description="Topic category where entity was discussed")
    
    context: str = Field(
        ..., 
        min_length=30, 
        max_length=500,
        description="Summary of how this entity was discussed in this topic"
    )
    
    subjects: List[Subject] = Field(
        ...,
        min_items=1,
        description="List of specific subjects discussed about this entity in this topic"
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


class CategorizeContext(BaseModel):
    """Processing context for categorization operation."""
    id: str = Field(..., description="Unique identifier for the item")
    categorization_input: CategorizationInput = Field(..., description="Categorization input data")
    previous_error: Optional[str] = Field(None, description="Previous error message if retrying")
    previous_failed_output: Optional[str] = Field(None, description="Previous failed output if retrying")


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


class CategorizeStageMetadata(BaseModel):
    """Metadata stored in pipeline state for categorize stage."""
    content_type: Optional[str] = Field(None, description="Type of content (speech, debate, interview, etc.)")
    model_used: str = Field(..., description="LLM model used for categorization")
    input_tokens: int = Field(default=0, description="Input tokens used")
    output_tokens: int = Field(default=0, description="Output tokens used")


class CategorizationResult(StageOperationResult[CategorizationOutput]):
    """Result of categorization operation (artifact only, no metadata)."""
    pass


class CategorizeItem(BaseModel):
    """Input record required for categorization."""
    id: str = Field(..., description="Identifier of the pipeline item to categorize")
    latest_completed_stage: str = Field(..., description="Last stage completed for this item")
    stages: Dict[str, Any] = Field(default_factory=dict, description="Per-stage metadata")
    error_message: Optional[str] = Field(None, description="Previous error message if categorization is a retry")
    
    def get_current_file_path(self) -> Optional[str]:
        """Get file path for the latest completed stage"""
        if self.latest_completed_stage and self.latest_completed_stage in self.stages:
            return self.stages[self.latest_completed_stage].get('file_path')
        return None