# Job Compatibility Agent

## Overview

The Job Compatibility Agent is the **Member C component** of the Agentic AI-Based Fair Opportunity and Capability Verification System for New Freelancers.

Its purpose is to match freelancers with suitable jobs based on their **evidence-supported capabilities**, rather than platform history, ratings, popularity, or previous client information.

The agent receives verified skills from the Skill Verification Agent (Member B), retrieves semantically relevant jobs, applies structured capability and experience filtering, and calculates a hybrid job compatibility score.

---

## Role in the System

The Job Compatibility Agent operates after the Skill Verification Agent.

```text
Portfolio Evidence Agent (Member A)
              |
              v
Skill Verification Agent (Member B)
              |
              | verified skills
              v
      Job Compatibility Agent
              |
       +------+------+
       |             |
       v             v
 Semantic        Structured
 Retrieval       Filtering
       |             |
       v             v
      +------+------+
             |
             v
      Hybrid Scoring
             |
             v
       Matched Jobs
```

Member C does not process raw portfolio text. It uses the verified capability information supplied by Member B.

---

## Main Features

* Sentence Transformer embeddings for semantic job retrieval
* FAISS vector index for efficient similarity search
* Evidence-supported capability matching
* Structured filtering using:

  * verified skills
  * minimum experience
  * skill-category compatibility
* Hybrid compatibility scoring
* Matched and missing skill identification
* Explainable compatibility results
* FastAPI service
* Synthetic job dataset
* Automated unit and API tests

---

## Input

The agent accepts verified skills produced by the Skill Verification Agent.

Each verified skill contains:

```json
{
  "skill": "Python",
  "status": "supported",
  "confidence": 0.97,
  "evidence_ids": ["E001"],
  "reason": "Supported by project evidence"
}
```

Only skills with the following statuses are considered usable:

* `supported`
* `weakly_supported`

Skills marked as `unsupported` or `contradicted` are excluded from capability matching.

The candidate input also contains:

```json
{
  "candidate_id": "F001",
  "experience_years": 0,
  "verified_skills": []
}
```

---

## Information Retrieval Methodology

### 1. Job Representation

Each job is represented using:

* job title
* job description
* required skills
* preferred skills
* skill categories

These fields are combined into a textual representation before generating an embedding.

Example:

```text
Junior Data Analyst
Analyze datasets and generate business insights.
Required skills: Python, SQL, Excel
Preferred skills: Pandas
Categories: data_analysis, business_intelligence
```

### 2. Semantic Embeddings

The agent uses the Sentence Transformer model:

```text
all-MiniLM-L6-v2
```

Candidate capabilities and job representations are converted into vector embeddings.

The embeddings are normalized so that inner-product similarity can be used as cosine similarity.

### 3. FAISS Retrieval

FAISS is used as the vector index.

The implementation uses:

```text
IndexFlatIP
```

The candidate capability representation is compared against the indexed job vectors and the most semantically relevant jobs are retrieved.

The initial retrieval stage obtains the top 10 candidates before structured filtering.

---

## Hybrid Retrieval

Pure keyword matching can miss jobs when different terms describe related capabilities.

For example, a candidate may have experience with:

```text
Python, Pandas, SQL
```

while a job description may describe:

```text
data analysis using Python-based tools
```

Semantic retrieval can identify this relationship even when the exact wording differs.

However, semantic similarity alone does not guarantee that the candidate has the required capabilities.

Therefore, Member C combines semantic retrieval with structured evidence-based matching.

```text
Semantic Similarity
        +
Structured Capability Matching
        +
Experience / Category Filtering
        |
        v
Hybrid Compatibility Score
```

---

## Structured Filtering

The structured stage checks three factors.

### Evidence-supported skills

Only skills verified by Member B as `supported` or `weakly_supported` are usable.

### Experience

A job is retained only when:

```text
candidate experience >= job minimum experience
```

### Skill Categories

Verified skills are mapped to capability categories.

For example:

```text
Python -> programming, data_analysis, machine_learning,
          backend, data_engineering

SQL -> database, data_analysis, data_engineering,
       business_intelligence

Pandas -> data_analysis, data_science
```

The candidate's derived categories are compared with the categories specified by the job.

A job must have compatible capability categories when category information is available.

The job must also have at least one overlapping evidence-supported required or preferred skill.

---

## Hybrid Compatibility Score

The final compatibility score combines semantic similarity and structured capability matching.

```text
Compatibility Score =
    0.60 × Semantic Score
  + 0.40 × Structured Score
```

Therefore:

```text
60% Semantic Similarity
40% Evidence-supported Structured Matching
```

The weighting is a design choice for the prototype.

### Structured Score

The structured score considers required and preferred skills separately.

Required skills receive greater importance:

```text
Required skill score = average verified confidence
Preferred skill score = average verified confidence

Structured Score =
    0.75 × Required Skill Score
  + 0.25 × Preferred Skill Score
```

