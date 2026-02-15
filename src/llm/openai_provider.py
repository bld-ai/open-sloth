"""
OpenAI LLM provider implementation.
"""

import json
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from loguru import logger

from src.llm.base import LLMProvider, ToolCall


class OpenAIProvider(LLMProvider):
    """OpenAI API provider."""

    def __init__(self, api_key: str, model: str, base_url: Optional[str] = None):
        super().__init__(api_key, model, base_url)
        self.client = AsyncOpenAI(
            api_key=api_key, base_url=base_url if base_url else None
        )

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> tuple[str, Optional[ToolCall]]:
        """Send chat to OpenAI."""
        kwargs = {"model": self.model, "messages": messages}

        if tools:
            kwargs["functions"] = tools
            kwargs["function_call"] = "auto"

        response = await self.client.chat.completions.create(**kwargs)
        message = response.choices[0].message

        if message.function_call:
            tool_call = ToolCall(
                name=message.function_call.name,
                arguments=json.loads(message.function_call.arguments),
            )
            return message.content or "", tool_call

        return message.content or "", None

    async def chat_with_tool_result(
        self,
        messages: List[Dict[str, Any]],
        tool_call: ToolCall,
        tool_result: Dict[str, Any],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> tuple[str, Optional[ToolCall]]:
        """Continue chat with tool result. Returns (text, optional_next_tool_call)."""

        full_messages = messages + [
            {
                "role": "assistant",
                "content": None,
                "function_call": {
                    "name": tool_call.name,
                    "arguments": json.dumps(tool_call.arguments),
                },
            },
            {
                "role": "function",
                "name": tool_call.name,
                "content": json.dumps(tool_result),
            },
        ]

        kwargs = {"model": self.model, "messages": full_messages}

        if tools:
            kwargs["functions"] = tools
            kwargs["function_call"] = "auto"

        response = await self.client.chat.completions.create(**kwargs)
        message = response.choices[0].message

        if message.function_call:
            next_tool_call = ToolCall(
                name=message.function_call.name,
                arguments=json.loads(message.function_call.arguments),
            )
            return message.content or "", next_tool_call

        return message.content or "", None
