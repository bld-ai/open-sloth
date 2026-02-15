"""
Main application entry point.
Runs health checks and starts the Telegram bot.
"""

import sys
from loguru import logger

from src.config.settings import settings
from src.bot.telegram_bot import telegram_bot
from src.sheets.sheets_client import sheets_client


def check_llm_connection() -> bool:
    """
    Verify LLM provider is accessible.

    Returns:
        True if connection successful, False otherwise
    """
    try:
        logger.info(f"Checking LLM connection ({settings.llm_provider})...")

        from src.llm import get_llm_provider

        llm = get_llm_provider(
            provider=settings.llm_provider,
            api_key=settings.get_llm_api_key(),
            model=settings.get_llm_model(),
            base_url=settings.llm_base_url,
        )

        logger.info(
            f"✓ LLM connection successful ({settings.llm_provider}: {settings.get_llm_model()})"
        )
        return True
    except Exception as e:
        logger.error(f"✗ LLM connection failed: {e}")
        return False


def check_sheets_connection() -> bool:
    """
    Verify Google Sheets is accessible.

    Returns:
        True if connection successful, False otherwise
    """
    try:
        logger.info("Checking Google Sheets connection...")

        if sheets_client.health_check():
            logger.info(f"✓ Google Sheets connection successful")
            logger.info(f"  Service account: {sheets_client.service_account_email}")
            return True
        else:
            logger.error("✗ Google Sheets connection failed")
            return False
    except Exception as e:
        logger.error(f"✗ Google Sheets connection failed: {e}")
        return False


def run_health_checks() -> bool:
    """
    Run all health checks before starting the bot.

    Returns:
        True if all checks pass, False otherwise
    """
    logger.info("=" * 50)
    logger.info("Running startup health checks...")
    logger.info("=" * 50)

    llm_ok = check_llm_connection()
    sheets_ok = check_sheets_connection()

    if llm_ok and sheets_ok:
        logger.info("=" * 50)
        logger.info("✓ All health checks passed!")
        logger.info("=" * 50)
        return True
    else:
        logger.error("=" * 50)
        logger.error("✗ Health checks failed!")
        logger.error("=" * 50)
        return False


def main():
    """Main application entry point."""
    logger.info(
        """
╔═══════════════════════════════════════╗
║         OpenSloth Starting...         ║
║   Telegram Bot + Google Sheets + AI   ║
╚═══════════════════════════════════════╝
    """
    )

    try:

        checks_passed = run_health_checks()

        if not checks_passed:
            logger.error("Cannot start bot due to failed health checks")
            logger.error("Please verify your configuration:")
            logger.error("  - TELEGRAM_BOT_TOKEN is valid")
            logger.error("  - LLM_API_KEY is valid")
            logger.error("  - credentials.json exists and is valid")
            sys.exit(1)

        logger.info("Starting Telegram bot...")
        telegram_bot.start()

    except KeyboardInterrupt:
        logger.info("\nReceived shutdown signal (Ctrl+C)")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("OpenSloth shut down")


if __name__ == "__main__":
    main()
