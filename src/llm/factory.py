"""
Factory function for creating LLM providers.
"""

from typing import Optional
from loguru import logger

from src.llm.base import LLMProvider


def get_llm_provider(
    provider: str,
    api_key: str,
    model: str,
    base_url: Optional[str] = None
) -> LLMProvider:
    """
    Create and return an LLM provider instance.

    Args:
        provider: Provider name (openai, anthropic, google, ollama)
        api_key: API key for the provider
        model: Model name
        base_url: Optional custom endpoint URL

    Returns:
        LLMProvider instance

    Raises:
        ValueError: If provider is not supported
    """
    provider = provider.lower()

    if provider == "openai":
        from src.llm.openai_provider import OpenAIProvider
        logger.info(f"Using OpenAI provider with model: {model}")
        return OpenAIProvider(api_key, model, base_url)

    elif provider == "anthropic":
        from src.llm.anthropic_provider import AnthropicProvider
        logger.info(f"Using Anthropic provider with model: {model}")
        return AnthropicProvider(api_key, model, base_url)

    elif provider == "google":
        from src.llm.google_provider import GoogleProvider
        logger.info(f"Using Google provider with model: {model}")
        return GoogleProvider(api_key, model, base_url)

    elif provider == "ollama":
        from src.llm.ollama_provider import OllamaProvider
        logger.info(f"Using Ollama provider with model: {model}")
        return OllamaProvider(api_key, model, base_url)

    else:
        raise ValueError(f"Unsupported LLM provider: {provider}. Use: openai, anthropic, google, or ollama")
