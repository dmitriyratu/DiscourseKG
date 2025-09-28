"""
Data schemas for political communication categorization and sentiment analysis.

This module defines the core data structures used throughout the KG-Sentiment platform
for categorizing political communications, extracting entities, and analyzing sentiment.
"""

from pydantic import BaseModel, Field, constr
from enum import Enum
from typing import Optional


# ============================================================================
# ENUMS - Core Classification Types
# ============================================================================

class PolicyDomain(str, Enum):
    """Broad policy areas for categorizing communications"""
    ECONOMIC_POLICY = "economic_policy"
    TECHNOLOGY_POLICY = "technology_policy" 
    FOREIGN_RELATIONS = "foreign_relations"
    HEALTHCARE_POLICY = "healthcare_policy"
    ENERGY_POLICY = "energy_policy"
    DEFENSE_POLICY = "defense_policy"
    SOCIAL_POLICY = "social_policy"
    REGULATORY_POLICY = "regulatory_policy"


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


class ProminenceLevel(str, Enum):
    """How much attention this entity received"""
    PRIMARY = ("primary", "main subject (20%+ of content)")
    SECONDARY = ("secondary", "significant mention (5-20% of content)")
    MENTIONED = ("mentioned", "clear mention (<5% of content)")
    BRIEF = ("brief", "passing reference only")
    
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
    
    entity_name: constr(min_length=1, max_length=200, strip_whitespace=True) = Field(
        ..., 
        description="Canonical/standard name for this entity (e.g., 'Apple', 'China', 'Joe Biden')"
    )
    
    entity_type: EntityType = Field(..., description="Type of entity")
    
    sentiment: SentimentLevel = Field(..., description="Speaker's feeling toward entity")
    
    prominence: ProminenceLevel = Field(..., description="How much attention entity received")
    
    is_market_relevant: bool = Field(default=False, description="Could this impact markets?")
    
    context: constr(min_length=10, max_length=500, strip_whitespace=True) = Field(
        ..., 
        description="How this entity was discussed"
    )
