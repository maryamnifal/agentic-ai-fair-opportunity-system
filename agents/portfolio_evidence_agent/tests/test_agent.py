import json

from agent.nlp_extractor import NLPExtractor
from agent.reconciler import Reconciler
from agent.portfolio_evidence_agent import PortfolioEvidenceAgent

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