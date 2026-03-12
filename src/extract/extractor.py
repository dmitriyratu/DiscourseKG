"""Two-phase extractor: speaker-entity attribution then parallel passage extraction."""

from collections import defaultdict
from difflib import SequenceMatcher
from enum import Enum
from typing import Dict, List, Optional

from langchain.chat_models import init_chat_model
from langchain_core.callbacks import get_usage_metadata_callback
from langchain_core.prompts import ChatPromptTemplate
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import Field, create_model

from src.extract.config import extraction_config
from src.extract.models import (
    ExtractionOutput, ExtractionResult, ExtractContext,
    ExtractStageMetadata, Passage, SpeakerEntityMap,
)
from src.extract.prompts import (
    ENTITY_SYSTEM_PROMPT, ENTITY_USER_PROMPT,
    PASSAGE_SYSTEM_PROMPT, PASSAGE_USER_PROMPT,
)
from src.shared.models import TokenUsage
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

        entity_prompt = ChatPromptTemplate.from_messages([
            ("system", ENTITY_SYSTEM_PROMPT),
            ("user", ENTITY_USER_PROMPT),
        ])
        self.entity_chain = (
            {
                "content_type": lambda x: x["content_type"],
                "matched_speakers": lambda x: x["matched_speakers"],
                "content": lambda x: x["content"],
                "previous_error_text": lambda x: x.get("previous_error_text", ""),
            }
            | entity_prompt
            | self.llm.with_structured_output(SpeakerEntityMap)
        )

        self.passage_prompt = ChatPromptTemplate.from_messages([
            ("system", PASSAGE_SYSTEM_PROMPT),
            ("user", PASSAGE_USER_PROMPT),
        ])
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=extraction_config.CHUNK_SIZE,
            chunk_overlap=extraction_config.CHUNK_OVERLAP,
            separators=["\n\n", "\n", " "],
        )

    @staticmethod
    def _passage_schema(entity_whitelist: Dict[str, List[str]]) -> type | None:
        """Dynamic Pydantic schema for Phase 2: speaker enum + unified entity enum → passages."""
        all_speakers = list(entity_whitelist.keys())
        all_entities = list(dict.fromkeys(
            e.strip()
            for entities in entity_whitelist.values()
            for e in entities
            if e.strip()
        ))
        if not all_speakers or not all_entities:
            return None

        speaker_enum = Enum("SpeakerEnum", [(f"s_{i}", s) for i, s in enumerate(all_speakers)], type=str)
        entity_enum = Enum("EntityEnum", [(f"e_{i}", e) for i, e in enumerate(all_entities)], type=str)

        entity_model = create_model(
            "PassageEntity",
            entity_name=(entity_enum, Field(...)),
            passages=(List[Passage], Field(...)),
        )
        speaker_model = create_model(
            "SpeakerPassages",
            speaker_name=(speaker_enum, Field(...)),
            entities=(List[entity_model], Field(...)),
        )
        return create_model(
            "PassageOutput",
            speakers=(List[speaker_model], Field(...)),
        )

    @staticmethod
    def _format_speaker_entity_list(entity_whitelist: Dict[str, List[str]]) -> str:
        return "\n".join(
            f"  {speaker}:\n" + "\n".join(f"    - {e}" for e in entities)
            for speaker, entities in entity_whitelist.items()
        )

    @staticmethod
    def _format_error_text(error_message: Optional[str] = None, failed_output: Optional[str] = None) -> str:
        if not error_message:
            return ""
        parts = ["\n\n*** PREVIOUS ATTEMPT FAILED ***\n\n"]
        if failed_output:
            parts.append(f"Your previous output:\n{failed_output}\n\n")
        parts.append(f"Validation error:\n{error_message}\n\nFix the errors and try again.\n")
        return "".join(parts)

    def extract_entities(self, context: ExtractContext) -> StageResult:
        """Two-phase extraction: speaker-entity attribution, then parallel passage extraction per chunk."""
        if not context.content:
            raise ValueError("No content found in extraction input")

        total_usage = TokenUsage()
        error_text = self._format_error_text(context.previous_error, context.previous_failed_output)
        if context.previous_error:
            logger.info(f"Retrying extraction for {context.id}")

        # Phase 1: speaker-entity attribution (single call, full text)
        logger.info(f"Phase 1 starting for {context.id}")
        matched_speakers_str = "\n".join(f"  - {s}" for s in context.matched_speakers)
        entity_whitelist, usage = self._extract_entity_whitelist(
            context.content, matched_speakers_str, context.content_type, error_text,
        )
        total_usage.input_tokens += usage.input_tokens
        total_usage.output_tokens += usage.output_tokens

        total_entities = sum(len(v) for v in entity_whitelist.values())
        logger.info(f"Phase 1 complete — {total_entities} entities across {len(entity_whitelist)} speakers for {context.id}")

        if not entity_whitelist:
            return self._create_result(context.id, ExtractionOutput(), total_usage)

        # Phase 2: parallel passage extraction per chunk
        no_chunk_threshold = int(1.5 * extraction_config.CHUNK_SIZE)
        chunks = (
            [context.content]
            if len(context.content) < no_chunk_threshold
            else self.splitter.split_text(context.content)
        )
        logger.info(f"Phase 2 starting for {context.id} ({len(chunks)} chunks, {len(context.content)} chars)")

        chunk_results, chunk_usage = self._extract_passages_parallel(chunks, entity_whitelist, context.content_type)
        total_usage.input_tokens += chunk_usage.input_tokens
        total_usage.output_tokens += chunk_usage.output_tokens

        by_speaker = self._merge(chunk_results, entity_whitelist)
        total_passages = sum(len(p) for entities in by_speaker.values() for p in entities.values())
        logger.info(f"Phase 2 complete — {total_passages} passages across {len(by_speaker)} speakers for {context.id}")

        output = ExtractionOutput(by_speaker=by_speaker, entity_whitelist=entity_whitelist)
        return self._create_result(context.id, output, total_usage)

    @staticmethod
    def _parse_usage(usage_cb) -> TokenUsage:
        return TokenUsage(
            input_tokens=sum(v.get("input_tokens", 0) for v in usage_cb.usage_metadata.values()),
            output_tokens=sum(v.get("output_tokens", 0) for v in usage_cb.usage_metadata.values()),
        )

    def _extract_entity_whitelist(
        self, content: str, matched_speakers_str: str, content_type: str, error_text: str,
    ) -> tuple[Dict[str, List[str]], TokenUsage]:
        with get_usage_metadata_callback() as usage_cb:
            parsed: SpeakerEntityMap = self.entity_chain.invoke({
                "content": content,
                "matched_speakers": matched_speakers_str,
                "content_type": content_type,
                "previous_error_text": error_text,
            })
        return {
            s.speaker: list(dict.fromkeys(e.strip() for e in s.entities if e.strip()))
            for s in parsed.speakers
            if s.entities
        }, self._parse_usage(usage_cb)

    def _extract_passages_parallel(
        self,
        chunks: List[str],
        entity_whitelist: Dict[str, List[str]],
        content_type: str,
    ) -> tuple[list[dict], TokenUsage]:
        schema = self._passage_schema(entity_whitelist)
        if schema is None:
            return [], TokenUsage()

        passage_chain = (
            {
                "content_type": lambda x: x["content_type"],
                "speaker_entity_list": lambda x: x["speaker_entity_list"],
                "content": lambda x: x["content"],
            }
            | self.passage_prompt
            | self.llm.with_structured_output(schema)
        )
        speaker_entity_list = self._format_speaker_entity_list(entity_whitelist)
        inputs = [
            {"speaker_entity_list": speaker_entity_list, "content": chunk, "content_type": content_type}
            for chunk in chunks
        ]

        with get_usage_metadata_callback() as usage_cb:
            responses = passage_chain.batch(inputs, config={"max_concurrency": extraction_config.MAX_CONCURRENT_CHUNKS})

        return [
            {
                speaker_obj.speaker_name.value: {
                    entity_obj.entity_name.value: list(entity_obj.passages)
                    for entity_obj in speaker_obj.entities
                }
                for speaker_obj in r.speakers
            }
            for r in responses
        ], self._parse_usage(usage_cb)

    def _merge(
        self,
        chunk_results: list[dict],
        entity_whitelist: Dict[str, List[str]],
    ) -> Dict[str, Dict[str, List[Passage]]]:
        """Merge chunk results: group by (speaker, entity), fuzzy-dedup on verbatim."""
        by_speaker: dict[str, dict[str, list[Passage]]] = defaultdict(lambda: defaultdict(list))
        seen_verbatims: dict[tuple, list[str]] = defaultdict(list)
        valid = {speaker: set(entities) for speaker, entities in entity_whitelist.items()}

        for chunk in chunk_results:
            for speaker, entities in chunk.items():
                if speaker not in valid:
                    logger.info(f"Discarding hallucinated speaker from Phase 2: {speaker}")
                    continue
                for entity, passages in entities.items():
                    if entity not in valid[speaker]:
                        logger.info(f"Discarding hallucinated entity '{entity}' for speaker '{speaker}'")
                        continue
                    key = (speaker, entity)
                    for passage in passages:
                        if not self._is_duplicate(passage.verbatim, seen_verbatims[key]):
                            by_speaker[speaker][entity].append(passage)
                            seen_verbatims[key].append(passage.verbatim)

        return {
            speaker: {entity: passages for entity, passages in entities.items() if passages}
            for speaker, entities in by_speaker.items()
        }

    @staticmethod
    def _is_duplicate(candidate: str, existing: List[str]) -> bool:
        return any(
            SequenceMatcher(None, candidate, e).ratio() > DEDUP_THRESHOLD
            for e in existing
        )

    def _create_result(self, id: str, data: ExtractionOutput, token_usage: TokenUsage) -> StageResult:
        artifact = ExtractionResult(id=id, success=True, data=data, error_message=None)
        metadata = ExtractStageMetadata(
            model_used=extraction_config.LLM_MODEL,
            input_tokens=token_usage.input_tokens,
            output_tokens=token_usage.output_tokens,
        ).model_dump()
        return StageResult(artifact=artifact.model_dump(mode='json'), metadata=metadata)
