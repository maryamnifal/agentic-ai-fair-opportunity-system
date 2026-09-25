from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from agent.portfolio_evidence_agent import PortfolioEvidenceAgent


# --------------------------------------------------
# FastAPI application
# --------------------------------------------------

app = FastAPI(
    title="Portfolio Evidence Agent",
    version="1.0.0",
    description=(
        "Extracts structured skill evidence from freelancer "
        "portfolio material using NLP and a local LLM."
    )
)


# --------------------------------------------------
# Portfolio Evidence Agent
# --------------------------------------------------

agent = PortfolioEvidenceAgent(
    use_llm=True
)


# --------------------------------------------------
# Request models
# --------------------------------------------------

class PortfolioProject(BaseModel):
    project_id: str
    title: str = ""
    description: str = ""
    url: Optional[str] = None
    role: Optional[str] = None


class Certificate(BaseModel):
    certificate_id: str
    title: str = ""
    issuer: Optional[str] = None
    issue_date: Optional[str] = None
    description: str = ""


class CodeSample(BaseModel):
    sample_id: str
    filename: Optional[str] = None
    language: Optional[str] = None
    snippet: str = ""


class WorkDescription(BaseModel):
    work_id: str
    description: str = ""


class ProfileRequest(BaseModel):
    freelancer_id: str

    portfolio_projects: List[PortfolioProject] = Field(
        default_factory=list
    )

    certificates: List[Certificate] = Field(
        default_factory=list
    )

    code_samples: List[CodeSample] = Field(
        default_factory=list
    )

    work_descriptions: List[WorkDescription] = Field(
        default_factory=list
    )


# --------------------------------------------------
# Health endpoint
# --------------------------------------------------

@app.get("/health")
def health():
    return {
        "status": "ok",
        "agent": "portfolio_evidence_agent",
        "version": agent.VERSION
    }


# --------------------------------------------------
# Evidence extraction endpoint
# --------------------------------------------------

@app.post("/extract-evidence")
def extract_evidence(profile: ProfileRequest):

    try:

        return agent.process(
            profile.model_dump()
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=f"Extraction failed: {error}"
        )