# agentic-ai-fair-opportunity-system
Agentic AI-Based Fair Opportunity and Capability Verification System for New Freelancers

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

