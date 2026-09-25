import json

from agent.nlp_extractor import NLPExtractor
from agent.reconciler import Reconciler
from agent.portfolio_evidence_agent import PortfolioEvidenceAgent
from fastapi.testclient import TestClient
from api import main as api_main


def test_skill_extraction():
    extractor = NLPExtractor(
        "data/skill_taxonomy.json"
    )

    text = """
    I developed a backend application using Django,
    PostgreSQL and REST API technologies.
    """

    results = extractor.extract(
        text,
        "portfolio_project",
        "proj_001"
    )

    skills = [
        item["skill"]
        for item in results
    ]

    assert "Django" in skills
    assert "PostgreSQL" in skills
    assert "REST API" in skills


def load_taxonomy():
    with open(
        "data/skill_taxonomy.json",
        "r",
        encoding="utf-8"
    ) as file:
        return json.load(file)


def test_reconciler_alias_normalisation():
    taxonomy = load_taxonomy()

    reconciler = Reconciler(taxonomy)

    ner_items = [
        {
            "skill": "postgres",
            "skill_category": "database",
            "source_type": "portfolio_project",
            "source_ref": "proj_001",
            "source_excerpt": "Used postgres for database storage.",
            "extraction_method": "ner",
            "confidence": 0.95,
            "reasoning": "Explicit mention of postgres."
        }
    ]

    items, unmapped = reconciler.merge(
        ner_items,
        []
    )

    assert len(items) == 1
    assert items[0]["skill"] == "PostgreSQL"
    assert items[0]["skill_category"] == "database"
    assert unmapped == []


def test_reconciler_duplicate_removal():
    taxonomy = load_taxonomy()

    reconciler = Reconciler(taxonomy)

    ner_items = [
        {
            "skill": "Django",
            "skill_category": "web_framework",
            "source_type": "portfolio_project",
            "source_ref": "proj_001",
            "source_excerpt": "Built the backend using Django.",
            "extraction_method": "ner",
            "confidence": 0.90,
            "reasoning": "Explicit mention of Django."
        },
        {
            "skill": "django",
            "skill_category": "web_framework",
            "source_type": "portfolio_project",
            "source_ref": "proj_001",
            "source_excerpt": "Django was used for the backend.",
            "extraction_method": "ner",
            "confidence": 0.95,
            "reasoning": "Explicit mention of Django."
        }
    ]

    items, unmapped = reconciler.merge(
        ner_items,
        []
    )

    assert len(items) == 1
    assert items[0]["skill"] == "Django"
    assert items[0]["confidence"] == 0.95
    assert unmapped == []


def test_reconciler_both_methods():
    taxonomy = load_taxonomy()

    reconciler = Reconciler(taxonomy)

    ner_items = [
        {
            "skill": "Django",
            "skill_category": "web_framework",
            "source_type": "portfolio_project",
            "source_ref": "proj_001",
            "source_excerpt": "Built the backend using Django.",
            "extraction_method": "ner",
            "confidence": 0.95,
            "reasoning": "Explicit mention of Django."
        }
    ]

    llm_items = [
        {
            "skill": "Django",
            "skill_category": "uncategorised",
            "source_type": "portfolio_project",
            "source_ref": "proj_001",
            "source_excerpt": "Built the backend using Django.",
            "extraction_method": "llm",
            "confidence": 0.85,
            "reasoning": "Django identified by LLM interpretation."
        }
    ]

    items, unmapped = reconciler.merge(
        ner_items,
        llm_items
    )

    assert len(items) == 1
    assert items[0]["skill"] == "Django"
    assert items[0]["extraction_method"] == "both"
    assert items[0]["confidence"] == 0.98
    assert unmapped == []

