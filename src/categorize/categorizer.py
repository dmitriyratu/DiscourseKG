from typing import Dict, List, Any
import time
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda

from src.app_config import config
from src.schemas import (
    TopicCategory, EntityType, SentimentLevel, 
    EntityMention, TopicMention, Subject, CategorizationInput, CategorizationOutput, CategorizationResult,
    SentimentAggregation
)
from src.utils.logging_utils import get_logger
from src.pipeline_config import PipelineStages
from src.categorize.prompts import SYSTEM_PROMPT, USER_PROMPT

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
        llm_structured = llm.with_structured_output(CategorizationOutput, include_raw=True)
        
        # Create prompt template from separate prompt file
        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("user", USER_PROMPT)
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
                "content": lambda x: x["content"][:config.MAX_TRANSCRIPT_LENGTH],
                "previous_error_text": lambda x: self._format_error_text(x.get("previous_error"))
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
    
    def _format_error_text(self, error_message: str = None) -> str:
        """Format previous error message for the prompt"""
        if not error_message:
            return ""
        return f"\n\n*** PREVIOUS ATTEMPT FAILED WITH ERROR:\n{error_message}\n\nPlease correct this error in your response. ***\n"
    
    def _compute_aggregated_sentiment(self, categorization_output: CategorizationOutput) -> CategorizationOutput:
        """Compute aggregated sentiment for each topic mention from its subjects"""
        for entity in categorization_output.entities:
            for mention in entity.mentions:
                # Count sentiments
                sentiment_counts = {}
                for subject in mention.subjects:
                    sentiment_value = subject.sentiment.value
                    sentiment_counts[sentiment_value] = sentiment_counts.get(sentiment_value, 0) + 1
                
                # Calculate proportions and create aggregation
                total_subjects = len(mention.subjects)
                mention.aggregated_sentiment = {
                    sentiment: SentimentAggregation(
                        count=count,
                        prop=round(count / total_subjects, 3)
                    )
                    for sentiment, count in sentiment_counts.items()
                }
        
        return categorization_output
    
    def categorize_content(self, processing_context: Dict[str, Any]) -> Dict[str, Any]:
        """Categorize content from processing context."""
        start_time = time.time()
        
        # Extract what we need from the processing context
        id = processing_context['id']
        categorization_input = processing_context['categorization_input']
        previous_error = processing_context.get('previous_error')
        
        if not categorization_input.content:
            raise ValueError("No content found in categorization input")
        
        try:
            if previous_error:
                logger.info(f"Retrying categorization with previous error context for id: {id}")
            logger.debug(f"Starting categorization for content (id: {id})")
            logger.debug(f"Processing content: {len(categorization_input.content)} chars, truncated to {config.MAX_TRANSCRIPT_LENGTH}")
            
            # Invoke chain with structured output (automatic validation & retry)
            response = self.chain.invoke({
                "title": categorization_input.title,
                "content_date": categorization_input.content_date,
                "content": categorization_input.content,
                "previous_error": previous_error
            })
            
            # Extract parsed result and token usage
            result = response["parsed"]
            raw_response = response["raw"]
            
            # Log token usage if available
            if hasattr(raw_response, 'usage_metadata') and raw_response.usage_metadata:
                usage = raw_response.usage_metadata
                input_tokens = usage.get('input_tokens', 0)
                output_tokens = usage.get('output_tokens', 0)
                total_tokens = usage.get('total_tokens', 0)
                
                logger.info(f"LLM token usage for {id}: input={input_tokens}, output={output_tokens}, total={total_tokens}")
            
            logger.debug(f"LLM response received: {len(result.entities)} entities")
            
            # Compute aggregated sentiment from subjects
            result = self._compute_aggregated_sentiment(result)
            
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