"""
Telegram bot implementation with polling.
"""

import asyncio
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from loguru import logger

from src.config.settings import settings
from src.bot.handlers import start_command, help_command, handle_message, error_handler


class TelegramBot:
    """Telegram bot with polling support."""

    def __init__(self):
        """Initialize the Telegram bot."""
        self.token = settings.telegram_bot_token
        self.application = None

    def setup_handlers(self):
        """Register command and message handlers."""
        self.application.add_handler(CommandHandler("start", start_command))
        self.application.add_handler(CommandHandler("help", help_command))
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
        )
        self.application.add_error_handler(error_handler)
        logger.info("Registered all bot handlers")

    def start(self):
        """Start the bot with polling."""
        try:
            self.application = Application.builder().token(self.token).build()
            self.setup_handlers()

            logger.info("Bot is now running and polling for messages")
            self.application.run_polling(
                poll_interval=settings.poll_interval, drop_pending_updates=True
            )

        except Exception as e:
            logger.error(f"Error running bot: {e}")
            raise


telegram_bot = TelegramBot()
