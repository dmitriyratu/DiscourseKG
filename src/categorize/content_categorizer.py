from typing import Dict, List, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.runnables import RunnablePassthrough
from pydantic import BaseModel, Field

from src.app_config import config
from src.schemas import (
    PolicyDomain, EntityType, SentimentLevel, 
    EntityMention, CategoryWithEntities, CategorizationOutput
)
from src.shared.logging_utils import get_logger

logger = get_logger(__name__)


class ContentCategorizer:
    """
    ContentCategorizer implementation using LangChain for structured output parsing.
    
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
        
        self.llm = ChatOpenAI(**llm_kwargs)
        
        logger.info(f"ContentCategorizer initialized with model: {config.OPENAI_MODEL}")
        
        # Create output parser for structured results
        self.output_parser = PydanticOutputParser(pydantic_object=CategorizationOutput)
        
        # Create prompt template
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", """You are an expert content analyst specializing in political and business communications. 
            
            {format_instructions}
            
            ENTITY TYPE OPTIONS:
            {entity_types}
            
            SENTIMENT OPTIONS:
            {sentiment_options}
            
            POLICY DOMAINS:
            {policy_domains}
            """),
            ("user", """Analyze the following political communication and extract structured entity mentions:

TITLE: {title}
SPEAKERS: {speakers}
DATE: {date}
CONTENT: {content}

INSTRUCTIONS:
1. Identify all significant entities mentioned (people, companies, countries, policy tools)
2. For each entity, determine its type and sentiment
3. Use canonical names for entities (e.g., "Apple Inc." → "Apple", "President Biden" → "Joe Biden")
4. Only classify sentiment when clearly expressed by the speaker
5. Extract direct quotes from the original text that best illustrate how the entity was discussed

CRITICAL QUOTE EXTRACTION RULES:
   - Quotes MUST be verbatim excerpts from the original text - copy exactly as written
   - Do NOT paraphrase, summarize, or modify the original language
   - Do NOT create new text or fill in missing words
   - If a quote contains partial sentences, include ellipsis (...) to indicate truncation
   - Choose quotes that best show the speaker's sentiment or key context about the entity
   - Include 1-3 most relevant quotes per entity
   - If no direct quotes exist for an entity, use an empty quotes array []
   - Verify each quote appears exactly as written in the original text

Return structured JSON with categories containing entities and their supporting quotes.""")
        ])
        
        # Create the chain
        self.chain = (
            {
                "format_instructions": lambda x: self.output_parser.get_format_instructions(),
                "entity_types": lambda x: self._get_enum_guidance(EntityType),
                "sentiment_options": lambda x: self._get_enum_guidance(SentimentLevel),
                "policy_domains": lambda x: self._get_enum_guidance(PolicyDomain),
                "title": RunnablePassthrough(),
                "speakers": RunnablePassthrough(),
                "date": RunnablePassthrough(),
                "content": RunnablePassthrough(),
            }
            | self.prompt_template
            | self.llm
            | self.output_parser
        )
    
    def _get_enum_guidance(self, enum_class) -> str:
        """Generate guidance text from enum descriptions"""
        return "\n".join(f"  {item.value}: {item.description}" for item in enum_class)
    
    
    def categorize_content(self, content_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Categorize content from a dictionary.
        
        Args:
            content_data: Dictionary containing content to categorize
        
        Returns:
            Dictionary containing categorization results
        """
        transcript = content_data.get('transcript', '')
        title = content_data.get('title', 'Unknown')
        speakers = content_data.get('speakers', ['Unknown'])
        date = content_data.get('date', 'Unknown')
        
        if not transcript:
            raise ValueError("No transcript found in content data")
        
        try:
            logger.info(f"Starting categorization for content: {content_data.get('id', 'unknown')}")
            
            # Run the chain with all required fields
            result = self.chain.invoke({
                "content": transcript[:config.MAX_TRANSCRIPT_LENGTH],
                "title": title,
                "speakers": speakers,
                "date": date
            })
            
            # Convert to dict and add metadata
            output = result.dict()
            output['id'] = content_data.get('id', 'unknown')
            output['metadata'] = {
                'model_used': config.OPENAI_MODEL
            }
            
            
            categories_count = len(output.get('categories', []))
            entities_count = sum(len(cat.get('entities', [])) for cat in output.get('categories', []))
            
            logger.info(f"Successfully categorized content: {categories_count} categories, {entities_count} entities")
            
            return output
            
        except Exception as e:
            logger.error(f"LangChain categorization failed for content {content_data.get('id', 'unknown')}: {str(e)}")
            raise Exception(f"LangChain categorization failed: {str(e)}")
    



