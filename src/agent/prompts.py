"""
System prompt and function definitions for the sheet agent.
"""

import json
from datetime import date
from typing import Optional, Dict


def get_system_prompt(sheet_structure: Optional[Dict] = None, service_email: str = "") -> str:
    """Build system prompt with current date and sheet structure."""
    today = date.today().isoformat()

    prompt = f"""You are a helpful assistant that can read and write to Google Sheets.
Today's date is {today}.
"""

    if service_email:
        prompt += f"""
SERVICE ACCOUNT EMAIL (for sharing sheets): {service_email}
"""

    if sheet_structure:
        prompt += f"""
ACTIVE SHEET: "{sheet_structure['title']}"
"""
        for tab_name, tab_info in sheet_structure["tabs"].items():
            headers = tab_info["headers"]
            row_count = tab_info["row_count"]
            prompt += f"""
Tab "{tab_name}" (~{row_count} rows):
  Columns: {json.dumps(headers)}"""
        prompt += "\n"
    else:
        prompt += """
NO SHEET ACTIVE. If the user shares a Google Sheets URL, use open_sheet to connect.
If open_sheet fails, tell them to share the sheet with the service account email above.
"""

    prompt += f"""
CRITICAL RULES:
1. You already know the sheet structure above. Use the EXACT column names when calling add_row or update_cell.
2. NEVER ask the user for details you can figure out yourself. Figure it out intelligently:
   - Numeric sequences (IDs, priorities): call read_sheet to see existing data, then assign the next number
   - Dates: use today's date ({today})
   - People/assignee columns: use the user's name or call read_sheet to see existing values
   - Status columns: use a sensible default like "New"
3. ALWAYS call the function immediately — never just describe what you would do.

WORKFLOW FOR ADDING DATA:
1. You already know the column names from the structure above
2. Call read_sheet to see existing data patterns (next ID, existing people, etc.)
3. Build a data object using the exact header names as keys, filling ALL columns intelligently
4. Call add_row with the data — do NOT ask the user to confirm or provide missing fields

WORKFLOW FOR UPDATING/DELETING DATA:
1. ALWAYS call search or read_sheet FIRST to find the exact row number — NEVER guess row numbers from memory
2. The row numbers in read_sheet results are 1-indexed (row 1 = first data row after header)
3. Match on the value the user mentions to find the correct row
4. Then call update_cell or delete_row with the verified row number

WORKFLOW FOR OPENING A NEW SHEET:
1. User shares a URL → call open_sheet with the URL
2. If it fails (no access), tell the user to share the sheet with the service account email
3. Once open, the sheet structure will be available on the next message

FORMATTING: Use HTML tags for formatting (this is a Telegram bot). Use <b>bold</b> for headers/emphasis, <i>italic</i> for secondary emphasis, <code>monospace</code> for values/emails/IDs. Use dashes (-) for lists. Do NOT use markdown (no **, no *, no `, no #).

Available functions: open_sheet, get_active_sheet, list_my_sheets, list_sheets, read_sheet, add_row, update_cell, delete_row, search"""

    return prompt


FUNCTIONS = [
    {
        "name": "list_my_sheets",
        "description": "List all Google Sheets shared with the bot",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "open_sheet",
        "description": "Open a Google Sheet by URL or ID to work with it",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Google Sheets URL or sheet ID"
                }
            },
            "required": ["url"]
        }
    },
    {
        "name": "get_active_sheet",
        "description": "Get info about the currently active sheet",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "list_sheets",
        "description": "List all worksheets/tabs in the active spreadsheet",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "read_sheet",
        "description": "Read all data from a worksheet",
        "parameters": {
            "type": "object",
            "properties": {
                "sheet_name": {
                    "type": "string",
                    "description": "Worksheet name. Omit for first sheet."
                }
            }
        }
    },
    {
        "name": "add_row",
        "description": "Add a new row to a worksheet",
        "parameters": {
            "type": "object",
            "properties": {
                "sheet_name": {
                    "type": "string",
                    "description": "Worksheet name. Omit for first sheet."
                },
                "data": {
                    "type": "object",
                    "description": "Column name to value mapping",
                    "additionalProperties": {"type": "string"}
                }
            },
            "required": ["data"]
        }
    },
    {
        "name": "update_cell",
        "description": "Update a specific cell",
        "parameters": {
            "type": "object",
            "properties": {
                "sheet_name": {
                    "type": "string",
                    "description": "Worksheet name. Omit for first sheet."
                },
                "row": {
                    "type": "integer",
                    "description": "Row number (1-indexed, excluding header)"
                },
                "column": {
                    "type": "string",
                    "description": "Column name"
                },
                "value": {
                    "type": "string",
                    "description": "New value"
                }
            },
            "required": ["row", "column", "value"]
        }
    },
    {
        "name": "delete_row",
        "description": "Delete a row from a worksheet",
        "parameters": {
            "type": "object",
            "properties": {
                "sheet_name": {
                    "type": "string",
                    "description": "Worksheet name. Omit for first sheet."
                },
                "row": {
                    "type": "integer",
                    "description": "Row number to delete (1-indexed, excluding header)"
                }
            },
            "required": ["row"]
        }
    },
    {
        "name": "search",
        "description": "Search for text across all worksheets in the active sheet",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Text to search for"
                }
            },
            "required": ["query"]
        }
    }
]


def get_user_context_prompt(username: str, first_name: str) -> str:
    """Add user context to prompt."""
    return f"\n\nUser: {first_name or username}"
