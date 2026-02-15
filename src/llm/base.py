"""
Abstract base class for LLM providers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional


@dataclass
class ToolCall:
    """Represents a tool/function call from the LLM."""

    name: str
    arguments: Dict[str, Any]


@dataclass
class Message:
    """Chat message."""

    role: str
    content: Optional[str]
    name: Optional[str] = None
    tool_call: Optional[ToolCall] = None


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, api_key: str, model: str, base_url: Optional[str] = None):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url

    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> tuple[str, Optional[ToolCall]]:
        """
        Send chat messages to the LLM.

        Args:
            messages: List of message dicts with 'role' and 'content'
            tools: Optional list of tool/function definitions

        Returns:
            Tuple of (response_text, tool_call_or_none)
        """
        pass

    @abstractmethod
    async def chat_with_tool_result(
        self,
        messages: List[Dict[str, Any]],
        tool_call: ToolCall,
        tool_result: Dict[str, Any],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> tuple[str, Optional["ToolCall"]]:
        """
        Continue chat after a tool call with the result.

        Args:
            messages: Original messages
            tool_call: The tool call that was made
            tool_result: Result from executing the tool
            tools: Tool definitions

        Returns:
            Tuple of (response_text, next_tool_call_or_none)
        """
        pass

    @staticmethod
    def convert_tools_to_functions(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert generic tool format to OpenAI functions format."""
        return tools
