from enum import Enum
from typing import Any, Dict, Optional, Type
import json
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from pydantic import ValidationError

from src.categorize.config import categorization_config
from src.categorize.models import (
    TopicCategory, EntityType, SentimentLevel, 
    EntityMention, TopicMention, Subject, CategorizationInput, CategorizationOutput,
    CategorizationResult, CategorizeContext, CategorizeStageMetadata
)
from src.utils.logging_utils import get_logger
from src.shared.pipeline_definitions import PipelineStages, StageResult
from src.categorize.prompts import SYSTEM_PROMPT, USER_PROMPT

logger = get_logger(__name__)


class Categorizer:
    """
    Categorizer implementation using LangChain for structured output parsing.
    
    This class handles the categorization of speech/communication data for the
    knowledge graph platform, creating a hierarchical structure of categories
    with entities and supporting quotes.
    """
    
    def __init__(self) -> None:
        llm_kwargs = {
            "model": categorization_config.OPENAI_MODEL,
            "temperature": categorization_config.OPENAI_TEMPERATURE,
            "max_tokens": categorization_config.OPENAI_MAX_OUTPUT_TOKENS,
            "api_key": categorization_config.OPENAI_API_KEY,
            "timeout": categorization_config.OPENAI_TIMEOUT,
            "max_retries": categorization_config.OPENAI_MAX_RETRIES,
        }
        
        logger.debug(f"Categorizer initialized with model: {categorization_config.OPENAI_MODEL}")
        logger.debug(f"Using temperature: {categorization_config.OPENAI_TEMPERATURE}, max_output_tokens: {categorization_config.OPENAI_MAX_OUTPUT_TOKENS}")
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
                "output_budget_tokens": lambda _: categorization_config.OPENAI_MAX_OUTPUT_TOKENS,
                "title": lambda x: x["title"],
                "content_date": lambda x: x["content_date"],
                "content": lambda x: x["content"],
                "previous_error_text": lambda x: self._format_error_text(
                    x.get("previous_error"), 
                    x.get("previous_failed_output")
                )
            }
            | prompt
            | llm_structured
        )
    
    def _get_enum_guidance(self, enum_class: Type[Enum]) -> str:
        """Generate guidance text from enum descriptions"""
        return "\n".join(f"  {item.value}: {item.description}" for item in enum_class)
    
    def _get_field_guidance(self) -> str:
        """Generate guidance text from CategorizationInput schema"""
        return "\n".join(f"  {name}: {field.description}" 
                        for name, field in CategorizationInput.model_fields.items())
    
    def _format_error_text(self, error_message: Optional[str] = None, failed_output: Optional[str] = None) -> str:
        """Format previous error message and failed output for the prompt"""
        if not error_message:
            return ""
        
        error_context = "\n\n*** PREVIOUS ATTEMPT FAILED ***\n\n"
        
        # Include the failed output if available
        if failed_output:
            try:
                if isinstance(failed_output, str):
                    formatted_output = failed_output
                else:
                    formatted_output = json.dumps(failed_output, indent=2)
                
                error_context += f"Your previous output:\n{formatted_output}\n\n"
            except Exception as e:
                logger.warning(f"Failed to format failed_output: {e}")
        
        error_context += f"Validation error:\n{error_message}\n\n"
        error_context += "Fix the validation errors and try again. Keep all correct parts and only fix what's wrong.\n"
        
        return error_context
    
    def categorize_content(self, processing_context: CategorizeContext) -> StageResult:
        """Categorize content from processing context."""
        
        # Extract what we need from the processing context
        id = processing_context.id
        categorization_input = processing_context.categorization_input
        previous_error = processing_context.previous_error
        previous_failed_output = processing_context.previous_failed_output
        
        if not categorization_input.content:
            raise ValueError("No content found in categorization input")
        
        response = None  # Initialize for exception handling
        try:
            if previous_error:
                logger.info(f"Retrying categorization for {id}: has_failed_output={bool(previous_failed_output)}")
            logger.debug(f"Starting categorization for content (id: {id})")
            logger.debug(f"Processing content: {len(categorization_input.content)} chars")
            
            # Invoke chain with structured output (automatic validation & retry)
            response = self.chain.invoke({
                "title": categorization_input.title,
                "content_date": categorization_input.content_date,
                "content": categorization_input.content,
                "previous_error": previous_error,
                "previous_failed_output": previous_failed_output
            })
            
            # Extract parsed result and token usage
            result = response["parsed"]
            raw_response = response["raw"]
            
            # Extract token usage
            token_usage = {}
            if usage := getattr(raw_response, 'usage_metadata', None):
                token_usage = {k: usage.get(k, 0) for k in ['input_tokens', 'output_tokens']}
                logger.info(f"LLM token usage for {id}: {token_usage}")
            
            logger.debug(f"LLM response received: {len(result.entities)} entities")
            
            return self._create_result(id, result, token_usage)
            
        except ValidationError as e:
            # Attach failed output to exception for retry context
            if response and response.get('raw'):
                e.failed_output = response['raw'].content
                failed_output_length = len(str(e.failed_output)) if e.failed_output else 0
                logger.info(f"Captured failed output for {id} ({failed_output_length} chars) - will be available on retry")
            else:
                e.failed_output = None
                logger.warning(f"No raw output available to capture for {id}")
            
            logger.error(f"Validation error for {id}: {str(e)}", 
                        extra={'stage': PipelineStages.CATEGORIZE.value, 
                               'error_type': 'validation_error', 
                               'content_length': len(categorization_input.content)})
            raise
    
    def _create_result(self, id: str, categorization_data: CategorizationOutput, token_usage: Dict[str, int] = {}) -> StageResult:
        """Helper to create StageResult with separated artifact and metadata."""
        # Build artifact (what gets persisted)
        artifact = CategorizationResult(
            id=id,
            success=True,
            data=categorization_data,
            error_message=None
        )
        
        # Extract metadata (for state updates only)
        metadata = CategorizeStageMetadata(
            model_used=categorization_config.OPENAI_MODEL,
            input_tokens=token_usage.get('input_tokens', 0),
            output_tokens=token_usage.get('output_tokens', 0)
        ).model_dump()
        
        entities_count = len(categorization_data.entities)
        mentions_count = sum(len(entity.mentions) for entity in categorization_data.entities)
        
        logger.debug(f"Successfully categorized content: {entities_count} entities, {mentions_count} mentions")
        
        return StageResult(artifact=artifact.model_dump(), metadata=metadata)