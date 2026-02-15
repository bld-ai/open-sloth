"""
Generic LLM agent for sheet manipulation.
Supports multiple LLM providers with conversation history.
"""

from typing import Dict, Any, List
from loguru import logger

from src.config.settings import settings
from src.sheets.sheets_client import sheets_client
from src.sheets.models import UserContext
from src.agent.prompts import get_system_prompt, FUNCTIONS, get_user_context_prompt
from src.llm import get_llm_provider, ToolCall


class Agent:
    """Agent that processes messages and executes sheet operations."""

    def __init__(self):
        self.llm = get_llm_provider(
            provider=settings.llm_provider,
            api_key=settings.get_llm_api_key(),
            model=settings.get_llm_model(),
            base_url=settings.llm_base_url,
        )

        self.conversation_history: Dict[int, List[Dict[str, str]]] = {}
        self.max_history = 10

    def _get_history(self, user_id: int) -> List[Dict[str, str]]:
        """Get conversation history for a user."""
        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = []
        return self.conversation_history[user_id]

    def _add_to_history(self, user_id: int, role: str, content: str):
        """Add a message to user's history."""
        history = self._get_history(user_id)
        history.append({"role": role, "content": content})

        if len(history) > self.max_history:
            self.conversation_history[user_id] = history[-self.max_history :]

    async def process_message(
        self, user_message: str, user_context: UserContext
    ) -> str:
        """Process a user message and return a response."""
        try:
            user_id = user_context.user_id

            self._add_to_history(user_id, "user", user_message)

            sheet_structure = None
            try:
                sheet_structure = sheets_client.get_sheet_structure()
            except Exception as e:
                logger.debug(f"Could not fetch sheet structure: {e}")

            system = get_system_prompt(
                sheet_structure=sheet_structure,
                service_email=sheets_client.service_account_email or "",
            ) + get_user_context_prompt(
                user_context.username or user_context.get_display_name(),
                user_context.first_name or "",
            )

            messages = [{"role": "system", "content": system}]
            messages.extend(self._get_history(user_id))

            response_text, tool_call = await self.llm.chat(messages, FUNCTIONS)

            max_iterations = 5
            iteration = 0

            while tool_call and iteration < max_iterations:
                iteration += 1
                logger.info(
                    f"Tool call {iteration}: {tool_call.name} with args: {tool_call.arguments}"
                )

                result = await self._execute(tool_call)

                response_text, tool_call = await self.llm.chat_with_tool_result(
                    messages, tool_call, result, FUNCTIONS
                )

            if iteration >= max_iterations:
                logger.warning("Max tool iterations reached")

            final_response = response_text or "Done!"
            self._add_to_history(user_id, "assistant", final_response)
            return final_response

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            raise

    async def _execute(self, tool_call: ToolCall) -> Dict[str, Any]:
        """Execute a tool call."""
        name = tool_call.name
        args = tool_call.arguments

        logger.debug(f"Executing {name} with args: {args}")

        try:
            if name == "list_sheets":
                return {"sheets": sheets_client.list_sheets()}

            elif name == "list_my_sheets":
                return {"sheets": sheets_client.list_all_accessible_sheets()}

            elif name == "open_sheet":
                url_or_name = args.get("url") or args.get("name")
                sheet_info = sheets_client.open_sheet(url_or_name)
                if "error" in sheet_info:
                    return sheet_info
                return {"success": True, "sheet": sheet_info}

            elif name == "get_active_sheet":
                return {"active_sheet": sheets_client.get_active_sheet_info()}

            elif name == "read_sheet":
                result = sheets_client.read_sheet(args.get("sheet_name"))
                return {
                    "headers": result["headers"],
                    "rows": result["rows"],
                    "count": len(result["rows"]),
                }

            elif name == "add_row":
                data = args.get("data") or args.get("row")
                if data is None:
                    data = {k: v for k, v in args.items() if k != "sheet_name"}
                result = sheets_client.add_row(data, args.get("sheet_name"))
                return result if result else {"success": True}

            elif name == "update_cell":
                sheets_client.update_cell(
                    args["row"], args["column"], args["value"], args.get("sheet_name")
                )
                return {"success": True}

            elif name == "delete_row":
                sheets_client.delete_row(args["row"], args.get("sheet_name"))
                return {"success": True}

            elif name == "search":
                results = sheets_client.search(args["query"])
                return {"results": results, "count": len(results)}

            else:
                return {"error": f"Unknown function: {name}"}

        except Exception as e:
            logger.error(f"Function error: {e}")
            return {"error": str(e)}


agent = Agent()
