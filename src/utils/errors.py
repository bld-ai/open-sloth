"""
Custom exceptions and retry decorators for API calls.
Uses tenacity for exponential backoff retry logic.
"""

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
import gspread.exceptions


class OpenSlothError(Exception):
    """Base exception for OpenSloth application."""

    pass


class SheetsConnectionError(OpenSlothError):
    """Raised when unable to connect to Google Sheets."""

    pass


class LLMConnectionError(OpenSlothError):
    """Raised when unable to connect to LLM provider."""

    pass


class TelegramBotError(OpenSlothError):
    """Raised when Telegram bot encounters an error."""

    pass


_llm_retry_exceptions = []

try:
    from openai import RateLimitError, APIError

    _llm_retry_exceptions.extend([RateLimitError, APIError])
except ImportError:
    pass

try:
    from anthropic import RateLimitError as AnthropicRateLimitError
    from anthropic import APIError as AnthropicAPIError

    _llm_retry_exceptions.extend([AnthropicRateLimitError, AnthropicAPIError])
except ImportError:
    pass

llm_retry = retry(
    retry=(
        retry_if_exception_type(tuple(_llm_retry_exceptions))
        if _llm_retry_exceptions
        else retry_if_exception_type((Exception,))
    ),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    stop=stop_after_attempt(3),
)

sheets_retry = retry(
    retry=retry_if_exception_type((gspread.exceptions.APIError,)),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    stop=stop_after_attempt(3),
)


OpenAIConnectionError = LLMConnectionError
openai_retry = llm_retry
