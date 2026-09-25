"""
Matching + scoring engine for the Skill Verification Agent.

Design goal: explainable, not "smart". Every score maps to a rule you can
state out loud in a viva. No ML model is used for scoring itself (Member A
already did the NLP/LLM extraction upstream) -- this module only reasons
about the *relationship* between a claimed skill and already-extracted
evidence skills/text.
"""

import re
from dataclasses import dataclass, field
from typing import List

from app.schemas import EvidenceItem
from app.skill_taxonomy import (
    STRONG_IMPLIES,
    WEAK_RELATED,
    EXCLUSIVITY_MARKERS,
    normalize,
    family_of,
)

# Confidence bands. Kept as named constants so they're easy to tune/defend.
CONF_EXACT_IN_DESCRIPTION = 0.97   # exact skill in extracted_skills AND named in description text
CONF_EXACT = 0.90                  # exact skill present in extracted_skills
CONF_STRONG_IMPLIED = 0.75         # evidence skill strongly implies the claim (e.g. Django -> Python)
CONF_WEAK_RELATED = 0.35           # loose/partial relation only
CONF_UNSUPPORTED = 0.05            # no relation found at all
CONF_CONTRADICTED = 0.02           # evidence explicitly contradicts the claim

STATUS_SUPPORTED = "supported"
STATUS_WEAK = "weakly_supported"
STATUS_UNSUPPORTED = "unsupported"
STATUS_CONTRADICTED = "contradicted"

# Below this confidence, a claim with no supporting evidence at all is unsupported.
WEAK_THRESHOLD = 0.20
SUPPORTED_THRESHOLD = 0.60


@dataclass
class SkillVerdict:
    skill: str
    status: str
    confidence: float
    evidence_ids: List[str] = field(default_factory=list)
    reason: str = ""


def _is_contradicted(claim_lower: str, evidence: EvidenceItem) -> bool:
    """
    A contradiction is flagged when the evidence text uses an exclusivity
    marker (e.g. "entirely in Java") for a technology family DIFFERENT from
    the claimed skill's family, and the claimed skill's family is not
    otherwise present in extracted_skills.
    """
    desc = evidence.description.lower()
    claim_family = family_of(claim_lower)
    if claim_family is None:
        return False

    extracted_lower = [normalize(s) for s in evidence.extracted_skills]
    if claim_family in extracted_lower or claim_lower in extracted_lower:
        return False  # claim's own family already shows up as evidence; not a contradiction

    # If an exclusivity marker is present ("built entirely in Java") AND the
    # description mentions (as a whole word, not a substring -- "Java" is not
    # "JavaScript") a DIFFERENT family's member, but never the claim's own
    # family, treat it as a contradiction.
    if any(marker in desc for marker in EXCLUSIVITY_MARKERS):
        mentions_other_family = False
        for family, members in _families_with_members():
            if family == claim_family:
                continue
            if any(_mentioned_in_text(m, desc) for m in members):
                mentions_other_family = True
                break
        if mentions_other_family:
            return True
    return False


def _families_with_members():
    from app.skill_taxonomy import LANGUAGE_FAMILIES
    return list(LANGUAGE_FAMILIES.items())


def _mentioned_in_text(skill_lower: str, text_lower: str) -> bool:
    """
    Word-boundary-aware check for whether a skill is actually named in free
    text, rather than a raw substring check. A raw `"java" in "javascript"`
    check is a false positive -- "Java" is not "JavaScript". Skill names
    can contain characters (like '.', '#', '+') that aren't \\w, so we
    escape the skill and only relax the boundary on the alnum edges.
    """
    if not skill_lower:
        return False
    pattern = r"(?<![a-z0-9])" + re.escape(skill_lower) + r"(?![a-z0-9])"
    return re.search(pattern, text_lower) is not None


