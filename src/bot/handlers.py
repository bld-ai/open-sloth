"""
Telegram bot command and message handlers.
"""

import re

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from loguru import logger

from src.config.settings import settings
from src.agent.agent import agent
from src.sheets.sheets_client import sheets_client
from src.sheets.models import UserContext
from src.utils.errors import LLMConnectionError, SheetsConnectionError


_ALLOWED_TAGS = {"b", "i", "code", "pre", "u", "s", "a"}


def sanitize_html(text: str) -> str:
    """Escape HTML but preserve allowed Telegram tags."""

    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    for tag in _ALLOWED_TAGS:

        text = re.sub(
            rf"&lt;({tag})(\s[^&]*?)?&gt;",
            rf"<\1\2>",
            text,
            flags=re.IGNORECASE,
        )

        text = re.sub(
            rf"&lt;/({tag})&gt;",
            rf"</\1>",
            text,
            flags=re.IGNORECASE,
        )
    return text


def is_user_allowed(user) -> bool:
    """Check if user is allowed to use the bot."""
    allowed = settings.allowed_users
    if not allowed:
        return True

    return str(user.id) in allowed or (user.username and user.username in allowed)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle the /start command.

    Sends a welcome message to the user.
    """
    if not is_user_allowed(update.effective_user):
        await update.message.reply_text("Access denied.")
        return

    service_email = sheets_client.service_account_email or "the service account"

    welcome_message = f"""<b>Welcome to OpenSloth!</b>

I can read and write to any Google Sheet you share with me.

<b>To give me access to a sheet:</b>
1. Open your Google Sheet
2. Click "Share" button
3. Add this email as Editor:
<code>{service_email}</code>

<b>What I can do:</b>
- Read data from any sheet
- Add, update, or delete rows
- Search across worksheets
- Work with multiple sheets

<b>Quick commands:</b>
- "Show me all data"
- "Add a row with Name: John, Status: Active"
- "Open [paste sheet URL]" - to switch sheets

Use /help for more examples."""

    await update.message.reply_text(welcome_message, parse_mode=ParseMode.HTML)
    logger.info(f"User {update.effective_user.id} started the bot")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle the /help command.

    Sends usage instructions and examples.
    """
    if not is_user_allowed(update.effective_user):
        await update.message.reply_text("Access denied.")
        return

    service_email = sheets_client.service_account_email or "the service account"

    help_message = f"""<b>OpenSloth Help</b>

<b>Sharing a Sheet:</b>
Share your Google Sheet with:
<code>{service_email}</code>
(Give "Editor" access for read+write)

<b>Reading Data:</b>
- "Show me all data"
- "What's in the sheet?"
- "List all rows"
- "Search for John"

<b>Adding Data:</b>
- "Add a row with Name: John, Email: john@example.com"
- "Add: Task: Fix bug, Status: Open"

<b>Updating Data:</b>
- "Update row 3, set Status to Done"
- "Change row 5 Name to Jane"

<b>Deleting Data:</b>
- "Delete row 4"

<b>Working with Multiple Sheets:</b>
- "What sheets do I have access to?"
- "Open https://docs.google.com/spreadsheets/d/..."
- "List all worksheets"

<b>Tips:</b>
- Row numbers start at 1 (after header)
- Just describe what you want in plain English!"""

    await update.message.reply_text(help_message, parse_mode=ParseMode.HTML)
    logger.info(f"User {update.effective_user.id} requested help")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle text messages from users.

    Forwards the message to the OpenAI agent and returns the response.
    """
    try:
        user = update.effective_user

        if not is_user_allowed(user):
            logger.warning(f"Access denied for user {user.id} (@{user.username})")
            await update.message.reply_text(
                "Access denied. You are not authorized to use this bot."
            )
            return

        message_text = update.message.text

        logger.info(
            f"Received message from user {user.id} (@{user.username}): {message_text[:100]}"
        )

        user_context = UserContext(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
        )

        await update.message.chat.send_action("typing")

        response = await agent.process_message(message_text, user_context)

        try:
            await update.message.reply_text(
                sanitize_html(response), parse_mode=ParseMode.HTML
            )
        except Exception:
            await update.message.reply_text(response)

        logger.info(f"Sent response to user {user.id}")

    except LLMConnectionError as e:
        error_msg = "I'm having trouble connecting to the AI service right now. Please try again in a moment."
        await update.message.reply_text(error_msg)
        logger.error(f"LLM error: {e}")

    except SheetsConnectionError as e:
        error_msg = "I'm having trouble accessing the spreadsheet. Please make sure it's properly configured and try again."
        await update.message.reply_text(error_msg)
        logger.error(f"Sheets error: {e}")

    except Exception as e:
        error_msg = "Something unexpected went wrong. Please try again or contact support if the issue persists."
        await update.message.reply_text(error_msg)
        logger.error(f"Unexpected error handling message: {e}", exc_info=True)


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle errors in the bot.

    Logs errors and sends user-friendly messages.
    """
    logger.error(
        f"Update {update} caused error: {context.error}", exc_info=context.error
    )

    if update and update.effective_message:
        try:
            error_msg = (
                "An error occurred while processing your request. Please try again."
            )
            await update.effective_message.reply_text(error_msg)
        except Exception as e:
            logger.error(f"Failed to send error message to user: {e}")
