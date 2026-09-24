from agent.nlp_extractor import NLPExtractor


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