# agentic-ai-fair-opportunity-system
Agentic AI-Based Fair Opportunity and Capability Verification System for New Freelancers

## Portfolio Evidence Agent
(Member A Maryam)

## Skill Verification Agent
(Member B Pirushalini)

## Job Compatibility Agent
(Member C Thushanya)

## Fair Ranking Agent
(Member D Girushana)

---

## System overview

Four agents form one pipeline. A freelancer's claimed skills and raw portfolio
material go in; a fairness-adjusted, ranked list of job matches comes out.

```
                    ┌──────────────────────────┐
  candidate input → │  Agent A: Portfolio       │
  (claimed skills,  │  Evidence (NLP + LLM)     │
   projects, certs) └──────────────┬────────────┘
                                    │ structured evidence
                                    ▼
                     ┌──────────────────────────┐
                     │  Agent B: Skill           │
                     │  Verification             │
                     └──────────────┬────────────┘
                                    │ evidence-supported skills
                                    ▼
                     ┌──────────────────────────┐
                     │  Agent C: Job             │
                     │  Compatibility (IR/FAISS) │
                     └──────────────┬────────────┘
                                    │ compatibility-scored job matches
                                    ▼
                     ┌──────────────────────────┐
                     │  Agent D: Fair Ranking    │
                     │  + Integration + Security │
                     │  + UI                     │
                     └──────────────┬────────────┘
                                    │
                                    ▼
                     fairness-adjusted ranked jobs
```

Agents talk to each other over plain HTTP/JSON (the agent communication
protocol used throughout this system). Agent D exposes the single entry
point end users interact with — everything else runs behind it.

| Agent | Folder | Default port |
|---|---|---|
| A — Portfolio Evidence | `agents/portfolio_evidence_agent` | 8000 |
| B — Skill Verification | `agents/skill_verification_agent` | 8001 |
| C — Job Compatibility | `agents/job_compatibility_agent` | 8002 |
| D — Fair Ranking (entry point) | `agents/fair-ranking-agent` | 8003 |

## Running the whole system

The simplest way — one command brings up all four agents, wired together:

```bash
docker-compose up -d --build
```

First build is slow (Agent A pulls a spaCy model + a local HF model; Agent C
pulls a sentence-transformers model on first request) — this needs internet
access and a few GB of disk. Subsequent builds are cached and much faster.

Check everything is up:

```bash
docker-compose ps
curl http://localhost:8000/health   # Agent A
curl http://localhost:8001/health   # Agent B
curl http://localhost:8002/health   # Agent C
curl http://localhost:8003/health   # Agent D
```

Then open the UI: **http://localhost:8003/demo**

Register a user, log in, fill in a candidate's claimed skills and portfolio
projects, and click "Evaluate candidate" — this calls Agent D's
`POST /api/full-pipeline`, which calls A → B → C in sequence and returns the
fairness-adjusted ranking.

### Running agents individually (no Docker)

Each agent folder has its own README with its own `pip install` / `uvicorn`
instructions, for working on one agent in isolation. See:
`agents/portfolio_evidence_agent/README` section below, and the READMEs
inside `agents/skill_verification_agent/` and `agents/fair-ranking-agent/`.

## Testing

Each agent has its own unit/API test suite (mocked, no Docker needed):

```bash
cd agents/portfolio_evidence_agent && pytest -v
cd agents/skill_verification_agent && pytest -v
cd agents/job_compatibility_agent && pytest -v
cd agents/fair-ranking-agent && pytest -v
```

The **end-to-end test** exercises all four agents together over real HTTP —
this is the "does the whole system actually work" check:

```bash
docker-compose up -d --build
# wait for all services to report healthy (docker-compose ps)
pytest tests/e2e -v
```

If the services aren't running, `tests/e2e` skips (rather than fails) so the
rest of the suite still runs cleanly without Docker.

## Environment variables (Agent D)

| Variable | Default | Purpose |
|---|---|---|
| `JWT_SECRET_KEY` | dev fallback (insecure) | Signs JWTs — set a real secret for any real deployment |
| `ENCRYPTION_KEY` | auto-generated | Fernet key for the encrypted user store |
| `PORTFOLIO_EVIDENCE_URL` | `http://localhost:8000` | Agent A's service |
| `SKILL_VERIFICATION_URL` | `http://localhost:8001` | Agent B's service |
| `JOB_COMPATIBILITY_URL` | `http://localhost:8002` | Agent C's service |

