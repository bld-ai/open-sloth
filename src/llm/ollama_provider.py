"""
Ollama LLM provider implementation for local models.
"""

import json
from typing import List, Dict, Any, Optional
from loguru import logger

from src.llm.base import LLMProvider, ToolCall

try:
    import ollama
    from ollama import AsyncClient

    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False


class OllamaProvider(LLMProvider):
    """Ollama local LLM provider."""

    def __init__(self, api_key: str, model: str, base_url: Optional[str] = None):
        super().__init__(api_key, model, base_url)
        if not OLLAMA_AVAILABLE:
            raise ImportError("ollama package not installed. Run: pip install ollama")
        self.client = AsyncClient(host=base_url) if base_url else AsyncClient()

    def _convert_to_ollama_tools(
        self, tools: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Convert OpenAI function format to Ollama tool format."""
        ollama_tools = []
        for tool in tools:
            ollama_tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "parameters": tool.get(
                            "parameters", {"type": "object", "properties": {}}
                        ),
                    },
                }
            )
        return ollama_tools

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> tuple[str, Optional[ToolCall]]:
        """Send chat to Ollama."""
        kwargs = {"model": self.model, "messages": messages}

        if tools:
            kwargs["tools"] = self._convert_to_ollama_tools(tools)

        response = await self.client.chat(**kwargs)
        message = response["message"]

        if "tool_calls" in message and message["tool_calls"]:
            tc = message["tool_calls"][0]
            tool_call = ToolCall(
                name=tc["function"]["name"],
                arguments=(
                    tc["function"]["arguments"]
                    if isinstance(tc["function"]["arguments"], dict)
                    else json.loads(tc["function"]["arguments"])
                ),
            )
            return message.get("content", ""), tool_call

        return message.get("content", ""), None

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
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": tool_call.name,
                            "arguments": tool_call.arguments,
                        }
                    }
                ],
            },
            {"role": "tool", "content": json.dumps(tool_result)},
        ]

        kwargs = {"model": self.model, "messages": full_messages}

        if tools:
            kwargs["tools"] = self._convert_to_ollama_tools(tools)

        response = await self.client.chat(**kwargs)
        message = response["message"]

        if "tool_calls" in message and message["tool_calls"]:
            tc = message["tool_calls"][0]
            next_tool_call = ToolCall(
                name=tc["function"]["name"],
                arguments=(
                    tc["function"]["arguments"]
                    if isinstance(tc["function"]["arguments"], dict)
                    else json.loads(tc["function"]["arguments"])
                ),
            )
            return message.get("content", ""), next_tool_call

        return message.get("content", ""), None
