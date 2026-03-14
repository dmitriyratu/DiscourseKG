"""Data models for categorization domain."""

from enum import Enum
from typing import Dict, List

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from src.shared.pipeline_definitions import StageOperationResult


class TopicCategory(str, Enum):
    """Broad topic categories for categorizing communications across any domain"""
    ECONOMICS = ("economics", "e.g., taxes, monetary policy, financial markets, cost of living, trade, tariffs, imports, exports")
    IMMIGRATION = ("immigration", "e.g., border security, deportation, asylum, refugees, enforcement")
    ELECTIONS = ("elections", "e.g., voting, election integrity, campaigns, ballot access, midterms")
    TECHNOLOGY = ("technology", "e.g., AI, data privacy, tech competition, innovation, tech regulation")
    FOREIGN_AFFAIRS = ("foreign_affairs", "e.g., diplomacy, international agreements, global conflicts")
    HEALTHCARE = ("healthcare", "e.g., health insurance, medical costs, public health, healthcare regulation")
    ENERGY_CLIMATE = ("energy_climate", "e.g., renewable energy, fossil fuels, climate change, environmental policy")
    DEFENSE = ("defense", "e.g., military spending, national security, military operations")
    SOCIAL = ("social", "e.g., education, welfare, social programs, inequality")
    GOVERNMENT = ("government", "e.g., federal budget, government size, bureaucracy, federal workforce, agency reform")
    LEGAL = ("legal", "e.g., court cases, lawsuits, indictments, DOJ, judicial decisions")
    MEDIA = ("media", "e.g., press coverage, specific outlets, journalists, fake news, censorship")
    PERSONNEL = ("personnel", "e.g., appointments, firings, resignations, confirmations, staffing")
    SPORTS = ("sports", "e.g., teams, athletes, games, leagues, sports events")
    OTHER = ("other", "anything else")
    
    def __new__(cls, value, description):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.description = description
        return obj


class EntityType(str, Enum):
    """Type of entity mentioned in communications"""
    ORGANIZATION = ("organization", "companies, institutions, government bodies, sports teams, political parties, etc.")
    LOCATION = ("location", "countries, regions, cities, named places, estates, etc.")
    PERSON = ("person", "individuals, public figures, etc.")
    PROGRAM = ("program", "initiatives, policies, projects, mechanisms, etc.")
    PRODUCT = ("product", "products, services, tools, platforms, weapons systems, etc.")
    EVENT = ("event", "conferences, summits, incidents, launches, etc.")
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
        if len(v.split()) > 3:
            raise ValueError(f"claim_label must be 1-3 words: '{v}'")
        return v

    @field_validator('speaker')
    @classmethod
    def validate_speaker(cls, v: str, info: ValidationInfo) -> str:
        """Instructor passes context={'valid_speakers': [...]} — reject invalid speakers on retry."""
        if info.context and (valid := info.context.get('valid_speakers')):
            if v not in valid:
                raise ValueError(f"Invalid speaker '{v}'; must be one of: {valid}")
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
        if len(v.split()) > 3:
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


class CategorizationOutputLLM(BaseModel):
    """LLM structured output."""
    entities: List[EntityMentionLLM] = Field(...)

    @field_validator('entities')
    @classmethod
    def unique_entities(cls, entities: List[EntityMentionLLM]) -> List[EntityMentionLLM]:
        names = [e.entity_name.lower() for e in entities]
        if len(names) != len(set(names)):
            duplicates = {n for n in names if names.count(n) > 1}
            raise ValueError(f"Duplicate entity names: {duplicates}")
        return entities


class CategorizationOutput(BaseModel):
    """Saved output with resolved passages."""
    entities: List[EntityMention] = Field(...)

    @field_validator('entities')
    @classmethod
    def unique_entities(cls, entities: List[EntityMention]) -> List[EntityMention]:
        names = [e.entity_name.lower() for e in entities]
        if len(names) != len(set(names)):
            duplicates = {n for n in names if names.count(n) > 1}
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