def score_skill_against_evidence(claim: str, evidence_list: List[EvidenceItem]) -> SkillVerdict:
    """
    Score a single claimed skill against ALL evidence items, keeping the
    best (highest-confidence) match, and aggregating evidence_ids from every
    item that contributes support at or above the weak threshold.
    """
    claim_lower = normalize(claim)

    best_confidence = 0.0
    best_reason = "No evidence supports this skill."
    best_status = STATUS_UNSUPPORTED
    contributing_ids: List[str] = []
    contradicting_ids: List[str] = []

    for ev in evidence_list:
        extracted_lower = [normalize(s) for s in ev.extracted_skills]
        desc_lower = ev.description.lower()

        # 1. Contradiction check first -- overrides everything else for this item
        if _is_contradicted(claim_lower, ev):
            contradicting_ids.append(ev.evidence_id)
            continue

        # 2. Exact match
        if claim_lower in extracted_lower:
            conf = CONF_EXACT_IN_DESCRIPTION if _mentioned_in_text(claim_lower, desc_lower) else CONF_EXACT
            reason = (
                f"'{claim}' is explicitly listed in evidence from project '{ev.project}'"
                + (" and mentioned in its description." if _mentioned_in_text(claim_lower, desc_lower) else ".")
            )
            contributing_ids.append(ev.evidence_id)
            if conf > best_confidence:
                best_confidence, best_reason, best_status = conf, reason, STATUS_SUPPORTED
            continue

        # 3. Strong implied match: does any extracted evidence skill strongly imply the claim?
        implied_by = [
            es for es in extracted_lower
            if claim_lower in STRONG_IMPLIES.get(es, [])
        ]
        if implied_by:
            reason = (
                f"Evidence from project '{ev.project}' uses {implied_by[0].title()}, "
                f"which strongly implies {claim}."
            )
            contributing_ids.append(ev.evidence_id)
            if CONF_STRONG_IMPLIED > best_confidence:
                best_confidence, best_reason, best_status = (
                    CONF_STRONG_IMPLIED, reason, STATUS_SUPPORTED,
                )
            continue

        # 4. Weak/loose relation
        weak_by = [
            es for es in extracted_lower
            if claim_lower in WEAK_RELATED.get(es, [])
        ]
        if weak_by:
            reason = (
                f"Evidence from project '{ev.project}' mentions {weak_by[0].title()}, "
                f"which is loosely related to {claim} but does not directly confirm it."
            )
            contributing_ids.append(ev.evidence_id)
            if CONF_WEAK_RELATED > best_confidence:
                best_confidence, best_reason, best_status = (
                    CONF_WEAK_RELATED, reason, STATUS_WEAK,
                )

    if contradicting_ids and best_confidence < SUPPORTED_THRESHOLD:
        return SkillVerdict(
            skill=claim,
            status=STATUS_CONTRADICTED,
            confidence=CONF_CONTRADICTED,
            evidence_ids=contradicting_ids,
            reason=(
                f"Evidence ({', '.join(contradicting_ids)}) explicitly indicates a "
                f"different, exclusive technology choice that conflicts with the "
                f"claim '{claim}'."
            ),
        )

    if best_confidence <= 0.0:
        return SkillVerdict(
            skill=claim,
            status=STATUS_UNSUPPORTED,
            confidence=CONF_UNSUPPORTED,
            evidence_ids=[],
            reason=f"No portfolio evidence mentions or implies '{claim}'.",
        )

    # Re-derive final status from confidence bands for consistency
    if best_confidence >= SUPPORTED_THRESHOLD:
        final_status = STATUS_SUPPORTED
    elif best_confidence >= WEAK_THRESHOLD:
        final_status = STATUS_WEAK
    else:
        final_status = STATUS_UNSUPPORTED

    # de-duplicate evidence ids, preserve order
    seen = set()
    dedup_ids = [i for i in contributing_ids if not (i in seen or seen.add(i))]

    return SkillVerdict(
        skill=claim,
        status=final_status,
        confidence=round(best_confidence, 2),
        evidence_ids=dedup_ids,
        reason=best_reason,
    )
