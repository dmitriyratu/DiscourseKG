"""Two-phase extractor: entity extraction then parallel passage extraction."""

from collections import defaultdict
from difflib import SequenceMatcher
from enum import Enum
from typing import List, Set

from langchain.chat_models import init_chat_model
from langchain_core.callbacks import get_usage_metadata_callback
from langchain_core.prompts import ChatPromptTemplate
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import Field, create_model

from src.extract.config import extraction_config
from src.extract.models import (
    EntityListOutput, ExtractionOutput, ExtractionResult,
    ExtractContext, ExtractedEntity, ExtractStageMetadata,
)
from src.extract.prompts import (
    ENTITY_SYSTEM_PROMPT, ENTITY_USER_PROMPT,
    PASSAGE_SYSTEM_PROMPT, PASSAGE_USER_PROMPT,
)
from src.shared.prompts import CANONICAL_NAMING_RULE
from src.shared.models import ContentType, TokenUsage
from src.shared.pipeline_definitions import StageResult
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)

DEDUP_THRESHOLD = 0.85


class Extractor:
    """Extracts entities and passages via two-phase parallel processing."""

    def __init__(self) -> None:
        self.llm = init_chat_model(
            extraction_config.LLM_MODEL,
            temperature=extraction_config.LLM_TEMPERATURE,
            max_tokens=extraction_config.LLM_MAX_OUTPUT_TOKENS,
            timeout=extraction_config.LLM_TIMEOUT,
            max_retries=extraction_config.LLM_MAX_RETRIES,
            api_key=extraction_config.LLM_API_KEY,
        )
        content_types_str = ", ".join(ct.value for ct in ContentType)

        entity_prompt = ChatPromptTemplate.from_messages([
            ("system", ENTITY_SYSTEM_PROMPT),
            ("user", ENTITY_USER_PROMPT),
        ])
        self.entity_chain = (
            {
                "content_types": lambda _: content_types_str,
                "canonical_naming_rule": lambda _: CANONICAL_NAMING_RULE,
                "content": lambda x: x["content"],
            }
            | entity_prompt
            | self.llm.with_structured_output(EntityListOutput, include_raw=True)
        )

        self.passage_prompt = ChatPromptTemplate.from_messages([
            ("system", PASSAGE_SYSTEM_PROMPT),
            ("user", PASSAGE_USER_PROMPT),
        ])
        self._passage_input_map = {
            "content_types": lambda _: content_types_str,
            "canonical_naming_rule": lambda _: CANONICAL_NAMING_RULE,
            "entity_list": lambda x: x["entity_list"],
            "content": lambda x: x["content"],
        }

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=extraction_config.CHUNK_SIZE,
            chunk_overlap=extraction_config.CHUNK_OVERLAP,
            separators=["\n\n", "\n", " "],
        )

    @staticmethod
    def _passage_schema(entity_list: EntityListOutput) -> type | None:
        """Pydantic model for Phase 2; entity_name constrained to Phase 1 whitelist."""
        valid_names = list(dict.fromkeys(e.strip() for e in entity_list.entities if e.strip()))
        if not valid_names:
            return None
        entity_enum = Enum("EntityNameEnum", [(f"e_{i}", n) for i, n in enumerate(valid_names)], type=str)
        entity_model = create_model("PassageEntity", entity_name=(entity_enum, Field(...)), passages=(List[str], Field(..., min_length=1)))
        return create_model("PassageOutput", entities=(List[entity_model], Field(default_factory=list)))

    def extract_entities(self, context: ExtractContext) -> StageResult:
        """Two-phase extraction: extract entity list, then parallel passage extraction per chunk."""
        if not context.content:
            raise ValueError("No content found in extraction input")

        total_usage = TokenUsage()

        # Phase 1: entity extraction (single call, full text)
        logger.info(f"Phase 1 starting for {context.id}")
        entity_list, usage = self._extract_entity_list(context.content)
        total_usage.input_tokens += usage.input_tokens
        total_usage.output_tokens += usage.output_tokens
        logger.info(f"Phase 1 complete — {len(entity_list.entities)} entities for {context.id}")

        if not entity_list.entities:
            return self._create_result(
                context.id,
                ExtractionOutput(entities=[], entity_whitelist=[]),
                total_usage,
            )

        # Post-process: omit active speakers from entity list (from filter stage)
        speakers = set(context.active_speakers)
        entity_list = self._filter_speakers(entity_list, speakers)
        if not entity_list.entities:
            return self._create_result(
                context.id,
                ExtractionOutput(entities=[], entity_whitelist=[]),
                total_usage,
            )
        logger.debug(f"Filtered to {len(entity_list.entities)} entities (excluded {len(speakers)} speakers)")

        # Phase 2: parallel passage extraction per chunk
        chunks = self.splitter.split_text(context.content)
        logger.info(f"Phase 2 starting for {context.id} ({len(chunks)} chunks)")
        if len(chunks) > 1:
            logger.debug(f"Phase 2 chunking {context.id}: {len(context.content)} chars -> {len(chunks)} chunks")

        chunk_results, chunk_usage = self._extract_passages_parallel(chunks, entity_list)
        total_usage.input_tokens += chunk_usage.input_tokens
        total_usage.output_tokens += chunk_usage.output_tokens

        merged = self._merge(chunk_results, entity_list)
        logger.info(f"Phase 2 complete — {len(merged.entities)} entities with passages for {context.id}")

        output = ExtractionOutput(
            entities=merged.entities,
            entity_whitelist=entity_list.entities,
        )
        return self._create_result(context.id, output, total_usage)

    def _extract_entity_list(self, content: str) -> tuple[EntityListOutput, TokenUsage]:
        with get_usage_metadata_callback() as usage_cb:
            response = self.entity_chain.invoke({"content": content})
            raw = next(iter(usage_cb.usage_metadata.values()), {})
            usage = TokenUsage(
                input_tokens=raw.get("input_tokens", 0),
                output_tokens=raw.get("output_tokens", 0),
            )
            parsed = response["parsed"]
            parsed = EntityListOutput(entities=list(set(parsed.entities)))
            return parsed, usage

    def _extract_passages_parallel(
        self,
        chunks: List[str],
        entity_list: EntityListOutput,
    ) -> tuple[list[ExtractionOutput], TokenUsage]:
        schema = self._passage_schema(entity_list)
        if schema is None:
            return [], TokenUsage()

        passage_chain = (
            self._passage_input_map
            | self.passage_prompt
            | self.llm.with_structured_output(schema, include_raw=True)
        )

        entity_list_str = "\n".join(f"  - {e}" for e in entity_list.entities)
        inputs = [
            {"entity_list": entity_list_str, "content": chunk}
            for chunk in chunks
        ]

        with get_usage_metadata_callback() as usage_cb:
            responses = passage_chain.batch(
                inputs,
                config={"max_concurrency": extraction_config.MAX_CONCURRENT_CHUNKS},
            )
            raw = next(iter(usage_cb.usage_metadata.values()), {})
            usage = TokenUsage(
                input_tokens=raw.get("input_tokens", 0),
                output_tokens=raw.get("output_tokens", 0),
            )

        results = []
        for r in responses:
            parsed = r["parsed"]
            entities = [
                ExtractedEntity(entity_name=e.entity_name.value, passages=e.passages)
                for e in parsed.entities
            ]
            results.append(ExtractionOutput(entities=entities))
        return results, usage

    def _merge(self, chunk_results: List[ExtractionOutput], allowed_entities: EntityListOutput) -> ExtractionOutput:
        """Merge chunk results: group by entity name, fuzzy-dedup passages."""
        passages_by_entity: dict[str, list[str]] = defaultdict(list)
        
        valid_entity_names = {e.strip() for e in allowed_entities.entities}

        for result in chunk_results:
            for entity in result.entities:
                if entity.entity_name not in valid_entity_names:
                    logger.info(f"Discarding hallucinated entity from Phase 2: {entity.entity_name}")
                    continue
                    
                existing = passages_by_entity[entity.entity_name]
                for passage in entity.passages:
                    if not self._is_duplicate(passage, existing):
                        existing.append(passage)

        entities = [
            ExtractedEntity(entity_name=name, passages=passages)
            for name, passages in passages_by_entity.items()
            if passages
        ]
        return ExtractionOutput(entities=entities)

    @staticmethod
    def _filter_speakers(entity_list: EntityListOutput, speakers: Set[str]) -> EntityListOutput:
        """Remove entities that are active speakers in the transcript."""
        filtered = [e for e in entity_list.entities if e.strip() not in speakers]
        return EntityListOutput(entities=filtered)

    @staticmethod
    def _is_duplicate(candidate: str, existing: List[str]) -> bool:
        return any(
            SequenceMatcher(None, candidate, e).ratio() > DEDUP_THRESHOLD
            for e in existing
        )

    def _create_result(self, id: str, data: ExtractionOutput, token_usage: TokenUsage) -> StageResult:
        artifact = ExtractionResult(
            id=id, success=True, data=data, error_message=None
        )
        metadata = ExtractStageMetadata(
            model_used=extraction_config.LLM_MODEL,
            input_tokens=token_usage.input_tokens,
            output_tokens=token_usage.output_tokens,
        ).model_dump()
        logger.debug(f"Extracted {len(data.entities)} entities for {id}")
        return StageResult(artifact=artifact.model_dump(mode='json'), metadata=metadata)
