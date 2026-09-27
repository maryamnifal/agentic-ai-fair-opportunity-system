# FairRank AI

AI-powered fair opportunity evaluation for new freelancers.

FairRank AI evaluates a candidate's claimed skills and portfolio material through four cooperating FastAPI agents. The system extracts evidence, verifies claims, matches suitable jobs, and applies an explainable fairness adjustment to the final ranking.

## System Architecture

```text
Candidate profile
      |
      v
Agent A: Portfolio Evidence ---> structured skill evidence
      |
      v
Agent B: Skill Verification ---> supported/weak/unsupported claims
      |
      v
Agent C: Job Compatibility ----> compatibility-scored jobs
      |
      v
Agent D: Fair Ranking ----------> fairness-adjusted ranked jobs
                                  + authentication, integration, and UI
```

Agents communicate over HTTP and JSON. Agent D is the public entry point; the other agents are internal services in the Docker Compose network.

| Agent | Responsibility | Service port | Source |
| --- | --- | ---: | --- |
| A - Portfolio Evidence | Extracts structured skills and evidence from portfolio material | 8000 | `agents/portfolio_evidence_agent` |
| B - Skill Verification | Compares claimed skills with extracted evidence | 8001 | `agents/skill_verification_agent` |
| C - Job Compatibility | Matches verified skills and experience to available roles | 8002 | `agents/job_compatibility_agent` |
| D - Fair Ranking | Integrates A, B, and C; authenticates users and fair-ranks jobs | 8003 | `agents/fair-ranking-agent` |

## The Four Agents

### Agent A: Portfolio Evidence

Agent A receives portfolio projects, certificates, code samples, and work descriptions. It uses spaCy taxonomy matching to identify explicit skills, captures source excerpts, records confidence and reasoning, and returns a structured evidence document.

The production Compose configuration uses deterministic NLP extraction with the local Qwen inference path disabled. This keeps the pipeline responsive while preserving valid explicit evidence extraction. The optional LLM interpreter can identify strongly implied skills, but it is not required for the API response.

Endpoints:

```text
GET  /health
POST /extract-evidence
```

### Agent B: Skill Verification

Agent B evaluates the candidate's claimed skills against Agent A's evidence. It classifies claims as supported, weakly supported, unsupported, or contradicted and provides the verification data used by the fairness step.

Endpoints:

```text
GET  /health
POST /api/verify-skills-from-portfolio
```

### Agent C: Job Compatibility

Agent C compares verified skills and experience against the job catalogue. It returns matched jobs, compatibility scores, matched skills, missing skills, and explanations.

Endpoints:

```text
GET  /health
POST /match-jobs
```

### Agent D: Fair Ranking

Agent D is the public application boundary. It owns:

- JWT authentication and authorization
- User registration and login
- Rate limiting
- Pipeline integration with Agents A, B, and C
- Fairness scoring and final ranking
- The FairRank AI web interface

The fairness step keeps the original compatibility score visible and applies an explainable multiplier based on evidence support. Strongly evidence-backed claims can be boosted; unsupported or contradicted overclaiming can be penalized.

Public endpoints:

```text
GET  /demo
GET  /health
POST /auth/register
POST /auth/login
POST /api/full-pipeline
POST /api/rank
POST /api/orchestrate
```

## Run With Docker Compose

From the repository root:

```bash
docker compose up -d --build
docker compose ps
```

Health checks:

```bash
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
```

Open the application at `http://localhost:8003/demo`.

Sign in, enter a candidate profile, and select **Evaluate candidate**. Agent D then runs the complete A -> B -> C -> D flow through one authenticated request.

## Authentication Contract

Registration accepts JSON:

```bash
curl -X POST http://localhost:8003/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"password123"}'
```

Login uses OAuth2 password form encoding, not JSON:

```bash
curl -X POST http://localhost:8003/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "username=alice" \
  --data-urlencode "password=password123"
```

The response contains a bearer token valid for the configured token lifetime:

```json
{
  "access_token": "...",
  "token_type": "bearer",
  "expires_in_minutes": 60
}
```

Use the token for protected endpoints:

```bash
curl -X POST http://localhost:8003/api/full-pipeline \
  -H "Authorization: Bearer <access-token>" \
  -H "Content-Type: application/json" \
  -d @candidate.json
```

## Configuration

Docker Compose supplies the internal service URLs to Agent D:

| Variable | Compose value | Purpose |
| --- | --- | --- |
| `PORTFOLIO_EVIDENCE_URL` | `http://portfolio-evidence-agent:8000` | Agent A service |
| `SKILL_VERIFICATION_URL` | `http://skill-verification-agent:8000` | Agent B service |
| `JOB_COMPATIBILITY_URL` | `http://job-compatibility-agent:8000` | Agent C service |
| `UPSTREAM_TIMEOUT_SECONDS` | `120` | Agent D upstream request timeout |
| `JWT_SECRET_KEY` | development value | JWT signing secret; replace in production |

When running services outside Docker, use the host port values from the agent table instead of the Compose service names.

## Testing

Run each agent's local tests:

```bash
cd agents/portfolio_evidence_agent && pytest -v
cd agents/skill_verification_agent && pytest -v
cd agents/job_compatibility_agent && pytest -v
cd agents/fair-ranking-agent && pytest -v
```

With Docker Compose running, run the end-to-end tests:

```bash
pytest tests/e2e -v
```

## Repository Layout

```text
agents/
  portfolio_evidence_agent/   Agent A
  skill_verification_agent/   Agent B
  job_compatibility_agent/    Agent C
  fair-ranking-agent/         Agent D and public UI
docker-compose.yml             Service wiring
tests/                         End-to-end tests
```
