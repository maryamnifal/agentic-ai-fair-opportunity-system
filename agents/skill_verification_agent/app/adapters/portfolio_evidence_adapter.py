"""
Adapter: Member A's Portfolio Evidence Agent -> Member B's EvidenceItem schema.

WHY THIS EXISTS
----------------
Member B was built and tested against a stub evidence schema (one EvidenceItem
per project, with a full description and a list of extracted skills), per the
brief's instruction to build independently and swap in real evidence later.

Member A's actual service (agents/portfolio_evidence_agent in the group repo)
returns a DIFFERENT shape from POST /extract-evidence:

{
  "freelancer_id": "fl_001",
  "agent": "portfolio_evidence_agent",
  "agent_version": "1.0.0",
  "extracted_at": "2026-...",
  "evidence_items": [
    {
      "skill": "Django",
      "skill_category": "web_framework",
      "source_type": "portfolio_project",   # portfolio_project | certificate | code_sample | work_description
      "source_ref": "proj_001",              # id of the specific project/certificate/etc.
      "source_excerpt": "built server-side APIs with Django and REST API",
      "extraction_method": "ner" | "llm" | "both",
      "confidence": 0.95,
      "reasoning": "Explicit mention of Django in portfolio_project.",
      "evidence_id": "ev_001"
    },
    ...
  ],
  "unmapped_terms": [...],
  "processing_notes": [...]
}

Her evidence_items are already ONE SKILL EACH -- not grouped by project, and
with only a short excerpt window rather than a full description.

WHAT THIS ADAPTER DOES
-----------------------
Member B's matching engine (matching.py) needs evidence grouped by SOURCE, not
by skill, because its "strong implied match" logic depends on which skills
co-occurred in the same piece of evidence (e.g. "Django implies Python" only
holds if Django and the Python claim are being checked against the same
project). So this adapter re-groups her flat per-skill items by
(source_type, source_ref) and rebuilds one EvidenceItem per source:

  - evidence_id      -> the source_ref itself (stable, human-readable)
  - project           -> "{source_type}:{source_ref}" (a readable label)
  - description       -> all of that source's excerpts, joined
  - extracted_skills  -> every canonical skill found in that source

No changes to matching.py, agent.py, schemas.py, or validation.py were needed
-- this adapter is the ONLY new code required to consume real evidence.
"""

from collections import defaultdict
from typing import Dict, List, Tuple

from app.schemas import EvidenceItem


def adapt_portfolio_evidence(member_a_response: dict) -> List[EvidenceItem]:
    """
    Convert Member A's raw /extract-evidence response into a list of
    EvidenceItem objects that SkillVerificationAgent.verify() can consume
    unchanged.
    """
    grouped: Dict[Tuple[str, str], dict] = defaultdict(
        lambda: {"skills": [], "excerpts": []}
    )

    for item in member_a_response.get("evidence_items", []):
        source_type = item.get("source_type") or "unknown_source"
        source_ref = item.get("source_ref") or "unknown_ref"
        key = (source_type, source_ref)

        skill = item.get("skill")
        if skill and skill not in grouped[key]["skills"]:
            grouped[key]["skills"].append(skill)

        excerpt = (item.get("source_excerpt") or "").strip()
        if excerpt and excerpt not in grouped[key]["excerpts"]:
            grouped[key]["excerpts"].append(excerpt)

    evidence_items: List[EvidenceItem] = []
    for (source_type, source_ref), payload in grouped.items():
        description = " ".join(payload["excerpts"]).strip()
        if not description:
            description = f"Evidence from {source_type} '{source_ref}'."

        evidence_items.append(
            EvidenceItem(
                evidence_id=str(source_ref),
                project=f"{source_type}:{source_ref}",
                description=description,
                extracted_skills=payload["skills"],
            )
        )

    return evidence_items


def adapt_candidate_id(member_a_response: dict) -> str:
    """Member A calls it freelancer_id; Member B's schema calls it candidate_id."""
    return (member_a_response.get("freelancer_id") or "").strip()
