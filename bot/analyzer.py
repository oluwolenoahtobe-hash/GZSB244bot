"""LLM-powered structured analysis of tender documents."""
import json
import logging
from typing import Any, Dict

from openai import APIError, APITimeoutError, OpenAI
from pydantic import ValidationError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from bot.config import get_settings
from bot.schemas import TenderAnalysis

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a senior procurement analyst specializing in tender and RFP "
    "document analysis. Extract structured information with precision.\n\n"
    "Rules:\n"
    "1. Return ONLY valid JSON conforming to the requested schema.\n"
    "2. Never invent information. If a field is absent, use null or an empty list.\n"
    "3. Preserve monetary values, dates, and identifiers exactly as written.\n"
    "4. Normalize dates to ISO 8601 (YYYY-MM-DD) when unambiguous; otherwise "
    "return the original string.\n"
    "5. Keep the summary concise (2-3 sentences) and factual.\n\n"
    "The JSON schema is:\n"
    "{\n"
    '  "summary": string | null,\n'
    '  "requirements": string[],\n'
    '  "deadlines": {\n'
    '    "submission_deadline": string | null,\n'
    '    "clarification_deadline": string | null,\n'
    '    "other_dates": string[]\n'
    "  },\n"
    '  "required_documents": string[],\n'
    '  "eligibility_criteria": string[],\n'
    '  "evaluation_criteria": [{"criterion": string, "weight": string | null}],\n'
    '  "budget": {\n'
    '    "estimated_value": string | null,\n'
    '    "currency": string | null,\n'
    '    "funding_source": string | null\n'
    "  },\n"
    '  "important_clauses": string[]\n'
    "}"
)

USER_PROMPT_TEMPLATE = (
    "Analyze the following tender document and extract all relevant "
    "information.\n\nDocument:\n\"\"\"\n{content}\n\"\"\""
)


class AnalysisError(RuntimeError):
    """Raised when the LLM returns an unusable response."""


class TenderAnalyzer:
    """Wraps the LLM client and enforces output schema validation."""

    def __init__(self) -> None:
        settings = get_settings()
        self._settings = settings
        self._client = OpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            timeout=settings.llm_request_timeout,
        )

    def analyze(self, document_text: str) -> TenderAnalysis:
        """Analyze raw tender text and return a validated result."""
        truncated = self._truncate(document_text)
        raw = self._call_llm_with_retry(truncated)
        return self._parse_and_validate(raw)

    def _truncate(self, text: str) -> str:
        limit = self._settings.max_document_chars
        if len(text) <= limit:
            return text
        logger.warning("Document truncated from %d to %d chars", len(text), limit)
        return text[:limit] + "\n\n[... document truncated ...]"

    def _call_llm_with_retry(self, content: str) -> str:
        @retry(
            stop=stop_after_attempt(self._settings.llm_max_retries),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            retry=retry_if_exception_type((APITimeoutError, APIError)),
            reraise=True,
        )
        def _call() -> str:
            response = self._client.chat.completions.create(
                model=self._settings.openai_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": USER_PROMPT_TEMPLATE.format(content=content),
                    },
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            return response.choices[0].message.content or "{}"

        return _call()

    def _parse_and_validate(self, raw: str) -> TenderAnalysis:
        try:
            payload: Dict[str, Any] = json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.error("LLM returned non-JSON payload: %s", raw[:500])
            raise AnalysisError("Model returned an invalid JSON response.") from exc

        try:
            return TenderAnalysis.model_validate(payload)
        except ValidationError as exc:
            logger.error("Schema validation failed: %s", exc)
            raise AnalysisError(
                "Model response did not match the expected schema."
            ) from exc