Missing required skills receive a score of `0` and are reported in the result.

---

## Example

For a candidate with:

```text
Python   - supported - 0.97
Pandas   - supported - 0.95
SQL      - supported - 0.90
Java     - unsupported - 0.05
```

the agent can use:

```text
Python
Pandas
SQL
```

but does not use Java as an evidence-supported capability.

An example returned job contains:

```json
{
  "job_id": "JOB015",
  "title": "Analytics Intern",
  "compatibility_score": 0.5233,
  "semantic_score": 0.4756,
  "structured_score": 0.595,
  "matched_skills": [
    "Pandas",
    "Python",
    "SQL"
  ],
  "missing_skills": [
    "Data Analysis"
  ]
}
```

---

## Output

The `/match-jobs` endpoint returns:

```json
{
  "candidate_id": "F001",
  "matched_jobs": [
    {
      "job_id": "JOB015",
      "title": "Analytics Intern",
      "compatibility_score": 0.5233,
      "semantic_score": 0.4756,
      "structured_score": 0.595,
      "matched_skills": [
        "Pandas",
        "Python",
        "SQL"
      ],
      "missing_skills": [
        "Data Analysis"
      ],
      "explanation": "Semantic similarity: 0.48. Evidence-supported structured score: 0.59. Matched skills: Pandas, Python, SQL. Missing required skills: Data Analysis."
    }
  ]
}
```

The explanation allows downstream components to understand why a job was matched.

---

## Job Dataset

The prototype contains a synthetic dataset of **15 jobs**.

The dataset includes jobs such as:

* Junior Data Analyst
* Machine Learning Intern
* Junior Python Developer
* Data Engineer Intern
* Business Intelligence Analyst
* Junior Data Scientist
* NLP Research Intern
* AI Engineer Intern
* SQL Developer Intern
* Power BI Developer
* Backend Developer Intern
* Data Visualization Intern
* Machine Learning Engineer
* ETL Developer Intern
* Analytics Intern

Each job contains capability-related information:

```text
job_id
title
description
required_skills
preferred_skills
skill_categories
minimum_experience_years
```

No platform-history, rating, popularity, previous-client, or fairness-ranking fields are used by Member C.

---

## API

### Health Check

```http
GET /health
```

Example response:

```json
{
  "status": "healthy",
  "agent": "job_compatibility_agent",
  "version": "1.0.0"
}
```

### Match Jobs

```http
POST /match-jobs
```

Example request:

```json
{
  "candidate_id": "F001",
  "experience_years": 0,
  "verified_skills": [
    {
      "skill": "Python",
      "status": "supported",
      "confidence": 0.97,
      "evidence_ids": ["E001"],
      "reason": "Supported by project evidence"
    },
    {
      "skill": "Pandas",
      "status": "supported",
      "confidence": 0.95,
      "evidence_ids": ["E001"],
      "reason": "Supported by project evidence"
    },
    {
      "skill": "SQL",
      "status": "supported",
      "confidence": 0.90,
      "evidence_ids": ["E002"],
      "reason": "Supported by project evidence"
    }
  ]
}
```

---

## Project Structure

```text
job_compatibility_agent/
├── README.md
├── requirements.txt
├── app/
│   ├── __init__.py
│   ├── agent.py
│   ├── embeddings.py
│   ├── filters.py
│   ├── main.py
│   ├── matcher.py
│   ├── retriever.py
│   └── schemas.py
├── data/
│   └── jobs.json
└── tests/
    ├── __init__.py
    ├── test_api.py
    ├── test_matcher.py
    └── test_retriever.py
```

---

## Running the Agent

From the repository root:

```powershell
python -m uvicorn agents.job_compatibility_agent.app.main:app --reload --port 8003
```

The API will be available at:

```text
http://127.0.0.1:8003
```

Swagger API documentation:

```text
http://127.0.0.1:8003/docs
```

---

## Testing

Run the Member C test suite with:

```powershell
python -m pytest agents/job_compatibility_agent/tests -v
```

Current validation:

```text
4 passed
```

The tests cover:

* health endpoint
* job matching API
* hybrid score calculation
* structured skill matching
* FAISS job retrieval

---

## Scope of Member C

Member C is responsible for:

* Job Compatibility Agent
* Information retrieval
* FAISS vector search
* Sentence Transformer embeddings
* Hybrid retrieval
* Capability-based matching
* Experience filtering
* Skill-category filtering
* Job dataset
* Compatibility scoring
* Match explanations
* API and tests

---

## Design Principle

The central design principle of this agent is:

> **Match opportunities based on verified capabilities and job requirements, rather than platform history or popularity.**

This allows the compatibility stage to focus on what the freelancer can demonstrate through verified evidence and how those capabilities relate to the requirements of available jobs.
