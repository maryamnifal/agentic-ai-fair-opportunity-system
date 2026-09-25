"""
Input validation and sanitization for Member B.

Two layers are used deliberately:
  1. Pydantic (in schemas.py) handles STRUCTURAL validation: required
     fields, types, lengths, malformed JSON -> automatic 422 responses.
  2. This module handles SANITIZATION and a few checks that are awkward
     to express purely as field types (e.g. stripping control characters,
     rejecting suspicious markup, checking for genuinely empty/whitespace
     content after trimming).

Scope note: this is NOT meant to defend against SQL injection (no SQL is
built from this input) or auth/authorization (that's Member D). It defends
the Skill Verification Agent's own processing from malformed/malicious
text payloads.
"""

import re
from typing import List, Tuple

from app.schemas import VerifyRequest

# Control characters (except normal whitespace) are stripped -- these have no
# legitimate reason to appear in skill names or evidence text and can be used
# to smuggle formatting/log-injection payloads.
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

# Very cheap markup/script guard. This is defense-in-depth, not a full
# sanitizer -- the API only ever returns this text back as JSON (never
# rendered as HTML), so the main risk is downstream consumers (e.g. a future
# UI) rendering it unsafely. We still strip obvious script tags.
_SCRIPT_TAG_RE = re.compile(r"<\s*script.*?>.*?<\s*/\s*script\s*>", re.IGNORECASE | re.DOTALL)


def sanitize_text(value: str) -> str:
    """Strip control characters, obvious <script> payloads, and collapse whitespace."""
    if value is None:
        return value
    cleaned = _SCRIPT_TAG_RE.sub("", value)
    cleaned = _CONTROL_CHARS_RE.sub("", cleaned)
    cleaned = cleaned.strip()
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned


def sanitize_request(request: VerifyRequest) -> VerifyRequest:
    """Return a new VerifyRequest with all free-text fields sanitized."""
    request.candidate_id = sanitize_text(request.candidate_id)
    request.claimed_skills = [sanitize_text(s) for s in request.claimed_skills]
    for ev in request.evidence:
        ev.project = sanitize_text(ev.project)
        ev.description = sanitize_text(ev.description)
        ev.extracted_skills = [sanitize_text(s) for s in ev.extracted_skills]
    return request


def business_rule_errors(request: VerifyRequest) -> List[str]:
    """
    Checks that pass Pydantic's structural validation but still represent
    invalid business input. Returns a list of human-readable error strings
    (empty list == valid).
    """
    errors: List[str] = []

    if not request.candidate_id.strip():
        errors.append("candidate_id must not be empty or whitespace-only.")

    non_empty_skills = [s for s in request.claimed_skills if s.strip()]
    if not non_empty_skills:
        errors.append("claimed_skills must contain at least one non-empty skill.")

    ids_seen = set()
    for ev in request.evidence:
        if not ev.evidence_id.strip():
            errors.append("evidence_id must not be empty or whitespace-only.")
        if ev.evidence_id in ids_seen:
            errors.append(f"duplicate evidence_id '{ev.evidence_id}' found in request.")
        ids_seen.add(ev.evidence_id)
        if not ev.description.strip():
            errors.append(f"evidence '{ev.evidence_id}' has an empty description.")

    return errors


def validate_and_sanitize(request: VerifyRequest) -> Tuple[VerifyRequest, List[str]]:
    """Convenience wrapper: sanitize first, then run business-rule checks."""
    request = sanitize_request(request)
    errors = business_rule_errors(request)
    return request, errors