def test_end_to_end_without_llm():

    agent = PortfolioEvidenceAgent(
        use_llm=False
    )

    profile = {
        "freelancer_id": "fl_001",

        "portfolio_projects": [
            {
                "project_id": "proj_001",
                "title": "Restaurant Booking Platform",
                "description":
                    "Built a backend application using Django, "
                    "PostgreSQL and REST API technologies."
            }
        ],

        "certificates": [
            {
                "certificate_id": "cert_001",
                "title": "Python Development Certificate",
                "description":
                    "Completed training in Python and Flask."
            }
        ],

        "code_samples": [
            {
                "sample_id": "code_001",
                "filename": "app.py",
                "language": "Python",
                "snippet":
                    "Created a Flask API using PostgreSQL."
            }
        ],

        "work_descriptions": [
            {
                "work_id": "work_001",
                "description":
                    "Developed React applications and used Git "
                    "for version control."
            }
        ]
    }

    output = agent.process(profile)

    assert output["freelancer_id"] == "fl_001"

    assert output["agent"] == "portfolio_evidence_agent"

    assert output["agent_version"] == "1.0.0"

    assert "evidence_items" in output

    skills = {
        item["skill"]
        for item in output["evidence_items"]
    }

    assert "Django" in skills
    assert "PostgreSQL" in skills
    assert "REST API" in skills
    assert "Python" in skills
    assert "Flask" in skills
    assert "React" in skills
    assert "Git" in skills

    for item in output["evidence_items"]:
        assert item["evidence_id"].startswith("ev_")
        assert item["extraction_method"] == "ner"

def test_end_to_end_with_mock_llm():

    class FakeLLM:

        def interpret(
            self,
            text,
            source_type,
            source_ref,
            known_skills
        ):
            return [
                {
                    "skill": "Django",
                    "skill_category": "uncategorised",
                    "source_type": source_type,
                    "source_ref": source_ref,
                    "source_excerpt": "Django",
                    "extraction_method": "llm",
                    "confidence": 0.85,
                    "reasoning": "Django identified by contextual interpretation."
                },
                {
                    "skill": "Python",
                    "skill_category": "uncategorised",
                    "source_type": source_type,
                    "source_ref": source_ref,
                    "source_excerpt": "Django",
                    "extraction_method": "llm",
                    "confidence": 0.75,
                    "reasoning": "Django implies Python usage."
                },
                {
                    "skill": "REST API",
                    "skill_category": "uncategorised",
                    "source_type": source_type,
                    "source_ref": source_ref,
                    "source_excerpt": "server-side APIs",
                    "extraction_method": "llm",
                    "confidence": 0.75,
                    "reasoning": "Server-side APIs indicate REST API development."
                }
            ]


    agent = PortfolioEvidenceAgent(
        use_llm=False
    )

    # Replace real LLM with our fake LLM
    agent.llm = FakeLLM()
    agent.use_llm = True


    profile = {
        "freelancer_id": "fl_llm_test",

        "portfolio_projects": [
            {
                "project_id": "proj_llm_001",
                "title": "Booking Platform",
                "description":
                    "Built server-side APIs with Django."
            }
        ],

        "certificates": [],
        "code_samples": [],
        "work_descriptions": []
    }


    output = agent.process(profile)


    evidence = {
        item["skill"]: item
        for item in output["evidence_items"]
    }


    assert "Django" in evidence
    assert "Python" in evidence
    assert "REST API" in evidence


    # Django was detected by NLP + LLM
    assert (
        evidence["Django"]["extraction_method"]
        == "both"
    )


    # Python came only from the LLM
    assert (
        evidence["Python"]["extraction_method"]
        == "llm"
    )


    # REST API came only from the LLM
    assert (
        evidence["REST API"]["extraction_method"]
        == "llm"
    )

    # Use NLP-only agent during automated API tests.
# This keeps tests fast and avoids loading the local LLM.
api_main.agent = PortfolioEvidenceAgent(
    use_llm=False
)

client = TestClient(
    api_main.app
)


