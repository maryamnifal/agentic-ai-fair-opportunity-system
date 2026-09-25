# agentic-ai-fair-opportunity-system
Agentic AI-Based Fair Opportunity and Capability Verification System for New Freelancers

# Agentic AI-Based Fair Opportunity and Capability Verification System

## Portfolio Evidence Agent
(Member A Maryam)

## Skill Verification Agent
(Member B Pirushalini)

## Job Compatibility Agent
(Member C Thushanya)

## Fair Ranking Agent
(Member D Girushana)

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
