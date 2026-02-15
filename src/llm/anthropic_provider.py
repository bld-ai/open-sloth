"""
Anthropic (Claude) LLM provider implementation.
"""

import json
from typing import List, Dict, Any, Optional
from loguru import logger

from src.llm.base import LLMProvider, ToolCall

try:
    import anthropic

    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


class AnthropicProvider(LLMProvider):
    """Anthropic Claude API provider."""

    def __init__(self, api_key: str, model: str, base_url: Optional[str] = None):
        super().__init__(api_key, model, base_url)
        if not ANTHROPIC_AVAILABLE:
            raise ImportError(
                "anthropic package not installed. Run: pip install anthropic"
            )
        self.client = anthropic.AsyncAnthropic(api_key=api_key)

    def _convert_to_anthropic_tools(
        self, tools: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Convert OpenAI function format to Anthropic tool format."""
        anthropic_tools = []
        for tool in tools:
            anthropic_tools.append(
                {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "input_schema": tool.get(
                        "parameters", {"type": "object", "properties": {}}
                    ),
                }
            )
        return anthropic_tools

    def _extract_system_message(
        self, messages: List[Dict[str, Any]]
    ) -> tuple[str, List[Dict[str, Any]]]:
        """Extract system message from messages list."""
        system = ""
        other_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                other_messages.append(msg)
        return system, other_messages

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> tuple[str, Optional[ToolCall]]:
        """Send chat to Claude."""
        system, chat_messages = self._extract_system_message(messages)

        kwargs = {"model": self.model, "max_tokens": 4096, "messages": chat_messages}

        if system:
            kwargs["system"] = system

        if tools:
            kwargs["tools"] = self._convert_to_anthropic_tools(tools)

        response = await self.client.messages.create(**kwargs)

        for block in response.content:
            if block.type == "tool_use":
                tool_call = ToolCall(name=block.name, arguments=block.input)

                text = ""
                for b in response.content:
                    if b.type == "text":
                        text = b.text
                        break
                return text, tool_call

        text = ""
        for block in response.content:
            if block.type == "text":
                text = block.text
                break

        return text, None

    async def chat_with_tool_result(
        self,
        messages: List[Dict[str, Any]],
        tool_call: ToolCall,
        tool_result: Dict[str, Any],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> tuple[str, Optional[ToolCall]]:
        """Continue chat with tool result. Returns (text, optional_next_tool_call)."""
        system, chat_messages = self._extract_system_message(messages)

        chat_messages.append(
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": "tool_1",
                        "name": tool_call.name,
                        "input": tool_call.arguments,
                    }
                ],
            }
        )

        chat_messages.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "tool_1",
                        "content": json.dumps(tool_result),
                    }
                ],
            }
        )

        kwargs = {"model": self.model, "max_tokens": 4096, "messages": chat_messages}

        if system:
            kwargs["system"] = system

        if tools:
            kwargs["tools"] = self._convert_to_anthropic_tools(tools)

        response = await self.client.messages.create(**kwargs)

        for block in response.content:
            if block.type == "tool_use":
                next_tool_call = ToolCall(name=block.name, arguments=block.input)
                text = ""
                for b in response.content:
                    if b.type == "text":
                        text = b.text
                        break
                return text, next_tool_call

        for block in response.content:
            if block.type == "text":
                return block.text, None

        return "", None