def test_health_endpoint():

    response = client.get(
        "/health"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"

    assert (
        data["agent"]
        == "portfolio_evidence_agent"
    )

    assert data["version"] == "1.0.0"


def test_extract_evidence_endpoint():

    payload = {
        "freelancer_id": "api_test_001",

        "portfolio_projects": [
            {
                "project_id": "proj_001",
                "title": "Backend Project",
                "description":
                    "Built a REST API using Django "
                    "and PostgreSQL."
            }
        ],

        "certificates": [],
        "code_samples": [],
        "work_descriptions": []
    }

    response = client.post(
        "/extract-evidence",
        json=payload
    )

    assert response.status_code == 200

    data = response.json()

    assert (
        data["freelancer_id"]
        == "api_test_001"
    )

    skills = {
        item["skill"]
        for item in data["evidence_items"]
    }

    assert "Django" in skills
    assert "REST API" in skills
    assert "PostgreSQL" in skills

def test_sparse_profile():
    agent = PortfolioEvidenceAgent(
        use_llm=False
    )

    profile = {
        "freelancer_id": "sparse_001",

        "portfolio_projects": [
            {
                "project_id": "proj_sparse",
                "title": "Website",
                "description": "Made a website."
            }
        ],

        "certificates": [],
        "code_samples": [],
        "work_descriptions": []
    }

    output = agent.process(profile)

    assert output["freelancer_id"] == "sparse_001"

    assert "processing_notes" in output

    assert any(
        "very short" in note.lower()
        for note in output["processing_notes"]
    )
       
def test_empty_profile():
    agent = PortfolioEvidenceAgent(
        use_llm=False
    )

    profile = {
        "freelancer_id": "empty_001",
        "portfolio_projects": [],
        "certificates": [],
        "code_samples": [],
        "work_descriptions": []
    }

    output = agent.process(profile)

    assert output["freelancer_id"] == "empty_001"

    assert output["evidence_items"] == []

    assert "processing_notes" in output

    assert any(
        "no extractable skill evidence" in note.lower()
        for note in output["processing_notes"]
    )

def test_unmapped_skill():
    agent = PortfolioEvidenceAgent(
        use_llm=False
    )

    profile = {
        "freelancer_id": "unmapped_001",

        "portfolio_projects": [
            {
                "project_id": "proj_unmapped",
                "title": "Frontend Project",
                "description":
                    "Used Svelte for frontend development."
            }
        ],

        "certificates": [],
        "code_samples": [],
        "work_descriptions": []
    }

    output = agent.process(profile)

    assert output["freelancer_id"] == "unmapped_001"

    # Svelte is not currently in our taxonomy,
    # so it should not become evidence.
    skills = {
        item["skill"]
        for item in output["evidence_items"]
    }

    assert "Svelte" not in skills

    # It should instead be reported as an unmapped term.
    assert any(
        "svelte" in term.lower()
        for term in output["unmapped_terms"]
    )

def test_graceful_llm_unavailable():

    class UnavailableLLM:
        def interpret(
            self,
            text,
            source_type,
            source_ref,
            known_skills
        ):
            # Simulate unavailable / failed LLM
            return []

    agent = PortfolioEvidenceAgent(
        use_llm=False
    )

    # Enable the LLM path but replace it with
    # an unavailable mock implementation.
    agent.llm = UnavailableLLM()
    agent.use_llm = True

    profile = {
        "freelancer_id": "fallback_001",

        "portfolio_projects": [
            {
                "project_id": "proj_fallback",
                "title": "Backend Project",
                "description":
                    "Built a REST API using Django and PostgreSQL."
            }
        ],

        "certificates": [],
        "code_samples": [],
        "work_descriptions": []
    }

    output = agent.process(profile)

    assert output["freelancer_id"] == "fallback_001"

    skills = {
        item["skill"]
        for item in output["evidence_items"]
    }

    # NLP should still work even though LLM returned nothing
    assert "Django" in skills
    assert "REST API" in skills
    assert "PostgreSQL" in skills

    # Since only NLP produced evidence,
    # extraction method should remain "ner".
    for item in output["evidence_items"]:
        assert item["extraction_method"] == "ner"

def test_llm_hallucinated_excerpt_rejected():

    class FakeHallucinatingLLM:

        def interpret(
            self,
            text,
            source_type,
            source_ref,
            known_skills
        ):

            return [
                {
                    "skill": "JavaScript",
                    "skill_category": "language",
                    "source_type": source_type,
                    "source_ref": source_ref,
                    "source_excerpt":
                        "Created a React dashboard",
                    "extraction_method": "llm",
                    "confidence": 0.90,
                    "reasoning":
                        "React requires JavaScript."
                }
            ]


    agent = PortfolioEvidenceAgent(
        use_llm=False
    )

    agent.llm = FakeHallucinatingLLM()
    agent.use_llm = True


    profile = {
        "freelancer_id": "hallucination_001",

        "portfolio_projects": [
            {
                "project_id": "proj_hallucination",
                "title": "Backend API",
                "description":
                    "Built server-side APIs with Django."
            }
        ],

        "certificates": [],
        "code_samples": [],
        "work_descriptions": []
    }


    output = agent.process(profile)


    skills = {
        item["skill"]
        for item in output["evidence_items"]
    }


    # Hallucinated LLM evidence should be rejected
    assert "JavaScript" not in skills