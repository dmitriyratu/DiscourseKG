"""Filterer: identifies active contributors and matches against tracked speakers."""

import tiktoken

from src.filter.config import filter_config
from src.filter.models import LLMFilterOutput, FilterOutput, FilterContext, FilterResult, FilterStageMetadata
from src.filter.prompts import SYSTEM_PROMPT, USER_PROMPT
from src.shared.llm import create_client, extract_usage
from src.shared.models import ContentType, TokenUsage
from src.shared.pipeline_definitions import StageResult
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)


class Filterer:
    """Identifies active contributors in content and matches against tracked speakers."""

    def __init__(self) -> None:
        self.client = create_client(
            filter_config.LLM_MODEL,
            api_key=filter_config.LLM_API_KEY,
        )
        self._encoder = tiktoken.get_encoding("cl100k_base")

    def filter_content(self, context: FilterContext) -> StageResult:
        logger.debug(f"Starting filter for {context.id}")
        content_preview = self._truncate_to_tokens(context.content, filter_config.CONTENT_PREVIEW_TOKENS)

        system = SYSTEM_PROMPT.format(
            content_types=", ".join(ct.value for ct in ContentType),
            content_type_options="\n".join(f"  {item.value}" for item in ContentType),
        )
        user = USER_PROMPT.format(
            tracked_speaker_hints=", ".join(context.tracked_speaker_hints),
            title=context.title,
            content_preview=content_preview,
        )

        llm_result, completion = self.client.create_with_completion(
            response_model=LLMFilterOutput,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=filter_config.LLM_TEMPERATURE,
        )

        usage = extract_usage(completion)
        if usage.input_tokens or usage.output_tokens:
            logger.info(f"Filter token usage for {context.id}: {usage}")

        tracked = set(context.tracked_speaker_hints)
        matched_speakers = [s for s in llm_result.active_speakers if s in tracked]

        filter_data = FilterOutput(
            content_type=llm_result.content_type,
            active_speakers=llm_result.active_speakers,
            matched_speakers=matched_speakers,
            is_relevant=len(matched_speakers) > 0,
            reason=llm_result.reason,
        )
        logger.debug(
            f"Filter result for {context.id}: is_relevant={filter_data.is_relevant}, "
            f"matched={matched_speakers}, active={llm_result.active_speakers}"
        )
        return self._create_result(context.id, filter_data, usage)

    def _create_result(self, id: str, filter_data: FilterOutput, token_usage: TokenUsage) -> StageResult:
        artifact = FilterResult(
            id=id, success=True, data=filter_data.model_dump(mode='json'), error_message=None,
        )
        metadata = FilterStageMetadata(
            content_type=filter_data.content_type,
            model_used=filter_config.LLM_MODEL,
            input_tokens=token_usage.input_tokens, output_tokens=token_usage.output_tokens,
            active_speakers=filter_data.active_speakers,
            matched_speakers=filter_data.matched_speakers,
        ).model_dump()
        return StageResult(artifact=artifact.model_dump(mode='json'), metadata=metadata)

    def _truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        tokens = self._encoder.encode(text)
        if len(tokens) <= max_tokens:
            return text
        return self._encoder.decode(tokens[:max_tokens])
