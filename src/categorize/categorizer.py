import json
from difflib import SequenceMatcher
from enum import Enum
from typing import Dict, List, Optional, Type

from langchain.chat_models import init_chat_model
from langchain_core.callbacks import get_usage_metadata_callback
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from pydantic import ValidationError

from src.categorize.config import categorization_config
from src.categorize.models import (
    Claim, EntityMention, EntityType, SentimentLevel, TopicCategory,
    CategorizationOutput, CategorizationOutputLLM, CategorizationResult, CategorizeContext, CategorizeStageMetadata,
)
from src.shared.models import TokenUsage, LLMValidationError
from src.shared.pipeline_definitions import StageResult
from src.categorize.prompts import SYSTEM_PROMPT, USER_PROMPT
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
        llm_structured = llm.with_structured_output(CategorizationOutputLLM, include_raw=True)

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
                "title": lambda x: x["title"],
                "content_date": lambda x: x["content_date"],
                "passages_json": lambda x: x["passages_json"],
                "previous_error_text": lambda x: x.get("previous_error_text", ""),
            }
            | prompt
            | llm_structured
        )

    def _get_enum_guidance(self, enum_class: Type[Enum]) -> str:
        return "\n".join(f"  {item.value}: {item.description}" for item in enum_class)

    def _format_matched_speakers(self, matched_speakers: List[str]) -> str:
        return "\n".join(f"  {name}" for name in matched_speakers)

    def _validate_speakers(self, result: CategorizationOutput, valid_speakers: List[str]) -> None:
        valid = set(valid_speakers)
        invalid = [c.speaker for e in result.entities for c in e.claims if c.speaker not in valid]
        if invalid:
            raise ValueError(
                f"LLM used invalid speakers {set(invalid)}; valid: {list(valid)}. "
                "Use exact display name from TRACKED SPEAKERS."
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

        if not cat_input.passages:
            raise ValueError("No passages found in categorization input")

        if processing_context.previous_error:
            logger.info(f"Retrying categorization for {id}")

        passages_json = json.dumps([{"index": i, **p} for i, p in enumerate(cat_input.passages)], indent=2)

        llm_result, usage = self._invoke(
            title=cat_input.title,
            content_date=cat_input.content_date,
            matched_speakers=cat_input.matched_speakers,
            passages_json=passages_json,
            previous_error=processing_context.previous_error,
            previous_failed_output=processing_context.previous_failed_output,
        )

        resolved = self._resolve_passage_indices(llm_result, cat_input.passages)
        return self._create_result(id, resolved, usage)

    def _invoke(
        self,
        title: str,
        content_date: str,
        matched_speakers: List[str],
        passages_json: str,
        previous_error: Optional[str] = None,
        previous_failed_output: Optional[str] = None,
    ) -> tuple[CategorizationOutputLLM, TokenUsage]:
        """Invoke chain once. Returns (parsed result, token_usage)."""
        with get_usage_metadata_callback() as usage_cb:
            response = None
            try:
                response = self.chain.invoke({
                    "matched_speakers": self._format_matched_speakers(matched_speakers),
                    "title": title,
                    "content_date": content_date,
                    "passages_json": passages_json,
                    "previous_error_text": self._format_error_text(previous_error, previous_failed_output),
                })
                self._validate_speakers(response["parsed"], matched_speakers)
                raw = next(iter(usage_cb.usage_metadata.values()), {})
                usage = TokenUsage(
                    input_tokens=raw.get("input_tokens", 0),
                    output_tokens=raw.get("output_tokens", 0),
                )
                return response["parsed"], usage
            except (ValidationError, ValueError) as e:
                raw_content = response["raw"].content if response and response.get("raw") else None
                raise LLMValidationError(str(e), failed_output=raw_content)

    def _dedupe_passages(self, passages: List[str], threshold: float = 0.9) -> List[str]:
        """Drop passages that are substrings of or similar to a longer one."""
        kept = []
        for p in sorted(set(passages), key=len, reverse=True):
            if not any(p in r or SequenceMatcher(None, p, r).ratio() >= threshold for r in kept):
                kept.append(p)
        return kept

    def _resolve_passage_indices(self, llm_result: CategorizationOutputLLM, passages: List) -> CategorizationOutput:
        verbatims = [p["verbatim"] for p in passages]
        return CategorizationOutput(entities=[
            EntityMention(
                entity_name=e.entity_name,
                entity_type=e.entity_type,
                claims=[
                    Claim(
                        speaker=c.speaker,
                        topic=c.topic,
                        claim_label=c.claim_label,
                        sentiment=c.sentiment,
                        summary=c.summary,
                        passages=self._dedupe_passages([verbatims[i] for i in c.passage_indices]),
                    )
                    for c in e.claims
                ]
            )
            for e in llm_result.entities
        ])

    def _create_result(self, id: str, categorization_data: CategorizationOutput, token_usage: TokenUsage) -> StageResult:
        artifact = CategorizationResult(
            id=id, success=True, data=categorization_data, error_message=None
        ).model_dump(mode='json')
        metadata = CategorizeStageMetadata(
            model_used=categorization_config.LLM_MODEL,
            input_tokens=token_usage.input_tokens,
            output_tokens=token_usage.output_tokens,
        ).model_dump()
        logger.debug(f"Successfully categorized: {len(categorization_data.entities)} entities")
        return StageResult(artifact=artifact, metadata=metadata)
