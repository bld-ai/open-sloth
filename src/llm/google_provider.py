"""
Google Gemini LLM provider implementation.
"""

import json
from typing import List, Dict, Any, Optional
from loguru import logger

from src.llm.base import LLMProvider, ToolCall

try:
    import google.generativeai as genai

    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False


class GoogleProvider(LLMProvider):
    """Google Gemini API provider."""

    def __init__(self, api_key: str, model: str, base_url: Optional[str] = None):
        super().__init__(api_key, model, base_url)
        if not GOOGLE_AVAILABLE:
            raise ImportError(
                "google-generativeai package not installed. Run: pip install google-generativeai"
            )
        genai.configure(api_key=api_key)
        self.model_instance = genai.GenerativeModel(model)

    def _convert_to_gemini_tools(self, tools: List[Dict[str, Any]]) -> List[Any]:
        """Convert OpenAI function format to Gemini tool format."""
        function_declarations = []
        for tool in tools:
            func_decl = {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "parameters": tool.get(
                    "parameters", {"type": "object", "properties": {}}
                ),
            }
            function_declarations.append(func_decl)
        return [genai.protos.Tool(function_declarations=function_declarations)]

    def _convert_messages(
        self, messages: List[Dict[str, Any]]
    ) -> tuple[str, List[Any]]:
        """Convert messages to Gemini format."""
        system = ""
        history = []

        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            elif msg["role"] == "user":
                history.append({"role": "user", "parts": [msg["content"]]})
            elif msg["role"] == "assistant":
                history.append({"role": "model", "parts": [msg["content"] or ""]})

        return system, history

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> tuple[str, Optional[ToolCall]]:
        """Send chat to Gemini."""
        system, history = self._convert_messages(messages)

        if system:
            model = genai.GenerativeModel(self.model, system_instruction=system)
        else:
            model = self.model_instance

        chat = model.start_chat(history=history[:-1] if len(history) > 1 else [])

        last_message = history[-1]["parts"][0] if history else ""

        kwargs = {}
        if tools:
            kwargs["tools"] = self._convert_to_gemini_tools(tools)

        response = await chat.send_message_async(last_message, **kwargs)

        for part in response.parts:
            if hasattr(part, "function_call") and part.function_call:
                fc = part.function_call
                tool_call = ToolCall(name=fc.name, arguments=dict(fc.args))
                return "", tool_call

        return response.text, None

    async def chat_with_tool_result(
        self,
        messages: List[Dict[str, Any]],
        tool_call: ToolCall,
        tool_result: Dict[str, Any],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> tuple[str, Optional[ToolCall]]:
        """Continue chat with tool result. Returns (text, optional_next_tool_call)."""
        system, history = self._convert_messages(messages)

        if system:
            model = genai.GenerativeModel(self.model, system_instruction=system)
        else:
            model = self.model_instance

        chat = model.start_chat(history=history[:-1] if len(history) > 1 else [])

        last_message = history[-1]["parts"][0] if history else ""

        kwargs = {}
        if tools:
            kwargs["tools"] = self._convert_to_gemini_tools(tools)

        await chat.send_message_async(last_message, **kwargs)

        response = await chat.send_message_async(
            genai.protos.Content(
                parts=[
                    genai.protos.Part(
                        function_response=genai.protos.FunctionResponse(
                            name=tool_call.name, response={"result": tool_result}
                        )
                    )
                ]
            ),
            **kwargs
        )

        for part in response.parts:
            if hasattr(part, "function_call") and part.function_call:
                fc = part.function_call
                next_tool_call = ToolCall(name=fc.name, arguments=dict(fc.args))
                return "", next_tool_call

        return response.text, None