`docker-compose.yml` sets the three URL variables to the container network
hostnames automatically — you only need to set these by hand when running
agents individually outside Docker.

---

# Portfolio Evidence Agent

## Overview

The Portfolio Evidence Agent extracts structured skill evidence from freelancer portfolio materials.

It combines:

- Rule-based NLP skill extraction using spaCy PhraseMatcher
- Local LLM-based contextual skill interpretation using Hugging Face models
- Evidence reconciliation for confidence scoring
- FastAPI REST interface for system integration

---

## Features

### 1. NLP Skill Extraction

The agent identifies explicitly mentioned skills from:

- Portfolio projects
- Certificates
- Code samples
- Work descriptions

Example:

Input: Built a backend application using Django and PostgreSQL.
Output: Django
        PostgreSQL


---

### 2. LLM Contextual Interpretation

The local LLM identifies strongly implied skills.

Example:

Input: Built server-side APIs with Django.
Possible inferred skills: Django
                          REST API
                          Python


The system validates LLM evidence before accepting it.

---

### 3. Evidence Reconciliation

The reconciler combines NLP and LLM results.

Example:
NLP:
Django

LLM:
Django

Result:
Django
method: both
confidence: 0.98


---

# Installation

## Create virtual environment

```bash
python -m venv venv

Activate:

Windows: 
venv\Scripts\activate

Install dependencies
pip install -r requirements.txt

Running Tests

Run:

pytest

Expected:

13 passed

Running the API

Start FastAPI:

uvicorn api.main:app --reload --port 8001

Server:

http://127.0.0.1:8001

Swagger documentation:

http://127.0.0.1:8001/docs

API Endpoints
Health Check
GET
/health

Response:

{
  "status": "ok",
  "agent": "portfolio_evidence_agent",
  "version": "1.0.0"
}
Extract Evidence
POST
/extract-evidence

Example request:

{
  "freelancer_id": "fl_001",
  "portfolio_projects": [
    {
      "project_id": "proj_001",
      "title": "Booking Platform",
      "description": "Built server-side APIs with Django."
    }
  ],
  "certificates": [],
  "code_samples": [],
  "work_descriptions": []
}
Example Response
{
  "freelancer_id": "fl_001",
  "agent": "portfolio_evidence_agent",
  "agent_version": "1.0.0",
  "evidence_items": [
    {
      "skill": "Django",
      "skill_category": "web_framework",
      "extraction_method": "both",
      "confidence": 0.98
    }
  ]
}
Project Structure
portfolio_evidence_agent/

├── agent/
│   ├── nlp_extractor.py
│   ├── llm_interpreter.py
│   ├── reconciler.py
│   └── portfolio_evidence_agent.py
│
├── api/
│   └── main.py
│
├── tests/
│   ├── test_agent.py
│   └── test_api.py
│
├── data/
│   └── skill_taxonomy.json
│
└── requirements.txt
Notes
The LLM layer uses a local Hugging Face model.
No external API key is required.
LLM outputs are validated against original portfolio evidence.
If the LLM is unavailable, NLP extraction continues working.

```

# Skill Verification Agent

## Overview

The Skill Verification Agent verifies freelancer skills against portfolio evidence provided by the Portfolio Evidence Agent.

It determines whether a claimed skill is:

- Exact match
- Implied match
- Weak/related match
- Unsupported
- Contradicted

## Features

### 1. Skill Verification

Compares claimed freelancer skills with available portfolio evidence.

### 2. Evidence Matching

Supports exact and contextual/implied skill matching.

Example:

Portfolio evidence:
"Built server-side APIs using Django."

Claimed skills:
- Django
- Python
- REST API

The agent can identify Django as directly supported and Python/REST API as implied where the evidence supports those relationships.

### 3. Portfolio Evidence Adapter

The adapter converts the Portfolio Evidence Agent's output into the format required by the Skill Verification Agent.

```text
Portfolio Evidence Agent
        ↓
Portfolio Evidence Adapter
        ↓
Skill Verification Agent
        ↓
Verification Results
