"""
ImpactFrame Security Module — PII Redactor
------------------------------------------
Removes personally identifiable information (PII) from data
before it is sent to the LLM (Gemini).

Why this matters:
- Health clinic data contains real staff names and patient identifiers
- Sending PII to external AI APIs raises privacy concerns
- Redacting names before LLM processing is a best practice
  for healthcare and NGO data systems

What gets redacted:
- Staff full names (replaced with role titles)
- Patient/respondent IDs (replaced with anonymised codes)
- Email addresses
- Phone numbers
- Any field explicitly tagged as PII

What is preserved:
- All analytical data (numbers, percentages, scores)
- Program names and categories
- Roles and job titles
- All data needed for budget decisions
"""

import re
import json
import hashlib
from typing import Any

# ── PII patterns ─────────────────────────────────────────────────
EMAIL_PATTERN    = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
PHONE_PATTERN    = re.compile(r'\b(\+?1?\s?)?(\(?\d{3}\)?[\s.-]?)?\d{3}[\s.-]?\d{4}\b')
SSN_PATTERN      = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')

# Known staff names from our dataset — in production this would
# be loaded from a secure name registry
KNOWN_STAFF_NAMES = [
    "Maria Chen", "James Okafor", "Rosa Mendez",
    "David Kim", "Angela Torres", "Patricia Williams",
    "Sung-Ji Park", "Kevin Barnes", "Linda Osei",
    "Marcus Webb", "Carmen Rivera",
]


def _anonymise_id(original_id: str) -> str:
    """
    Replace a real ID with a consistent anonymised code.
    Uses a one-way hash so the same ID always gets the same
    anonymous code — allowing cross-reference without exposing PII.
    """
    hashed = hashlib.sha256(original_id.encode()).hexdigest()[:6].upper()
    return f"RESP-{hashed}"


def redact_string(text: str) -> str:
    """Remove PII patterns from a plain text string."""
    if not isinstance(text, str):
        return text

    # Remove emails
    text = EMAIL_PATTERN.sub("[EMAIL REDACTED]", text)

    # Remove phone numbers
    text = PHONE_PATTERN.sub("[PHONE REDACTED]", text)

    # Remove SSNs
    text = SSN_PATTERN.sub("[ID REDACTED]", text)

    # Remove known staff names
    for name in KNOWN_STAFF_NAMES:
        text = text.replace(name, "[STAFF NAME REDACTED]")

    return text


def redact_record(record: dict) -> dict:
    """
    Redact PII from a single data record (dict).
    Handles specific field names we know contain PII.
    """
    if not isinstance(record, dict):
        return record

    redacted = {}
    for key, value in record.items():

        key_lower = key.lower()

        # Fields that should be fully redacted
        if any(pii_field in key_lower for pii_field in [
            "name", "email", "phone", "contact",
            "address", "ssn", "dob", "date_of_birth"
        ]):
            # For Name fields — keep role context if available
            if "name" in key_lower and isinstance(value, str):
                # Replace full name but note it was a name field
                redacted[key] = "[NAME REDACTED]"
            else:
                redacted[key] = "[REDACTED]"

        # Response IDs — anonymise rather than fully redact
        elif key_lower in ["response id", "response_id", "respondent_id", "id"]:
            redacted[key] = _anonymise_id(str(value)) if value else value

        # Staff ID — keep the ID format but anonymise
        elif key_lower in ["staff id", "staff_id"]:
            redacted[key] = _anonymise_id(str(value)) if value else value

        # String values — scan for PII patterns
        elif isinstance(value, str):
            redacted[key] = redact_string(value)

        # Lists — redact each item
        elif isinstance(value, list):
            redacted[key] = [
                redact_record(item) if isinstance(item, dict)
                else redact_string(item) if isinstance(item, str)
                else item
                for item in value
            ]

        # Nested dicts — recurse
        elif isinstance(value, dict):
            redacted[key] = redact_record(value)

        # Numbers, booleans — safe, keep as-is
        else:
            redacted[key] = value

    return redacted


def redact_dataset(data: dict) -> dict:
    """
    Redact PII from a full dataset payload as returned by the MCP server.
    Handles the nested structure: {source, records: [...]} or {source, content: str}
    """
    if not isinstance(data, dict):
        return data

    result = dict(data)

    # CSV-style datasets: list of records
    for key in ["records", "survey_responses", "budget_data",
                "population_health", "staff_availability"]:
        if key in result and isinstance(result[key], list):
            result[key] = [redact_record(r) for r in result[key]]

    # Text-style datasets: program effectiveness report
    if "report_content" in result and isinstance(result["report_content"], str):
        result["report_content"] = redact_string(result["report_content"])

    if "content" in result and isinstance(result["content"], str):
        result["content"] = redact_string(result["content"])

    return result


def redact_summary(text: str) -> str:
    """
    Final pass redaction on any LLM output before it is
    displayed or stored — catches anything the LLM may have
    reproduced from the input data.
    """
    return redact_string(text)


# ── Audit logging ─────────────────────────────────────────────────
def log_redaction_event(source: str, record_count: int) -> None:
    """
    Log that redaction occurred — without logging the actual data.
    In production this would write to a secure audit log.
    """
    print(f"[Security] Redacted {record_count} records from source: {source}")
