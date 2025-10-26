from typing import Dict, List, Any
import time
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda

from src.app_config import config
from src.schemas import (
    TopicCategory, EntityType, SentimentLevel, 
    EntityMention, TopicMention, CategorizationInput, CategorizationOutput, CategorizationResult
)
from src.utils.logging_utils import get_logger
from src.pipeline_config import PipelineStages

logger = get_logger(__name__)


class Categorizer:
    """
    Categorizer implementation using LangChain for structured output parsing.
    
    This class handles the categorization of speech/communication data for the
    knowledge graph platform, creating a hierarchical structure of categories
    with entities and supporting quotes.
    """
    
    def __init__(self):
        
        llm_kwargs = {
            "model": config.OPENAI_MODEL,
            "temperature": config.OPENAI_TEMPERATURE,
            "max_tokens": config.OPENAI_MAX_TOKENS,
            "api_key": config.OPENAI_API_KEY
        }
        
        logger.debug(f"Categorizer initialized with model: {config.OPENAI_MODEL}")
        logger.debug(f"Using temperature: {config.OPENAI_TEMPERATURE}, max_tokens: {config.OPENAI_MAX_TOKENS}")
        logger.debug("Using structured output with automatic Pydantic validation")
        
        # Create LLM with structured output
        llm = ChatOpenAI(**llm_kwargs)
        llm_structured = llm.with_structured_output(CategorizationOutput, include_raw=False)
        
        # Create prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert content analyst specializing in communications analysis across all domains.
            
            INPUT FIELD DESCRIPTIONS:
            {field_descriptions}
            
            ENTITY TYPE OPTIONS:
            {entity_types}
            
            SENTIMENT OPTIONS:
            {sentiment_options}
            
            TOPIC CATEGORIES:
            {topic_categories}
            
            Return a JSON object with an "entities" array. Each entity should have:
            - entity_name: canonical name
            - entity_type: one of the entity types above
            - mentions: array of mention objects, ONE per unique topic
            
            Each mention object should have:
            - topic: topic category (must be unique per entity)
            - sentiment: sentiment level
            - context: summary of discussion
            - quotes: array of verbatim quotes
            """),
            ("user", """Analyze the following communication and extract structured entity mentions:

TITLE: {title}
CONTENT DATE: {content_date}
CONTENT: {content}

INSTRUCTIONS:
1. Identify all significant entities mentioned (organizations, locations, people, programs, products, events)
2. For each unique entity, determine its type
3. Use canonical names for entities (e.g., "Apple Inc." → "Apple", "President Biden" → "Joe Biden")
4. For each entity, create ONE MENTION per unique topic category where it was discussed
5. If an entity is discussed in multiple topics, include multiple mention objects within that entity's mentions array
6. Only classify sentiment when clearly expressed by the speaker

OUTPUT STRUCTURE:
- Group by entity (not by topic)
- Each entity appears once with a mentions array
- Each mention represents one topic where that entity was discussed
- Sentiment/context/quotes are specific to each topic mention

CRITICAL QUOTE EXTRACTION RULES:
   - Quotes MUST be verbatim excerpts from the original text - copy exactly as written
   - Do NOT paraphrase, summarize, or modify the original language
   - Choose quotes that best show the speaker's sentiment or key context about the entity
   - Include 1-3 most relevant quotes per mention
   - If no direct quotes exist, use an empty quotes array []

Return structured JSON with entities containing their topic mentions.

CRITICAL: Each entity must have EXACTLY ONE mention per unique topic. Do not repeat topics for the same entity.""")
        ])
        
        # Create LCEL chain with automatic enum guidance injection
        self.chain = (
            {
                "field_descriptions": RunnableLambda(lambda _: self._get_field_guidance()),
                "entity_types": RunnableLambda(lambda _: self._get_enum_guidance(EntityType)),
                "sentiment_options": RunnableLambda(lambda _: self._get_enum_guidance(SentimentLevel)),
                "topic_categories": RunnableLambda(lambda _: self._get_enum_guidance(TopicCategory)),
                "title": lambda x: x["title"],
                "content_date": lambda x: x["content_date"],
                "content": lambda x: x["content"][:config.MAX_TRANSCRIPT_LENGTH]
            }
            | prompt
            | llm_structured
        )
    
    def _get_enum_guidance(self, enum_class) -> str:
        """Generate guidance text from enum descriptions"""
        return "\n".join(f"  {item.value}: {item.description}" for item in enum_class)
    
    def _get_field_guidance(self) -> str:
        """Generate guidance text from CategorizationInput schema"""
        return "\n".join(f"  {name}: {field.description}" 
                        for name, field in CategorizationInput.model_fields.items())
    
    def categorize_content(self, processing_context: Dict[str, Any]) -> Dict[str, Any]:
        """Categorize content from processing context."""
        start_time = time.time()
        
        # Extract what we need from the processing context
        id = processing_context['id']
        categorization_input = processing_context['categorization_input']
        
        if not categorization_input.content:
            raise ValueError("No content found in categorization input")
        
        try:
            logger.debug(f"Starting categorization for content (id: {id})")
            logger.debug(f"Processing content: {len(categorization_input.content)} chars, truncated to {config.MAX_TRANSCRIPT_LENGTH}")
            
            # Invoke chain with structured output (automatic validation & retry)
            result = self.chain.invoke({
                "title": categorization_input.title,
                "content_date": categorization_input.content_date,
                "content": categorization_input.content
            })
            
            logger.debug(f"LLM response received: {len(result.entities)} entities")
            
            return self._create_result(id, result)
            
        except Exception as e:
            logger.error(f"LangChain categorization failed: {str(e)}", 
                        extra={'stage': PipelineStages.CATEGORIZE.value, 
                               'error_type': 'langchain_error', 'content_length': len(categorization_input.content)})
            # Let exception bubble up to flow processor
            raise
    
    def _create_result(self, id: str, categorization_data: CategorizationOutput) -> Dict[str, Any]:
        """Helper to create CategorizationResult."""
        categorization_result = CategorizationResult(
            id=id,
            success=True,
            data=categorization_data,
            metadata={
                'model_used': config.OPENAI_MODEL
            }
        )
        
        entities_count = len(categorization_result.data.entities)
        mentions_count = sum(len(entity.mentions) for entity in categorization_result.data.entities)
        
        logger.debug(f"Successfully categorized content: {entities_count} entities, {mentions_count} mentions")
        
        return categorization_result.model_dump()