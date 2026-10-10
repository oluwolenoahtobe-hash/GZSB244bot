"""Telegram command and message handlers."""
import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from bot.analyzer import AnalysisError, TenderAnalyzer
from bot.config import get_settings
from bot.extractors import (
    EmptyDocumentError,
    UnsupportedFileTypeError,
    extract_text,
)
from bot.formatters import format_analysis, split_for_telegram

logger = logging.getLogger(__name__)

WELCOME_MESSAGE = (
    "👋 *Welcome to the Tender Analysis Bot.*\n\n"
    "Send me a tender document in PDF or DOCX format and I will extract:\n"
    "• Eligibility requirements and deadlines\n"
    "• Required submission documents\n"
    "• Evaluation criteria and budget details\n"
    "• Important contractual clauses\n\n"
    "_Maximum file size: {size} MB._"
)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start and /help."""
    settings = get_settings()
    if update.effective_message is None:
        return
    await update.effective_message.reply_text(
        WELCOME_MESSAGE.format(size=settings.max_file_size_mb),
        parse_mode=ParseMode.MARKDOWN,
    )


async def document_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle uploaded documents end-to-end."""
    message = update.effective_message
    if message is None or message.document is None:
        return

    document = message.document
    settings = get_settings()

    filename = document.file_name or "document"
    user_id = update.effective_user.id if update.effective_user else "unknown"
    logger.info(
        "Received '%s' (%d bytes) from user %s",
        filename,
        document.file_size or 0,
        user_id,
    )

    if not filename.lower().endswith((".pdf", ".docx")):
        await message.reply_text("❌ Only PDF and DOCX files are supported.")
        return

    if document.file_size and document.file_size > settings.max_file_size_bytes:
        await message.reply_text(
            f"❌ File exceeds the {settings.max_file_size_mb} MB limit."
        )
        return

    status = await message.reply_text("📥 Downloading document...")

    try:
        file = await context.bot.get_file(document.file_id)
        file_bytes = bytes(await file.download_as_bytearray())

        await status.edit_text("📄 Extracting text...")
        text = extract_text(file_bytes, filename)

        await status.edit_text("🤖 Analyzing document...")
        analyzer = TenderAnalyzer()
        analysis = analyzer.analyze(text)

        formatted = format_analysis(analysis)
        chunks = split_for_telegram(formatted)

        await status.edit_text("✅ Analysis complete.")
        total = len(chunks)
        for index, chunk in enumerate(chunks, start=1):
            header = f"📊 Part {index}/{total}\n\n" if total > 1 else ""
            await message.reply_text(
                header + chunk,
                parse_mode=ParseMode.MARKDOWN_V2,
                disable_web_page_preview=True,
            )

    except UnsupportedFileTypeError as exc:
        await status.edit_text(f"❌ {exc}")
    except EmptyDocumentError as exc:
        await status.edit_text(f"❌ {exc}")
    except AnalysisError as exc:
        logger.exception("Analysis failure")
        await status.edit_text(f"❌ Analysis failed: {exc}")
    except Exception:  # noqa: BLE001
        logger.exception("Unhandled error while processing document")
        await status.edit_text(
            "❌ An unexpected error occurred. Please try again later."
        )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Global error handler to prevent silent failures."""
    logger.error(
        "Update %s caused error: %s",
        update,
        context.error,
        exc_info=context.error,
    )
