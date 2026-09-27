# Skill Verification Agent

Agent B in the FairRank AI pipeline.

This FastAPI service compares a candidate's claimed skills with structured
portfolio evidence and returns an explainable verdict for each claim. It checks
claim-to-evidence consistency; it does not prove identity, credentials, or
real-world competence.

## Role In The Pipeline

```text
Agent A: Portfolio Evidence
        |
        | structured evidence
        v
Agent B: Skill Verification
        |
        | verified skills
        v
Agent C: Job Compatibility
        |
        v
Agent D: Fair Ranking
```

Agent D calls the integration endpoint during the full pipeline. Agent B can
also be run independently for API and unit testing.

## Verdicts

Each claimed skill receives one of these statuses:

- `supported`: evidence directly confirms or strongly implies the claim
- `weakly_supported`: evidence is related but incomplete or indirect
- `unsupported`: no relevant evidence was found
- `contradicted`: evidence indicates an incompatible or exclusive alternative

Responses also include confidence, contributing evidence IDs, and a plain
English reason.

## Endpoints

```text
GET  /health
GET  /demo
POST /api/verify-skills
POST /api/verify-skills-from-portfolio
```

`/api/verify-skills` accepts Agent B's native request shape. Use it when the
caller already has `EvidenceItem` objects.

`/api/verify-skills-from-portfolio` accepts Agent A's raw `/extract-evidence`
response and adapts it internally. This is the endpoint used by Agent D.

## Request Examples

### Native evidence request

```bash
curl -X POST http://localhost:8001/api/verify-skills \
  -H "Content-Type: application/json" \
  -d '{
    "candidate_id": "F001",
    "claimed_skills": ["Python", "Django", "React"],
    "evidence": [
      {
        "evidence_id": "E001",
        "source_type": "portfolio_project",
        "source_ref": "proj_001",
        "source_excerpt": "Built a booking platform using Django and REST APIs.",
        "extracted_skills": ["Python", "Django", "REST API"]
      }
    ]
  }'
```

### Agent A integration request

The integration endpoint takes the claimed skills alongside Agent A's raw
response:

```bash
curl -X POST http://localhost:8001/api/verify-skills-from-portfolio \
  -H "Content-Type: application/json" \
  -d '{
    "claimed_skills": ["Python", "Django", "REST API"],
    "portfolio_evidence": {
      "freelancer_id": "F001",
      "evidence_items": [
        {
          "skill": "Django",
          "skill_category": "web_framework",
          "source_type": "portfolio_project",
          "source_ref": "proj_001",
          "source_excerpt": "Built a booking platform using Django and REST APIs.",
          "extraction_method": "ner",
          "confidence": 0.95,
          "reasoning": "Explicit mention of Django in a portfolio project."
        }
      ],
      "unmapped_terms": [],
      "processing_notes": []
    }
  }'
```

Agent D sends this second request internally as part of
`POST /api/full-pipeline`.

## Response Shape

A successful response includes the candidate ID and one verification result per
claimed skill. A result contains the claim, verdict, confidence, evidence IDs,
and reasoning. Validation failures return structured JSON with HTTP `400` or
`422`, depending on whether the request is malformed or violates a business
rule.

## Scoring Model

Verification is deterministic and rule-based. Agent B does not run an LLM. It
matches claims against the evidence supplied by Agent A using the skill
relationship taxonomy.

| Relationship | Typical result |
| --- | --- |
| Exact skill in evidence | High-confidence `supported` |
| Strong framework/language implication | `supported` with lower confidence |
| Related but incomplete evidence | `weakly_supported` |
| No relationship | `unsupported` |
| Explicitly incompatible technology | `contradicted` |

The score is derived from the best matching evidence item, and duplicate claims
are normalized before the final response is assembled.

## Validation And Security Boundary

This service owns request validation, sanitization, length limits, and business
input checks. It does not own user authentication or authorization. JWT login,
rate limiting, and encryption-at-rest belong to Agent D, which is the public
application boundary.

## Run Locally

From this directory:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

Then open:

```text
http://localhost:8001/docs
http://localhost:8001/demo
http://localhost:8001/health
```

## Run With Docker Compose

From the repository root:

```bash
docker compose up -d --build skill-verification-agent
curl http://localhost:8001/health
```

Inside the Compose network, Agent D reaches this service at:

```text
http://skill-verification-agent:8000
```

## Tests

```bash
pytest -v
```

The test suite covers matching relationships, implied and weak matches,
contradictions, duplicate claims, validation errors, adapter behavior, and API
responses.

## Source Layout

```text
app/
  main.py                         FastAPI routes and error handlers
  schemas.py                      request and response contracts
  agent.py                        verification orchestration
  matching.py                     deterministic scoring rules
  skill_taxonomy.py               skill relationship data
  validation.py                   sanitization and business validation
  adapters/portfolio_evidence_adapter.py
                                  Agent A response adapter
data/                            synthetic test profiles
tests/                            unit and API tests
```
