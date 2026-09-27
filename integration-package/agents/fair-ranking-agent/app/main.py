"""
FastAPI application for Member D: Fair Ranking Agent + Integration + Security + UI.

Endpoints:
  POST /auth/register              create a user
  POST /auth/login                 get a JWT access token
  POST /api/rank                   [protected, rate-limited] fair-rank
                                    already-computed matched_jobs from Member C
  POST /api/orchestrate            [protected, rate-limited] full pipeline:
                                    calls Member B + Member C live, then
                                    fair-ranks the result
  GET  /demo                       basic UI for this agent
  GET  /health                     health check
"""

from pathlib import Path

from fastapi import Depends, FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, FileResponse
from pydantic import ValidationError

from app.schemas import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    ErrorResponse,
    FairRankingRequest,
    FairRankingResponse,
    OrchestrateRequest,
    FullPipelineRequest,
)
from app.auth import create_access_token, get_current_user
from app.users_store import create_user, verify_user, user_exists
from app.rate_limit import rate_limit
from app.ranking_agent import FairRankingAgent
from app.integration import (
    call_portfolio_evidence,
    call_skill_verification,
    call_job_compatibility,
    UpstreamServiceError,
)
from app.schemas import FairRankingRequest as _FRR  # for orchestrate reuse

app = FastAPI(
    title="Fair Ranking Agent (Member D)",
    description=(
        "Fairness-adjusted job ranking, integration with Members B & C, "
        "JWT auth, rate limiting, and encryption-at-rest for user data."
    ),
    version="1.0.0",
)

ranking_agent = FairRankingAgent()
_STATIC_DIR = Path(__file__).resolve().parent / "static"


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "fair-ranking-agent"}


@app.get("/demo", include_in_schema=False)
def demo_ui():
    return FileResponse(_STATIC_DIR / "demo.html")


# ---------------- Auth ----------------

@app.post(
    "/auth/register",
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse}},
)
def register(payload: RegisterRequest):
    if user_exists(payload.username):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorResponse(
                error="user_exists", detail=f"User '{payload.username}' already exists."
            ).model_dump(),
        )
    try:
        create_user(payload.username, payload.password)
    except ValueError as exc:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorResponse(error="invalid_request", detail=str(exc)).model_dump(),
        )
    return {"status": "created", "username": payload.username}


@app.post(
    "/auth/login",
    response_model=TokenResponse,
    responses={401: {"model": ErrorResponse}},
)
def login(payload: LoginRequest):
    if not verify_user(payload.username, payload.password):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=ErrorResponse(
                error="invalid_credentials", detail="Incorrect username or password."
            ).model_dump(),
        )
    from app.auth import ACCESS_TOKEN_EXPIRE_MINUTES

    token = create_access_token(payload.username)
    return TokenResponse(access_token=token, expires_in_minutes=ACCESS_TOKEN_EXPIRE_MINUTES)


# ---------------- Fair ranking ----------------

@app.post(
    "/api/rank",
    response_model=FairRankingResponse,
    responses={401: {"model": ErrorResponse}, 429: {"model": ErrorResponse}},
)
def rank_jobs(
    payload: FairRankingRequest,
    request: Request,
    username: str = Depends(get_current_user),
    _rl: None = Depends(rate_limit),
):
    """
    Re-ranks Member C's matched_jobs using the fairness multiplier derived
    from claimed_skills vs. Member B's verified_skills. Requires a valid JWT.
    """
    request.state.username = username
    return ranking_agent.rank(payload)


@app.post(
    "/api/orchestrate",
    response_model=FairRankingResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
    },
)
def orchestrate(
    payload: OrchestrateRequest,
    request: Request,
    username: str = Depends(get_current_user),
    _rl: None = Depends(rate_limit),
):
    """
    Full pipeline: calls Member B's live service to verify claimed skills
    against Member A's portfolio evidence, then Member C's live service to
    get job matches, then applies fair ranking -- all behind one
    authenticated, rate-limited call.
    """
    request.state.username = username

    try:
        candidate_id, verified_skills = call_skill_verification(
            payload.claimed_skills, payload.portfolio_evidence
        )
    except UpstreamServiceError as exc:
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content=ErrorResponse(error="upstream_error", detail=str(exc)).model_dump(),
        )

    final_candidate_id = payload.candidate_id or candidate_id
    if not final_candidate_id:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorResponse(
                error="invalid_request",
                detail="candidate_id was not provided and Member B did not return one.",
            ).model_dump(),
        )

    try:
        matched_jobs = call_job_compatibility(
            final_candidate_id, verified_skills, payload.experience_years
        )
    except UpstreamServiceError as exc:
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content=ErrorResponse(error="upstream_error", detail=str(exc)).model_dump(),
        )

    fair_request = _FRR(
        candidate_id=final_candidate_id,
        claimed_skills=payload.claimed_skills,
        verified_skills=verified_skills,
        matched_jobs=matched_jobs,
    )
    return ranking_agent.rank(fair_request)


@app.post(
    "/api/full-pipeline",
    response_model=FairRankingResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
    },
)
def full_pipeline(
    payload: FullPipelineRequest,
    request: Request,
    username: str = Depends(get_current_user),
    _rl: None = Depends(rate_limit),
):
    """
    The single entry point for the system's UI: walks the ENTIRE pipeline in
    one authenticated, rate-limited call --

        Agent A (portfolio evidence) -> Agent B (skill verification)
        -> Agent C (job compatibility) -> Agent D (fair ranking)

    Takes raw candidate input (claimed skills + portfolio projects /
    certificates / code samples / work descriptions, in Member A's own
    request shape) and returns the final fairness-adjusted job ranking.
    """
    request.state.username = username

    profile = {
        "freelancer_id": payload.candidate_id,
        "portfolio_projects": [p.model_dump() for p in payload.portfolio_projects],
        "certificates": [c.model_dump() for c in payload.certificates],
        "code_samples": [s.model_dump() for s in payload.code_samples],
        "work_descriptions": [w.model_dump() for w in payload.work_descriptions],
    }

    try:
        portfolio_evidence = call_portfolio_evidence(profile)
    except UpstreamServiceError as exc:
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content=ErrorResponse(error="upstream_error", detail=str(exc)).model_dump(),
        )

    try:
        candidate_id, verified_skills = call_skill_verification(
            payload.claimed_skills, portfolio_evidence
        )
    except UpstreamServiceError as exc:
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content=ErrorResponse(error="upstream_error", detail=str(exc)).model_dump(),
        )

    final_candidate_id = candidate_id or payload.candidate_id

    try:
        matched_jobs = call_job_compatibility(
            final_candidate_id, verified_skills, payload.experience_years
        )
    except UpstreamServiceError as exc:
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content=ErrorResponse(error="upstream_error", detail=str(exc)).model_dump(),
        )

    fair_request = _FRR(
        candidate_id=final_candidate_id,
        claimed_skills=payload.claimed_skills,
        verified_skills=verified_skills,
        matched_jobs=matched_jobs,
    )
    return ranking_agent.rank(fair_request)


# ---------------- Error handlers ----------------

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(error="validation_error", detail=str(exc.errors())).model_dump(),
    )


@app.exception_handler(ValidationError)
async def pydantic_validation_handler(request: Request, exc: ValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(error="validation_error", detail=str(exc)).model_dump(),
    )
