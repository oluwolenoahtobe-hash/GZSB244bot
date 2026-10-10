"""Keyword and regex patterns used for rule-based tender analysis.

Edit the lists below to support additional languages or tender formats.
All matching is case-insensitive.
"""
import re
from typing import Dict, List, Pattern

# ---------------------------------------------------------------------------
# Section heading keywords
# ---------------------------------------------------------------------------
# When the analyzer finds a line that matches one of these headings, it starts
# collecting the lines beneath it until the next heading is found.

SECTION_KEYWORDS: Dict[str, List[str]] = {
    "requirements": [
        "requirements",
        "mandatory requirements",
        "general requirements",
        "minimum requirements",
        "bidder requirements",
    ],
    "required_documents": [
        "required documents",
        "documents required",
        "submission documents",
        "documents to be submitted",
        "required submissions",
    ],
    "eligibility_criteria": [
        "eligibility criteria",
        "eligibility requirements",
        "qualification criteria",
        "qualifications",
        "prequalification",
    ],
    "evaluation_criteria": [
        "evaluation criteria",
        "evaluation method",
        "assessment criteria",
        "scoring criteria",
        "technical evaluation",
        "financial evaluation",
    ],
    "budget": [
        "budget",
        "estimated value",
        "contract value",
        "tender value",
        "estimated cost",
        "funding",
    ],
    "important_clauses": [
        "important clauses",
        "special conditions",
        "general conditions",
        "contract terms",
        "terms and conditions",
        "special terms",
    ],
}

# ---------------------------------------------------------------------------
# Deadline patterns
# ---------------------------------------------------------------------------
# These regexes are applied to the full text to find dates that match a
# particular deadline type.

DATE_REGEX = (
    r"("
    r"\d{4}-\d{2}-\d{2}"                       # 2025-06-01
    r"|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}"          # 01/06/2025 or 1-6-25
    r"|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4}"
    r"|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{2,4}"
    r")"
)

DEADLINE_PATTERNS: Dict[str, Pattern] = {
    "submission_deadline": re.compile(
        r"(?:submission|submit|closing|due|deadline)[^\n]{0,80}?" + DATE_REGEX,
        re.IGNORECASE,
    ),
    "clarification_deadline": re.compile(
        r"(?:clarification|questions|inquir(?:y|ies)|enquir(?:y|ies))"
        r"[^\n]{0,80}?" + DATE_REGEX,
        re.IGNORECASE,
    ),
    "opening_date": re.compile(
        r"(?:opening|bid opening|tender opening)[^\n]{0,80}?" + DATE_REGEX,
        re.IGNORECASE,
    ),
    "pre_bid_meeting": re.compile(
        r"(?:pre[\s-]?bid|pre[\s-]?tender)[^\n]{0,80}?" + DATE_REGEX,
        re.IGNORECASE,
    ),
}

# ---------------------------------------------------------------------------
# Budget patterns
# ---------------------------------------------------------------------------

CURRENCY_REGEX = re.compile(
    r"(USD|EUR|GBP|NGN|NG₦|₦|\$|€|£|KES|ZAR|GHS|AED|INR|₹)",
    re.IGNORECASE,
)

BUDGET_AMOUNT_REGEX = re.compile(
    r"(?:USD|EUR|GBP|NGN|₦|\$|€|£|KES|ZAR|GHS|AED|INR|₹)\s?"
    r"([\d,]+(?:\.\d{1,2})?(?:\s?(?:million|billion|thousand|m|bn|k))?)",
    re.IGNORECASE,
)

FUNDING_SOURCE_REGEX = re.compile(
    r"fund(?:ed|ing)\s+(?:by|from|source)[:\s]+([^\n\.]{3,120})",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Summary heuristic keywords
# ---------------------------------------------------------------------------

SUMMARY_KEYWORDS = (
    "invitation to bid",
    "request for proposal",
    "request for quotation",
    "expression of interest",
    "call for proposals",
    "invitation to tender",
    "tender notice",
    "procurement notice",
)
