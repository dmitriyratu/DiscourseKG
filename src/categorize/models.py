"""Data models for categorization domain."""

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.shared.pipeline_definitions import StageOperationResult


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


class ClaimLLM(BaseModel):
    """LLM output: indices into passages array."""
    model_config = ConfigDict(use_enum_values=True)
    speaker: str = Field(...)
    topic: TopicCategory = Field(...)
    claim_label: str = Field(..., min_length=2, max_length=50)
    sentiment: SentimentLevel = Field(...)
    summary: str = Field(...)
    passage_indices: List[int] = Field(..., min_length=1)

    @field_validator('claim_label')
    @classmethod
    def claim_label_words(cls, v: str) -> str:
        n = len(v.split())
        if n < 1 or n > 3:
            raise ValueError(f"claim_label must be 1-3 words: '{v}'")
        return v


class Claim(BaseModel):
    """Saved output: resolved verbatim passages."""
    model_config = ConfigDict(use_enum_values=True)
    speaker: str = Field(...)
    topic: TopicCategory = Field(...)
    claim_label: str = Field(..., min_length=2, max_length=50)
    sentiment: SentimentLevel = Field(...)
    summary: str = Field(...)
    passages: List[str] = Field(..., min_length=1)

    @field_validator('claim_label')
    @classmethod
    def claim_label_words(cls, v: str) -> str:
        n = len(v.split())
        if n < 1 or n > 3:
            raise ValueError(f"claim_label must be 1-3 words: '{v}'")
        return v


class EntityMentionLLM(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    entity_name: str = Field(..., min_length=1, max_length=200)
    entity_type: EntityType = Field(...)
    claims: List[ClaimLLM] = Field(..., min_length=1)


class EntityMention(BaseModel):
    """Entity with its claims."""
    model_config = ConfigDict(use_enum_values=True)
    entity_name: str = Field(..., min_length=1, max_length=200)
    entity_type: EntityType = Field(...)
    claims: List[Claim] = Field(..., min_length=1)


class CategorizationInput(BaseModel):
    """Input fields for categorization."""
    title: str = Field(...)
    content_date: str = Field(...)
    passages: List[Dict[str, str]] = Field(..., description="Flat list: {entity_name, speaker, verbatim}")
    matched_speakers: List[str] = Field(..., description="Tracked speakers present in content (display names)")


class CategorizeContext(BaseModel):
    """Processing context for categorization operation."""
    id: str = Field(..., description="Unique identifier for the item")
    categorization_input: CategorizationInput = Field(..., description="Categorization input data")
    previous_error: Optional[str] = Field(None, description="Previous error message if retrying")
    previous_failed_output: Optional[str] = Field(None, description="Previous failed output if retrying")


class CategorizationOutputLLM(BaseModel):
    """LLM structured output."""
    entities: List[EntityMentionLLM] = Field(...)

    @field_validator('entities')
    @classmethod
    def unique_entities(cls, entities: List[EntityMentionLLM]) -> List[EntityMentionLLM]:
        entity_names = [e.entity_name.lower() for e in entities]
        if len(entity_names) != len(set(entity_names)):
            duplicates = {n for n in entity_names if entity_names.count(n) > 1}
            raise ValueError(f"Duplicate entity names: {duplicates}")
        return entities


class CategorizationOutput(BaseModel):
    """Saved output with resolved passages."""
    entities: List[EntityMention] = Field(...)

    @field_validator('entities')
    @classmethod
    def unique_entities(cls, entities: List[EntityMention]) -> List[EntityMention]:
        entity_names = [e.entity_name.lower() for e in entities]
        if len(entity_names) != len(set(entity_names)):
            duplicates = {n for n in entity_names if entity_names.count(n) > 1}
            raise ValueError(f"Duplicate entity names: {duplicates}")
        return entities


class CategorizeStageMetadata(BaseModel):
    """Metadata stored in pipeline state for categorize stage."""
    model_used: str = Field(..., description="LLM model used for categorization")
    input_tokens: int = Field(default=0, description="Input tokens used")
    output_tokens: int = Field(default=0, description="Output tokens used")


class CategorizationResult(StageOperationResult[CategorizationOutput]):
    """Result of categorization operation (artifact only, no metadata)."""
    pass