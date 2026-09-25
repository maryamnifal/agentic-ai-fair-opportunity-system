"""
FastAPI application exposing the Skill Verification Agent.

Endpoint: POST /api/verify-skills

Integration note for Member D: this app only implements input validation,
sanitization, and the core verification logic. It deliberately does NOT
implement JWT auth, rate limiting, or encryption -- those are Member D's
responsibility and can be added as middleware/dependencies around this
router without touching the verification logic itself.
"""

from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, FileResponse
from pydantic import ValidationError

from app.schemas import (
    VerifyRequest,
    VerifyResponse,
    ErrorResponse,
    PortfolioEvidenceVerifyRequest,
)
from app.validation import validate_and_sanitize
from app.agent import SkillVerificationAgent
from app.adapters.portfolio_evidence_adapter import (
    adapt_portfolio_evidence,
    adapt_candidate_id,
)

app = FastAPI(
    title="Skill Verification Agent (Member B)",
    description=(
        "Determines whether a freelancer's claimed skills are supported by "
        "their portfolio evidence. Does not verify identity or credentials."
    ),
    version="1.0.0",
)

agent = SkillVerificationAgent()


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "skill-verification-agent"}


_STATIC_DIR = Path(__file__).resolve().parent / "static"


@app.get("/demo", include_in_schema=False)
def demo_ui():
    """
    Demo page for THIS agent only (not the group project's final UI --
    that belongs to Member D). Lets you exercise POST /api/verify-skills
    from a browser instead of curl/Swagger.
    """
    return FileResponse(_STATIC_DIR / "demo.html")


@app.post(
    "/api/verify-skills",
    response_model=VerifyResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid business input"},
        422: {"model": ErrorResponse, "description": "Malformed/invalid request body"},
    },
)
def verify_skills(payload: VerifyRequest):
    """
    Accepts claimed skills + portfolio evidence, returns per-skill
    evidence-supported verdicts with confidence scores and reasons.
    FastAPI + Pydantic already reject malformed JSON / wrong types / missing
    fields with a 422 before this function body runs.
    """
    sanitized_request, business_errors = validate_and_sanitize(payload)
    if business_errors:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorResponse(
                error="invalid_request",
                detail="; ".join(business_errors),
            ).model_dump(),
        )

    result = agent.verify(sanitized_request)
    return result


@app.post(
    "/api/verify-skills-from-portfolio",
    response_model=VerifyResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid business input"},
        422: {"model": ErrorResponse, "description": "Malformed/invalid request body"},
    },
)
def verify_skills_from_portfolio(payload: PortfolioEvidenceVerifyRequest):
    """
    Integration endpoint: accepts Member A's raw Portfolio Evidence Agent
    output directly (the dict her POST /extract-evidence returns) instead of
    requiring the caller to pre-convert it into EvidenceItem objects.

    Internally this adapts her schema into ours via
    app/adapters/portfolio_evidence_adapter.py, then runs the exact same
    verification logic as /api/verify-skills.
    """
    candidate_id = payload.candidate_id or adapt_candidate_id(payload.portfolio_evidence)
    if not candidate_id or not candidate_id.strip():
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorResponse(
                error="invalid_request",
                detail=(
                    "candidate_id was not provided and could not be found in "
                    "portfolio_evidence.freelancer_id."
                ),
            ).model_dump(),
        )

    try:
        evidence = adapt_portfolio_evidence(payload.portfolio_evidence)
    except Exception as exc:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorResponse(
                error="invalid_request",
                detail=f"Could not interpret portfolio_evidence: {exc}",
            ).model_dump(),
        )

    request = VerifyRequest(
        candidate_id=candidate_id,
        claimed_skills=payload.claimed_skills,
        evidence=evidence,
    )

    sanitized_request, business_errors = validate_and_sanitize(request)
    if business_errors:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorResponse(
                error="invalid_request",
                detail="; ".join(business_errors),
            ).model_dump(),
        )

    result = agent.verify(sanitized_request)
    return result


# ---- Centralized error handlers so failure responses are consistent JSON ----

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            error="validation_error",
            detail=str(exc.errors()),
        ).model_dump(),
    )


@app.exception_handler(ValidationError)
async def pydantic_validation_handler(request: Request, exc: ValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(error="validation_error", detail=str(exc)).model_dump(),
    )
