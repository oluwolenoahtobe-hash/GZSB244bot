"""Tender Analysis Telegram Bot — single-file version."""
import io
import logging
import os
import re
import sys
from typing import List, Optional

import docx
import PyPDF2
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from telegram.helpers import escape_markdown

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
MAX_FILE_MB = int(os.environ.get("MAX_FILE_SIZE_MB", "20"))
MAX_FILE_BYTES = MAX_FILE_MB * 1024 * 1024

if not BOT_TOKEN:
    print("ERROR: TELEGRAM_BOT_TOKEN environment variable is required.")
    sys.exit(1)

logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    level=LOG_LEVEL.upper(),
    stream=sys.stdout,
)
log = logging.getLogger("bot")

# ---------------------------------------------------------------------------
# Keyword patterns for rule-based extraction
# ---------------------------------------------------------------------------
SECTIONS = {
    "requirements": [
        "requirements", "mandatory requirements", "general requirements",
        "minimum requirements", "bidder requirements",
    ],
    "required_documents": [
        "required documents", "documents required", "submission documents",
        "documents to be submitted", "required submissions",
    ],
    "eligibility_criteria": [
        "eligibility criteria", "eligibility requirements",
        "qualification criteria", "qualifications", "prequalification",
    ],
    "evaluation_criteria": [
        "evaluation criteria", "evaluation method", "assessment criteria",
        "scoring criteria", "technical evaluation", "financial evaluation",
    ],
    "important_clauses": [
        "important clauses", "special conditions", "general conditions",
        "contract terms", "terms and conditions", "special terms",
    ],
}

DATE_RE = (
    r"(\d{4}-\d{2}-\d{2}"
    r"|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}"
    r"|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4}"
    r"|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{2,4})"
)

SUBMISSION_RE = re.compile(
    r"(?:submission|submit|closing|due|deadline)[^\n]{0,80}?" + DATE_RE, re.I
)
CLARIFICATION_RE = re.compile(
    r"(?:clarification|questions|inquir(?:y|ies))[^\n]{0,80}?" + DATE_RE, re.I
)
BUDGET_RE = re.compile(
    r"(?:USD|EUR|GBP|NGN|₦|\$|€|£|KES|ZAR|GHS|AED|INR|₹)\s?"
    r"([\d,]+(?:\.\d{1,2})?(?:\s?(?:million|billion|thousand|m|bn|k))?)",
    re.I,
)
CURRENCY_RE = re.compile(r"(USD|EUR|GBP|NGN|₦|\$|€|£|KES|ZAR|GHS|AED|INR|₹)", re.I)
FUNDING_RE = re.compile(
    r"fund(?:ed|ing)\s+(?:by|from|source)[:\s]+([^\n\.]{3,120})", re.I
)

MAX_HEADING_LEN = 80
MAX_ITEMS = 25
MIN_ITEM_LEN = 4

# ---------------------------------------------------------------------------
# Document text extraction
# ---------------------------------------------------------------------------
def extract_text(data: bytes, filename: str) -> str:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        reader = PyPDF2.PdfReader(io.BytesIO(data))
        text = "\n".join((p.extract_text() or "") for p in reader.pages)
    elif lower.endswith(".docx"):
        doc = docx.Document(io.BytesIO(data))
        text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    else:
        raise ValueError(f"Unsupported file type: {filename}")

    text = text.strip()
    if not text:
        raise ValueError(
            "No extractable text found. The file may be a scanned image."
        )
    return text

# ---------------------------------------------------------------------------
# Rule-based analysis
# ---------------------------------------------------------------------------
def classify_heading(line: str) -> Optional[str]:
    if len(line) > MAX_HEADING_LEN:
        return None
    cleaned = line.strip().strip(":").strip(".").lower()
    for key, kws in SECTIONS.items():
        for kw in kws:
            if cleaned == kw or cleaned.startswith(kw + ":"):
                return key
            if re.match(rf"^[\d\.\)\s\-]*{re.escape(kw)}$", cleaned):
                return key
    return None


def clean_item(line: str) -> str:
    line = re.sub(
        r"^\s*(?:[\-\*\u2022\u25cf\u25aa]|\(?\d+[\.\)]|\(?[a-zA-Z][\.\)])\s*",
        "",
        line,
    ).strip()
    return "" if re.fullmatch(r"\d{1,3}", line) else line


def analyze(text: str) -> dict:
    lines = [ln.strip() for ln in text.splitlines()]
    collected = {k: [] for k in SECTIONS}
    current = None

    for line in lines:
        if not line:
            current = None
            continue
        heading = classify_heading(line)
        if heading:
            current = heading
            continue
        if current is None:
            continue
        item = clean_item(line)
        if item and len(item) >= MIN_ITEM_LEN and len(collected[current]) < MAX_ITEMS:
            collected[current].append(item)

    result = {
        "summary": lines[0][:300] if lines else None,
        "submission_deadline": None,
        "clarification_deadline": None,
        "estimated_value": None,
        "currency": None,
        "funding_source": None,
        **collected,
    }

    m = SUBMISSION_RE.search(text)
    if m:
        result["submission_deadline"] = m.group(1)
    m = CLARIFICATION_RE.search(text)
    if m:
        result["clarification_deadline"] = m.group(1)
    m = BUDGET_RE.search(text)
    if m:
        result["estimated_value"] = m.group(1).strip()
    m = CURRENCY_RE.search(text)
    if m:
        result["currency"] = m.group(1).upper()
    m = FUNDING_RE.search(text)
    if m:
        result["funding_source"] = m.group(1).strip()

    return result

# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------
def esc(value: str) -> str:
    return escape_markdown(str(value), version=2)


def bullet_section(title: str, items: List[str]) -> List[str]:
    items = [i for i in items if i and i.strip()]
    if not items:
        return []
    out = [f"*{esc(title)}*"]
    out.extend(f"• {esc(i)}" for i in items)
    out.append("")
    return out


def format_result(r: dict) -> str:
    lines: List[str] = []

    if r.get("summary"):
        lines.append(f"*📋 Summary*\n{esc(r['summary'])}\n")

    lines.extend(bullet_section("✅ Requirements", r["requirements"]))
    lines.extend(bullet_section("📄 Required Documents", r["required_documents"]))
    lines.extend(bullet_section("🎯 Eligibility Criteria", r["eligibility_criteria"]))
    lines.extend(bullet_section("📊 Evaluation Criteria", r["evaluation_criteria"]))

    deadline_lines = []
    if r["submission_deadline"]:
        deadline_lines.append(f"• Submission: {esc(r['submission_deadline'])}")
    if r["clarification_deadline"]:
        deadline_lines.append(f"• Clarification: {esc(r['clarification_deadline'])}")
    if deadline_lines:
        lines.append("*⏰ Deadlines*")
        lines.extend(deadline_lines)
        lines.append("")

    budget_lines = []
    if r["estimated_value"]:
        currency = f" {r['currency']}" if r["currency"] else ""
        budget_lines.append(f"• Estimated value: {esc(r['estimated_value'])}{esc(currency)}")
    if r["funding_source"]:
        budget_lines.append(f"• Funding source: {esc(r['funding_source'])}")
    if budget_lines:
        lines.append("*💰 Budget*")
        lines.extend(budget_lines)
        lines.append("")

    lines.extend(bullet_section("⚠️ Important Clauses", r["important_clauses"]))

    if not lines:
        return "_No structured information could be extracted from this document._"

    return "\n".join(lines).strip()


def split_message(text: str, size: int = 3500) -> List[str]:
    if len(text) <= 4096:
        return [text]
    chunks, current, length = [], [], 0
    for line in text.splitlines(keepends=True):
        if length + len(line) > size and current:
            chunks.append("".join(current))
            current, length = [], 0
        current.append(line)
        length += len(line)
    if current:
        chunks.append("".join(current))
    return chunks

# ---------------------------------------------------------------------------
# Telegram handlers
# ---------------------------------------------------------------------------
WELCOME = (
    "👋 *Welcome to the Tender Analysis Bot.*\n\n"
    "Send me a tender document in PDF or DOCX format and I will extract:\n"
    "• Eligibility requirements and deadlines\n"
    "• Required submission documents\n"
    "• Evaluation criteria and budget details\n"
    "• Important contractual clauses\n\n"
    f"_Maximum file size: {MAX_FILE_MB} MB._"
)


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message:
        await update.effective_message.reply_text(WELCOME, parse_mode=ParseMode.MARKDOWN)


async def document_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    if msg is None or msg.document is None:
        return

    doc = msg.document
    filename = doc.file_name or "document"

    if not filename.lower().endswith((".pdf", ".docx")):
        await msg.reply_text("❌ Only PDF and DOCX files are supported.")
        return

    if doc.file_size and doc.file_size > MAX_FILE_BYTES:
        await msg.reply_text(f"❌ File exceeds the {MAX_FILE_MB} MB limit.")
        return

    status = await msg.reply_text("📥 Downloading document...")

    try:
        tg_file = await context.bot.get_file(doc.file_id)
        data = bytes(await tg_file.download_as_bytearray())

        await status.edit_text("📄 Extracting text...")
        text = extract_text(data, filename)

        await status.edit_text("🔍 Analyzing document...")
        result = analyze(text)
        formatted = format_result(result)
        chunks = split_message(formatted)

        await status.edit_text("✅ Analysis complete.")
        total = len(chunks)
        for i, chunk in enumerate(chunks, start=1):
            header = f"📊 Part {i}/{total}\n\n" if total > 1 else ""
            await msg.reply_text(
                header + chunk,
                parse_mode=ParseMode.MARKDOWN_V2,
                disable_web_page_preview=True,
            )

    except ValueError as exc:
        await status.edit_text(f"❌ {exc}")
    except Exception:
        log.exception("Failed to process document")
        await status.edit_text("❌ An unexpected error occurred. Please try again.")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    log.error("Update caused error: %s", context.error, exc_info=context.error)

# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
def main() -> None:
    log.info("Starting tender analysis bot (rule-based)")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler(["start", "help"], start_cmd))
    app.add_handler(MessageHandler(filters.Document.ALL, document_cmd))
    app.add_error_handler(error_handler)
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
