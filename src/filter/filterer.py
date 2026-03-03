"""Filterer implementation using LangChain for structured speaker identification."""

import tiktoken
from typing import Dict
from langchain.chat_models import init_chat_model
from langchain_core.callbacks import get_usage_metadata_callback
from langchain_core.prompts import ChatPromptTemplate

from src.filter.config import filter_config
from src.filter.models import LLMFilterOutput, FilterOutput, FilterContext, FilterResult, FilterStageMetadata
from src.filter.prompts import SYSTEM_PROMPT, USER_PROMPT
from src.shared.models import ContentType
from src.shared.pipeline_definitions import StageResult
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)


class Filterer:
    """Identifies active contributors in content and matches against tracked speakers."""
    
    def __init__(self) -> None:
        llm = init_chat_model(
            filter_config.LLM_MODEL,
            temperature=filter_config.LLM_TEMPERATURE,
            timeout=filter_config.LLM_TIMEOUT,
            max_retries=filter_config.LLM_MAX_RETRIES,
            api_key=filter_config.LLM_API_KEY,
        )
        llm_structured = llm.with_structured_output(LLMFilterOutput, include_raw=True)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("user", USER_PROMPT)
        ])
        
        self.chain = (
            {
                "tracked_speaker_hints": lambda x: x["tracked_speaker_hints"],
                "title": lambda x: x["title"],
                "content_preview": lambda x: x["content_preview"],
                "content_type_options": lambda _: "\n".join(f"  {item.value}" for item in ContentType),
            }
            | prompt
            | llm_structured
        )
        self._encoder = tiktoken.get_encoding("cl100k_base")
    
    def filter_content(self, context: FilterContext) -> StageResult:
        """Run speaker identification on content."""
        logger.debug(f"Starting filter for {context.id}")
        content_preview = self._truncate_to_tokens(context.content, filter_config.CONTENT_PREVIEW_TOKENS)

        with get_usage_metadata_callback() as usage_cb:
            response = self.chain.invoke({
                "tracked_speaker_hints": ", ".join(context.tracked_speaker_hints),
                "title": context.title,
                "content_preview": content_preview,
            })

        llm_result = response["parsed"]
        usage = next(iter(usage_cb.usage_metadata.values()), {})
        token_usage = {"input_tokens": usage.get("input_tokens", 0), "output_tokens": usage.get("output_tokens", 0)}
        if token_usage["input_tokens"] or token_usage["output_tokens"]:
            logger.info(f"Filter token usage for {context.id}: {token_usage}")
        
        # Compute matched_speakers (id -> display_name) and is_relevant
        matched_speakers = {
            context.display_name_to_id[s]: s
            for s in llm_result.active_speakers
            if s in context.display_name_to_id
        }
        is_relevant = len(matched_speakers) > 0
        
        filter_data = FilterOutput(
            content_type=llm_result.content_type,
            active_speakers=llm_result.active_speakers,
            matched_speakers=matched_speakers,
            is_relevant=is_relevant,
            reason=llm_result.reason,
        )
        
        logger.debug(
            f"Filter result for {context.id}: is_relevant={is_relevant}, "
            f"matched={matched_speakers}, active={llm_result.active_speakers}"
        )
        
        return self._create_result(context.id, filter_data, token_usage)
    
    def _create_result(self, id: str, filter_data: FilterOutput, token_usage: Dict[str, int]) -> StageResult:
        """Create StageResult with separated artifact and metadata."""
        artifact = FilterResult(
            id=id,
            success=True,
            data=filter_data.model_dump(mode='json'),
            error_message=None
        )
        
        metadata = FilterStageMetadata(
            content_type=filter_data.content_type,
            model_used=filter_config.LLM_MODEL,
            input_tokens=token_usage.get('input_tokens', 0),
            output_tokens=token_usage.get('output_tokens', 0),
            matched_speakers=filter_data.matched_speakers,
        ).model_dump()
        
        return StageResult(artifact=artifact.model_dump(mode='json'), metadata=metadata)

    def _truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        """Truncate text to a maximum number of tokens."""
        tokens = self._encoder.encode(text)
        if len(tokens) <= max_tokens:
            return text
        return self._encoder.decode(tokens[:max_tokens])
