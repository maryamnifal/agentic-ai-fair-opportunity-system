# Skill Verification Agent (Member B)

Part of *Agentic AI-Based Fair Opportunity and Capability Verification System for New Freelancers* (IT 3041).

## What this does

Given a freelancer's **claimed skills** and **structured portfolio evidence** (produced upstream by
Member A's Portfolio Evidence Agent), this service determines, per skill, whether it is:

- `supported` — evidence directly confirms or strongly implies the skill
- `weakly_supported` — evidence is only loosely/partially related
- `unsupported` — no relevant evidence found
- `contradicted` — evidence explicitly indicates a different, exclusive technology choice

along with a **confidence score (0–1)**, the **evidence_ids** that contributed, and a plain-English
**reason**.

### What this does NOT do

It does **not** verify identity, check certificates, or prove real-world competence. It only checks
**claim-evidence consistency** — whether a claim is *supported by the evidence supplied to it*.

## Architecture

```
Member A (Portfolio Evidence Agent)
        │  structured evidence JSON
        ▼
POST /api/verify-skills  (FastAPI)
        │
        ├─ Pydantic validation (structure/types/lengths) → 422 on failure
        ├─ validation.py: sanitization + business-rule checks → 400 on failure
        ├─ agent.py: SkillVerificationAgent
        │     └─ matching.py: per-skill scoring against skill_taxonomy.py
        ▼
Evidence-supported skills JSON
        │
        ▼
Member C (Job Compatibility / IR Agent)
```

## Folder structure

```
app/
  schemas.py         Pydantic input/output models (the contract with A/C/D)
  skill_taxonomy.py  explainable skill-relatedness lookup table
  matching.py         scoring engine (exact / implied / weak / contradiction)
  agent.py             orchestrator (dedup claims, run matching, assemble response)
  validation.py       sanitization + business-rule validation
  security.py          password hashing (bcrypt) — NOT auth/JWT (Member D's scope)
  main.py               FastAPI app, POST /api/verify-skills, error handlers
data/
  synthetic_freelancers.json   15 synthetic freelancer profiles for testing
tests/
  test_matching.py     unit tests for the scoring engine
  test_agent.py         unit tests for the orchestrator (dedup)
  test_api.py            API-level tests (status codes, error handling)
```

## Running it

```bash
pip install -r requirements.txt --break-system-packages   # or use a venv
uvicorn app.main:app --reload
```

API docs: `http://localhost:8000/docs`
Health check: `GET /health`
Demo page: `http://localhost:8000/demo`

**Note on the demo page:** this is a demo for *this component only*, so I can visually check my
own endpoint and use it in the mid-evaluation demo / Gen AI video. It is not the group project's
final UI — that's Member D's responsibility, integrated with auth and the other agents.

## Example request

```bash
curl -X POST http://localhost:8000/api/verify-skills \
  -H "Content-Type: application/json" \
  -d @- <<'EOF'
{
  "candidate_id": "F001",
  "claimed_skills": ["Python", "Django", "Machine Learning", "React"],
  "evidence": [
    {
      "evidence_id": "E001",
      "project": "Online Booking System",
      "description": "Built a web-based booking platform using Django and REST APIs.",
      "extracted_skills": ["Python", "Django", "REST API", "Web Development"]
    }
  ]
}
EOF
```

## Testing

```bash
pytest -v
```

20 tests covering: strong match, implied match, weak match, no evidence, contradiction,
multiple supporting evidence items, unrelated-skill non-assumption, duplicate skill dedup,
missing fields, malformed JSON, invalid types, oversized input.

## Scoring approach (for the viva)

The engine is a **rule-based lookup**, not an ML model — Member A already did NLP/LLM
extraction upstream, so this module only reasons about the *relationship* between a claim
and already-extracted evidence:

| Case | Example | Confidence band |
|---|---|---|
| Exact match in evidence + named in description | Claim "Django", evidence says "Django REST API" | 0.97 |
| Exact match in extracted_skills only | Claim "Python", evidence lists "Python" | 0.90 |
| Strong implied match (framework → language) | Claim "Python", evidence only shows "Django" | 0.75 |
| Weak/loose relation | Claim "Machine Learning", evidence shows "Pandas" | 0.35 |
| No relation found | Claim "React", evidence is a Java backend | 0.05 |
| Explicit contradiction | Claim "Python", evidence says "entirely in Java" | 0.02 |

Status is then derived from the confidence band (`≥0.60` → supported, `0.20–0.59` → weakly
supported, `<0.20` → unsupported; contradiction is its own status regardless of band).

## Integration notes

- **From Member A**: her actual `POST /extract-evidence` output (see
  `agents/portfolio_evidence_agent` in the group repo) is a flat list of one
  evidence item **per skill**, with a short excerpt rather than a full project
  description, and uses `freelancer_id` instead of `candidate_id`. This is
  different from the stub schema Member B was built and tested against. Rather
  than rewrite `matching.py`/`agent.py`, an **adapter**
  (`app/adapters/portfolio_evidence_adapter.py`) re-groups her per-skill items
  by source (project/certificate/code sample/work description) into the
  `EvidenceItem` shape the matching engine already expects. A new endpoint,
  **`POST /api/verify-skills-from-portfolio`**, accepts her raw response body
  directly (plus `claimed_skills`), runs it through the adapter, and returns
  the same `VerifyResponse` as `/api/verify-skills`. The original endpoint is
  unchanged and still works with hand-built evidence (e.g. for Member C/D to
  test against without running Member A's service).
- **To Member C**: the response gives evidence-supported skills with confidence scores and
  evidence_ids/reasons, so Member C never needs to re-read raw portfolio text — only the
  verified skill list.
- **Security boundary**: this component owns input validation, sanitization, and password
  hashing. JWT auth, role-based authorization, rate limiting, and encryption-at-rest belong
  to Member D and should wrap this API rather than be reimplemented here.

### Two ways to call this service

| Endpoint | When to use |
|---|---|
| `POST /api/verify-skills` | You already have evidence in Member B's own `EvidenceItem` shape (e.g. synthetic test data, or Member C/D testing without running Member A's service) |
| `POST /api/verify-skills-from-portfolio` | You have Member A's raw `/extract-evidence` response and want it verified directly, no manual conversion |
