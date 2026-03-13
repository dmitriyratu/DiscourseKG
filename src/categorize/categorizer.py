"""Categorizes pre-extracted entity data into structured topics, claims, and sentiment."""

import json
from collections import defaultdict
from difflib import SequenceMatcher
from enum import Enum
from typing import List, Type

from src.categorize.config import categorization_config
from src.categorize.models import (
    Claim, EntityMention, EntityType, SentimentLevel, TopicCategory,
    CategorizationOutput, CategorizationOutputLLM, CategorizationResult, CategorizeContext, CategorizeStageMetadata,
)
from src.categorize.prompts import SYSTEM_PROMPT, USER_PROMPT
from src.shared.llm import create_client, extract_usage
from src.shared.models import TokenUsage
from src.shared.pipeline_definitions import StageResult
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)


class Categorizer:

    def __init__(self) -> None:
        self.client = create_client(
            categorization_config.LLM_MODEL,
            api_key=categorization_config.LLM_API_KEY,
        )
        self._entity_guidance = self._enum_guidance(EntityType)
        self._topic_guidance = self._enum_guidance(TopicCategory)
        self._sentiment_guidance = self._enum_guidance(SentimentLevel)

    @staticmethod
    def _enum_guidance(enum_class: Type[Enum]) -> str:
        return "\n".join(f"  {item.value}: {item.description}" for item in enum_class)

    @staticmethod
    def _group_passages(passages: List) -> List:
        groups: dict = defaultdict(list)
        for i, p in enumerate(passages):
            groups[p["entity_name"]].append({k: v for k, v in {"index": i, **p}.items() if k != "entity_name"})
        return [{"entity_name": name, "passages": ps} for name, ps in groups.items()]

    def categorize_content(self, ctx: CategorizeContext) -> StageResult:
        cat_input = ctx.categorization_input
        if not cat_input.passages:
            raise ValueError("No passages found in categorization input")

        passages_json = json.dumps(self._group_passages(cat_input.passages), indent=2)
        matched = "\n".join(f"  {name}" for name in cat_input.matched_speakers)

        system = SYSTEM_PROMPT.format(
            entity_types=self._entity_guidance,
            topic_categories=self._topic_guidance,
            sentiment_options=self._sentiment_guidance,
            matched_speakers=matched,
        )
        user = USER_PROMPT.format(
            title=cat_input.title,
            content_date=cat_input.content_date,
            matched_speakers=matched,
            passages_json=passages_json,
        )

        llm_result, completion = self.client.create_with_completion(
            response_model=CategorizationOutputLLM,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            context={"valid_speakers": cat_input.matched_speakers},
            temperature=categorization_config.LLM_TEMPERATURE,
            max_tokens=categorization_config.LLM_MAX_OUTPUT_TOKENS,
        )

        usage = extract_usage(completion)
        resolved = self._resolve(llm_result, cat_input.passages)
        logger.debug(f"Categorized {ctx.id}: {len(resolved.entities)} entities")
        return self._create_result(ctx.id, resolved, usage)

    def _resolve(self, llm_result: CategorizationOutputLLM, passages: List) -> CategorizationOutput:
        verbatims = [p["verbatim"] for p in passages]
        return CategorizationOutput(entities=[
            EntityMention(
                entity_name=e.entity_name, entity_type=e.entity_type,
                claims=[
                    Claim(
                        speaker=c.speaker, topic=c.topic, claim_label=c.claim_label,
                        sentiment=c.sentiment, summary=c.summary,
                        passages=self._dedupe([verbatims[i] for i in c.passage_indices]),
                    ) for c in e.claims
                ]
            ) for e in llm_result.entities
        ])

    @staticmethod
    def _dedupe(passages: List[str], threshold: float = 0.9) -> List[str]:
        kept = []
        for p in sorted(set(passages), key=len, reverse=True):
            if not any(p in r or SequenceMatcher(None, p, r).ratio() >= threshold for r in kept):
                kept.append(p)
        return kept

    def _create_result(self, id: str, data: CategorizationOutput, usage: TokenUsage) -> StageResult:
        artifact = CategorizationResult(id=id, success=True, data=data, error_message=None).model_dump(mode='json')
        metadata = CategorizeStageMetadata(
            model_used=categorization_config.LLM_MODEL,
            input_tokens=usage.input_tokens, output_tokens=usage.output_tokens,
        ).model_dump()
        return StageResult(artifact=artifact, metadata=metadata)
