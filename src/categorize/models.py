"""Data models for categorization domain."""

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.shared.models import StageOperationResult


class TopicCategory(str, Enum):
    """Broad topic categories for categorizing communications across any domain"""
    ECONOMICS = ("economics", "e.g., taxes, monetary policy, financial markets, cost of living")
    TRADE = ("trade", "e.g., tariffs, trade deals, imports, exports, supply chains")
    IMMIGRATION = ("immigration", "e.g., border security, deportation, asylum, refugees, enforcement")
    ELECTIONS = ("elections", "e.g., voting, election integrity, campaigns, ballot access, midterms")
    TECHNOLOGY = ("technology", "e.g., AI, data privacy, tech competition, innovation")
    FOREIGN_AFFAIRS = ("foreign_affairs", "e.g., diplomacy, international agreements, global conflicts")
    HEALTHCARE = ("healthcare", "e.g., health insurance, medical costs, public health")
    ENERGY = ("energy", "e.g., renewable energy, fossil fuels, climate change")
    DEFENSE = ("defense", "e.g., military spending, national security, military operations")
    SOCIAL = ("social", "e.g., education, welfare, social programs, inequality")
    REGULATION = ("regulation", "e.g., oversight, regulations, compliance, standards")
    LEGAL = ("legal", "e.g., court cases, lawsuits, indictments, DOJ, judicial decisions")
    MEDIA = ("media", "e.g., press coverage, specific outlets, journalists, fake news, censorship")
    PERSONNEL = ("personnel", "e.g., appointments, firings, resignations, confirmations, staffing")
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


class Claim(BaseModel):
    """Specific claim made within a topic"""
    model_config = ConfigDict(use_enum_values=True)

    subject_name: str = Field(
        ..., 
        min_length=2,
        max_length=50,
        description="1-3 word description of the specific claim (2 words preferred)"
    )
    
    sentiment: SentimentLevel = Field(..., description="Speaker's feeling toward this specific claim")
    
    quotes: List[str] = Field(
        ...,
        min_items=1,
        max_items=10,
        description="Include all relevant verbatim quotes (up to 10 per claim)"
    )
    
    @field_validator('subject_name')
    @classmethod
    def validate_word_count(cls, v: str) -> str:
        """Ensure subject_name is 1-3 words"""
        word_count = len(v.split())
        if word_count < 1 or word_count > 3:
            raise ValueError(f"subject_name must be 1-3 words, got {word_count} words: '{v}'")
        return v


class Topic(BaseModel):
    """Discussion of an entity by a specific speaker within a topic category"""
    model_config = ConfigDict(use_enum_values=True)

    speaker: str = Field(..., description="Speaker ID (from matched_speakers) who made this topic discussion")

    topic: TopicCategory = Field(..., description="Topic category where entity was discussed")
    
    context: str = Field(
        ..., 
        min_length=30, 
        max_length=500,
        description="Summary of how this speaker discussed this entity in this topic"
    )
    
    claims: List[Claim] = Field(
        ...,
        min_items=1,
        description="List of specific claims this speaker made about this entity in this topic"
    )


class EntityMention(BaseModel):
    """Entity with all its topic discussions"""
    model_config = ConfigDict(use_enum_values=True)

    entity_name: str = Field(
        ..., 
        min_length=1, 
        max_length=200,
        description="Canonical name for this entity (e.g., 'Apple', 'China', 'Joe Biden')"
    )
    
    entity_type: EntityType = Field(..., description="Type of entity")
    
    topics: List[Topic] = Field(
        ...,
        min_items=1,
        description="List of topic discussions, one per (speaker, topic) pair"
    )
    
    @field_validator('topics')
    @classmethod
    def validate_unique_speaker_topic_pairs(cls, topics: List[Topic]) -> List[Topic]:
        """Ensure each (speaker, topic) pair appears only once per entity"""
        keys: List[Tuple[str, str]] = [(t.speaker, t.topic) for t in topics]
        if len(keys) != len(set(keys)):
            duplicates = {k for k in keys if keys.count(k) > 1}
            raise ValueError(f"Duplicate (speaker, topic) pairs found: {duplicates}. Each entity must have ONE topic per (speaker, topic).")
        return topics


class ExtractedEntityInput(BaseModel):
    """Single entity from the extract stage, with passages to categorize."""
    entity_name: str = Field(..., description="Canonical entity name")
    passages: List[str] = Field(..., description="Passages with [display_name] speaker markers")


class CategorizationInput(BaseModel):
    """Input fields for categorization."""
    title: str = Field(..., description="Title of the scraped content")
    content_date: str = Field(..., description="Date when the content was created/published")
    entities: List[ExtractedEntityInput] = Field(..., description="Entities with passages from extract stage")
    matched_speakers: Dict[str, str] = Field(..., description="Tracked speakers present in content: id -> display_name")


class CategorizeContext(BaseModel):
    """Processing context for categorization operation."""
    id: str = Field(..., description="Unique identifier for the item")
    categorization_input: CategorizationInput = Field(..., description="Categorization input data")
    previous_error: Optional[str] = Field(None, description="Previous error message if retrying")
    previous_failed_output: Optional[str] = Field(None, description="Previous failed output if retrying")


class CategorizationOutput(BaseModel):
    """Output schema for the entire categorization"""
    entities: List[EntityMention] = Field(description="List of entities with their topic discussions")

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