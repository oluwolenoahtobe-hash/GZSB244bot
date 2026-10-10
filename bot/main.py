"""Application entrypoint."""
import logging

from telegram.ext import Application, CommandHandler, MessageHandler, filters

from bot.config import get_settings
from bot.handlers import document_handler, error_handler, start_command
from bot.logging_config import configure_logging

logger = logging.getLogger(__name__)


def build_application() -> Application:
    """Wire up handlers and return a configured Application."""
    settings = get_settings()
    application = Application.builder().token(settings.telegram_bot_token).build()

    application.add_handler(CommandHandler(["start", "help"], start_command))
    application.add_handler(MessageHandler(filters.Document.ALL, document_handler))
    application.add_error_handler(error_handler)

    return application


def main() -> None:
    """Run the bot using long polling."""
    settings = get_settings()
    configure_logging(settings.log_level)

    logger.info("Starting tender analysis bot (rule-based, no external API)")
    application = build_application()
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
