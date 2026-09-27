# Fair Ranking Agent (Member D)

Part of *Agentic AI-Based Fair Opportunity and Capability Verification System for New Freelancers* (IT 3041).

## What this owns

Per the brief, Member D owns: **Fair Ranking Agent**, **Integration**, **JWT authentication/authorization**,
**Rate limiting**, **Encryption**, and **Basic UI**.

## Why a Fair Ranking Agent, given Member C already scores compatibility?

Member C's Job Compatibility Agent (`agents/job_compatibility_agent`) already **excludes**
unsupported/contradicted skills from its `compatibility_score` — so extra unproven claims
don't directly help a candidate. But it also doesn't **penalize** them: a candidate who
claims 8 skills (2 supported) and one who honestly claims 2 skills (2 supported) currently
get an identical score for the skills that do match.

The brief's fairness principle goes further than "ignore unsupported claims" — it says the
system should *"prioritize capability supported by evidence rather than the quantity of
claims."* This agent makes that an explicit, visible, and separately-auditable adjustment:

- Candidates whose claims are mostly evidence-backed get a **fairness multiplier > 1** (boosted)
- Candidates who overclaim (many unsupported/contradicted claims relative to what they
  claimed) get a **fairness multiplier < 1** (penalized)
- Both `compatibility_score` (Member C's original) and `fair_score` (after adjustment) are
  returned, so the effect is transparent, not hidden

Demonstrated case (see `tests/test_fairness.py::test_two_candidates_same_raw_score_different_fair_score`):
two candidates with the **identical** `compatibility_score` of 0.8 end up with `fair_score`
0.96 (honest, all claims supported) vs 0.695 (claimed 6 skills, only 2 supported) —
same raw match quality, different final rank.

## Architecture

```
Member B (verified_skills)          Member C (matched_jobs)
        │                                    │
        └──────────────┬─────────────────────┘
                        ▼
              POST /api/rank  (or /api/orchestrate, which calls B & C live)
                        │
              fairness.py: compute_fairness()
                        │
              ranking_agent.py: FairRankingAgent.rank()
                        │
                        ▼
              Fairness-adjusted, re-ranked job list
```

Both endpoints require a valid JWT (`auth.py`) and are rate-limited (`rate_limit.py`).
User credentials are bcrypt-hashed and the store is encrypted at rest (`users_store.py`,
`encryption.py`).

## Folder structure

```
app/
  schemas.py          Pydantic models (VerifiedSkill/MatchedJob mirror B & C's real schemas)
  fairness.py           the fairness scoring rules (explainable, rule-based)
  ranking_agent.py        FairRankingAgent orchestrator
  integration.py            calls Member B's and Member C's live HTTP services
  auth.py                     JWT creation/verification
  users_store.py                bcrypt-hashed, Fernet-encrypted-at-rest user store
  encryption.py                   Fernet encrypt/decrypt helpers
  rate_limit.py                     in-memory fixed-window rate limiter
  main.py                             FastAPI app wiring everything together
  static/demo.html                      basic UI: login + orchestrate + fairness display
tests/
  test_fairness.py     unit tests for the scoring rules
  test_ranking_agent.py  unit tests for re-ranking behavior
  test_auth.py             register/login/protected-endpoint tests
  test_rate_limit.py         429 behavior
  test_api.py                  full API tests incl. mocked orchestrate pipeline
```

## Running it

```bash
pip install -r requirements.txt --break-system-packages   # or use a venv
uvicorn app.main:app --reload --port 8003
```

- API docs: `http://localhost:8003/docs`
- Basic UI: `http://localhost:8003/demo`
- Health check: `GET /health`

### Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `JWT_SECRET_KEY` | dev fallback (insecure) | Signs/verifies JWTs. **Set a real secret in production.** |
| `ENCRYPTION_KEY` | auto-generated, persisted to `data/.encryption_key` | Fernet key for the encrypted user store |
| `SKILL_VERIFICATION_URL` | `http://localhost:8001` | Member B's service, for `/api/orchestrate` |
| `JOB_COMPATIBILITY_URL` | `http://localhost:8002` | Member C's service, for `/api/orchestrate` |

## Two endpoints, two use cases

| Endpoint | When to use |
|---|---|
| `POST /api/rank` | You already have Member B's `verified_skills` and Member C's `matched_jobs` (e.g. hand-built test data, or calling B/C yourself) |
| `POST /api/orchestrate` | You only have `claimed_skills` + Member A's raw portfolio evidence — Member D calls Member B then Member C live, then fair-ranks the result. This is Member D's "Integration" responsibility. |

To use `/api/orchestrate` for real (not the mocked tests), Member B's and Member C's services
need to actually be running on the URLs above — this repo's own test suite mocks them out so
tests don't require three live servers.

## Auth flow

```bash
curl -X POST http://localhost:8003/auth/register -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"password123"}'

curl -X POST http://localhost:8003/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "username=alice" \
  --data-urlencode "password=password123"
# -> {"access_token": "...", "token_type": "bearer", "expires_in_minutes": 60}

curl -X POST http://localhost:8003/api/rank -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" -d '{ ... }'
```

## Testing

```bash
pytest -v
```

24 tests: fairness scoring (boost/penalty/clamping), re-ranking behavior, auth
(register/login/token validation), rate limiting (429 after the window), and the API
(including `/api/orchestrate` with mocked Member B/C responses).

## Security notes (for the viva)

- **JWT**: HS256-signed tokens with a 60-minute expiry. Signature verification means any
  tampering with the token payload (e.g. changing the username) invalidates it.
- **Password hashing**: bcrypt via `passlib`, one-way and salted — Member D can never
  recover a user's actual password, even from the stored hash.
- **Encryption at rest**: the user store file (`data/users.enc`) is encrypted with Fernet
  (AES-128-CBC + HMAC-SHA256) before it touches disk — a different concern from password
  hashing (hashing protects the password itself; encryption protects the *file* holding
  the hashes, so even a copied file isn't human-readable).
- **Rate limiting**: in-memory fixed-window counter (10 requests / 60s per user), returns
  `429` with `Retry-After`. Not distributed — fine for a single-process university project;
  a production system would use Redis or similar across multiple app instances.

## What this deliberately does NOT do

- Does not re-implement Member B's input validation/sanitization or Member C's
  embeddings/FAISS retrieval — those stay in their own services.
- Does not claim to verify identity or credentials — fairness is computed purely from
  Member B's evidence-based verification, not from any external check.
