"""Render TenderAnalysis into Telegram-friendly MarkdownV2."""
from typing import Iterable, List

from telegram.helpers import escape_markdown

from bot.schemas import TenderAnalysis

TELEGRAM_MESSAGE_LIMIT = 4096
SAFE_CHUNK_SIZE = 3500


def _escape(value: str) -> str:
    """Escape text for Telegram MarkdownV2."""
    return escape_markdown(str(value), version=2)


def _bullet_section(title: str, items: Iterable[str]) -> List[str]:
    cleaned = [item for item in items if item and str(item).strip()]
    if not cleaned:
        return []
    lines = [f"*{_escape(title)}*"]
    lines.extend(f"• {_escape(item)}" for item in cleaned)
    lines.append("")
    return lines


def format_analysis(analysis: TenderAnalysis) -> str:
    """Produce a MarkdownV2-formatted string representing the analysis."""
    lines: List[str] = []

    if analysis.summary:
        lines.append(f"*📋 Summary*\n{_escape(analysis.summary)}\n")

    lines.extend(_bullet_section("✅ Requirements", analysis.requirements))

    deadlines = analysis.deadlines
    deadline_lines: List[str] = []
    if deadlines.submission_deadline:
        deadline_lines.append(
            f"• Submission: {_escape(deadlines.submission_deadline)}"
        )
    if deadlines.clarification_deadline:
        deadline_lines.append(
            f"• Clarification: {_escape(deadlines.clarification_deadline)}"
        )
    deadline_lines.extend(f"• {_escape(d)}" for d in deadlines.other_dates)
    if deadline_lines:
        lines.append("*⏰ Deadlines*")
        lines.extend(deadline_lines)
        lines.append("")

    lines.extend(_bullet_section("📄 Required Documents", analysis.required_documents))
    lines.extend(
        _bullet_section("🎯 Eligibility Criteria", analysis.eligibility_criteria)
    )

    if analysis.evaluation_criteria:
        lines.append("*📊 Evaluation Criteria*")
        for item in analysis.evaluation_criteria:
            weight = f" ({_escape(item.weight)})" if item.weight else ""
            lines.append(f"• {_escape(item.criterion)}{weight}")
        lines.append("")

    budget = analysis.budget
    budget_lines: List[str] = []
    if budget.estimated_value:
        currency = f" {budget.currency}" if budget.currency else ""
        budget_lines.append(
            f"• Estimated value: {_escape(budget.estimated_value)}{_escape(currency)}"
        )
    if budget.funding_source:
        budget_lines.append(f"• Funding source: {_escape(budget.funding_source)}")
    if budget_lines:
        lines.append("*💰 Budget*")
        lines.extend(budget_lines)
        lines.append("")

    lines.extend(_bullet_section("⚠️ Important Clauses", analysis.important_clauses))

    return "\n".join(lines).strip() or "_No extractable information found._"


def split_for_telegram(text: str, size: int = SAFE_CHUNK_SIZE) -> List[str]:
    """Split long messages on line boundaries to respect Telegram limits."""
    if len(text) <= TELEGRAM_MESSAGE_LIMIT:
        return [text]

    chunks: List[str] = []
    current: List[str] = []
    current_len = 0

    for line in text.splitlines(keepends=True):
        if current_len + len(line) > size and current:
            chunks.append("".join(current))
            current, current_len = [], 0
        current.append(line)
        current_len += len(line)

    if current:
        chunks.append("".join(current))
    return chunks
