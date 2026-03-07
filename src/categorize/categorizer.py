import json
from enum import Enum
from typing import Dict, Optional, Type

from langchain.chat_models import init_chat_model
from langchain_core.callbacks import get_usage_metadata_callback
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from pydantic import ValidationError

from src.categorize.config import categorization_config
from src.categorize.models import (
    TopicCategory, EntityType, SentimentLevel, CategorizationOutput,
    CategorizationResult, CategorizeContext, CategorizeStageMetadata,
)
from src.shared.models import TokenUsage, LLMValidationError
from src.shared.pipeline_definitions import StageResult
from src.categorize.prompts import SYSTEM_PROMPT, USER_PROMPT
from src.shared.prompts import CANONICAL_NAMING_RULE
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)


class Categorizer:
    """Categorizes pre-extracted entity data into structured topics, claims, and sentiment."""

    def __init__(self) -> None:
        llm = init_chat_model(
            categorization_config.LLM_MODEL,
            temperature=categorization_config.LLM_TEMPERATURE,
            max_tokens=categorization_config.LLM_MAX_OUTPUT_TOKENS,
            timeout=categorization_config.LLM_TIMEOUT,
            max_retries=categorization_config.LLM_MAX_RETRIES,
            api_key=categorization_config.LLM_API_KEY,
        )
        logger.debug(f"Categorizer initialized with model: {categorization_config.LLM_MODEL}")
        llm_structured = llm.with_structured_output(CategorizationOutput, include_raw=True)

        entity_guidance = self._get_enum_guidance(EntityType)
        topic_guidance = self._get_enum_guidance(TopicCategory)
        sentiment_guidance = self._get_enum_guidance(SentimentLevel)

        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("user", USER_PROMPT)
        ])

        self.chain = (
            {
                "entity_types": RunnableLambda(lambda _: entity_guidance),
                "sentiment_options": RunnableLambda(lambda _: sentiment_guidance),
                "topic_categories": RunnableLambda(lambda _: topic_guidance),
                "matched_speakers": lambda x: x["matched_speakers"],
                "canonical_naming_rule": lambda _: CANONICAL_NAMING_RULE,
                "title": lambda x: x["title"],
                "content_date": lambda x: x["content_date"],
                "entities_json": lambda x: x["entities_json"],
                "previous_error_text": lambda x: x.get("previous_error_text", ""),
            }
            | prompt
            | llm_structured
        )

    def _get_enum_guidance(self, enum_class: Type[Enum]) -> str:
        return "\n".join(f"  {item.value}: {item.description}" for item in enum_class)

    def _format_matched_speakers(self, matched_speakers: Dict[str, str]) -> str:
        return "\n".join(f"  {sid}: {name}" for sid, name in matched_speakers.items())

    def _validate_speaker_ids(self, result: CategorizationOutput, valid_ids: Dict[str, str]) -> None:
        valid = set(valid_ids)
        invalid = [t.speaker for e in result.entities for t in e.topics if t.speaker not in valid]
        if invalid:
            raise ValueError(
                f"LLM used invalid speaker IDs {set(invalid)}; valid: {list(valid)}. "
                "Use exact speaker_id from TRACKED SPEAKERS."
            )

    def _format_error_text(self, error_message: Optional[str] = None, failed_output: Optional[str] = None) -> str:
        if not error_message:
            return ""
        parts = ["\n\n*** PREVIOUS ATTEMPT FAILED ***\n\n"]
        if failed_output:
            parts.append(f"Your previous output:\n{failed_output}\n\n")
        parts.append(f"Validation error:\n{error_message}\n\n")
        parts.append("Fix the validation errors and try again. Keep all correct parts and only fix what's wrong.\n")
        return "".join(parts)

    def categorize_content(self, processing_context: CategorizeContext) -> StageResult:
        """Categorize pre-extracted entities in a single LLM call."""
        id = processing_context.id
        cat_input = processing_context.categorization_input

        if not cat_input.entities:
            raise ValueError("No entities found in categorization input")

        if processing_context.previous_error:
            logger.info(f"Retrying categorization for {id}")

        entities_json = json.dumps(
            [e.model_dump(mode="json") for e in cat_input.entities],
            indent=2,
        )

        result, usage = self._invoke(
            title=cat_input.title,
            content_date=cat_input.content_date,
            matched_speakers=cat_input.matched_speakers,
            entities_json=entities_json,
            previous_error=processing_context.previous_error,
            previous_failed_output=processing_context.previous_failed_output,
        )

        return self._create_result(id, result, usage)

    def _invoke(
        self,
        title: str,
        content_date: str,
        matched_speakers: Dict[str, str],
        entities_json: str,
        previous_error: Optional[str] = None,
        previous_failed_output: Optional[str] = None,
    ) -> tuple[CategorizationOutput, TokenUsage]:
        """Invoke chain once. Returns (parsed result, token_usage)."""
        with get_usage_metadata_callback() as usage_cb:
            response = None
            try:
                response = self.chain.invoke({
                    "matched_speakers": self._format_matched_speakers(matched_speakers),
                    "title": title,
                    "content_date": content_date,
                    "entities_json": entities_json,
                    "previous_error_text": self._format_error_text(previous_error, previous_failed_output),
                })
                self._validate_speaker_ids(response["parsed"], matched_speakers)
                raw = next(iter(usage_cb.usage_metadata.values()), {})
                usage = TokenUsage(
                    input_tokens=raw.get("input_tokens", 0),
                    output_tokens=raw.get("output_tokens", 0),
                )
                return response["parsed"], usage
            except (ValidationError, ValueError) as e:
                raw_content = response["raw"].content if response and response.get("raw") else None
                raise LLMValidationError(str(e), failed_output=raw_content)

    def _create_result(self, id: str, categorization_data: CategorizationOutput, token_usage: TokenUsage) -> StageResult:
        artifact = CategorizationResult(
            id=id, success=True, data=categorization_data, error_message=None
        )
        metadata = CategorizeStageMetadata(
            model_used=categorization_config.LLM_MODEL,
            input_tokens=token_usage.input_tokens,
            output_tokens=token_usage.output_tokens,
        ).model_dump()
        logger.debug(f"Successfully categorized: {len(categorization_data.entities)} entities")
        return StageResult(artifact=artifact.model_dump(mode='json'), metadata=metadata)
