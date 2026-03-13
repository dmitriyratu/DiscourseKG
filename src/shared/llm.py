"""Shared LLM client utilities using instructor for structured output with automatic retry."""

import instructor

from src.shared.models import TokenUsage


def create_client(model: str, api_key: str = None, **kwargs):
    """Create an instructor client from a provider/model string (e.g. 'openai/gpt-4o-mini')."""
    params = {**kwargs}
    if api_key:
        params["api_key"] = api_key
    return instructor.from_provider(model, **params)


def extract_usage(completion) -> TokenUsage:
    """Extract token usage from a raw completion (handles OpenAI and Anthropic formats)."""
    usage = getattr(completion, "usage", None)
    if not usage:
        return TokenUsage()
    return TokenUsage(
        input_tokens=getattr(usage, "input_tokens", 0) or getattr(usage, "prompt_tokens", 0),
        output_tokens=getattr(usage, "output_tokens", 0) or getattr(usage, "completion_tokens", 0),
    )
