from agent.portfolio_evidence_agent import PortfolioEvidenceAgent


agent = PortfolioEvidenceAgent(
    use_llm=True
)

profile = {
    "freelancer_id": "fl_real_test",

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

output = agent.process(profile)

print("\nFINAL EVIDENCE")
print("==============")

for item in output["evidence_items"]:
    print(item)