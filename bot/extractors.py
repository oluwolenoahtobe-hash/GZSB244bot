"""Text extraction from supported document formats."""
import io
import logging
from typing import Callable, Dict

import docx
import PyPDF2

logger = logging.getLogger(__name__)


class UnsupportedFileTypeError(ValueError):
    """Raised when an unsupported file type is provided."""


class EmptyDocumentError(ValueError):
    """Raised when no extractable text is found in the document."""


def _extract_pdf(data: bytes) -> str:
    reader = PyPDF2.PdfReader(io.BytesIO(data))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)


def _extract_docx(data: bytes) -> str:
    document = docx.Document(io.BytesIO(data))
    paragraphs = [p.text for p in document.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


_EXTRACTORS: Dict[str, Callable[[bytes], str]] = {
    ".pdf": _extract_pdf,
    ".docx": _extract_docx,
}


def _get_suffix(filename: str) -> str:
    dot = filename.rfind(".")
    return filename[dot:].lower() if dot != -1 else ""


def extract_text(data: bytes, filename: str) -> str:
    """Extract plain text from a supported document."""
    suffix = _get_suffix(filename)
    extractor = _EXTRACTORS.get(suffix)
    if extractor is None:
        raise UnsupportedFileTypeError(
            f"Unsupported file type '{suffix}'. Supported: {sorted(_EXTRACTORS)}"
        )

    try:
        text = extractor(data)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Extraction failed for %s", filename)
        raise EmptyDocumentError(f"Failed to parse {suffix} file: {exc}") from exc

    text = text.strip()
    if not text:
        raise EmptyDocumentError(
            "No extractable text found. The document may be a scanned image "
            "without an OCR text layer."
        )

    logger.info("Extracted %d characters from %s (%s)", len(text), filename, suffix)
    return text
