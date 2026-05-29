from extractors.project_extractor import analyze_project_text


SAMPLE_TEXT = """
Project Name: Finance Transformation PMO

Background:
Manual reporting delays executive decisions.

Scope:
- Implement a consolidated project reporting process

Objectives:
- Reduce weekly status preparation effort
- Improve steering committee visibility

Deliverables:
- Integrated project plan
- RAID log

Milestones:
- Sponsor approval on 2026-06-15
- Pilot launch on 2026-07-01

Tasks:
- Prepare project charter | Owner: PMO Lead
- Build reporting dashboard requires finance data feed
- Validate pilot after approval from sponsor

Risks:
- Finance data feed delay could impact pilot launch

Assumptions:
- Business owners are available for weekly review

Dependencies:
- Pending finance data feed from ERP team

Stakeholders:
- Executive Sponsor: CFO
- Delivery Lead: PMO Lead

Acceptance Criteria:
- Weekly status package approved by steering committee
"""


def test_project_structure_extraction() -> None:
    analysis = analyze_project_text("file-1", SAMPLE_TEXT)

    assert analysis["project_title"] == "Finance Transformation PMO"
    assert "Reduce weekly status preparation effort" in analysis["objectives"]
    assert analysis["tasks"][0]["owner"] == "PMO Lead"
    assert analysis["dependencies"][0]["escalation_required"] is True
    assert analysis["risks"][0]["impact"] == "High"
    assert "2026-06-15" in analysis["dates"]
    assert analysis["stakeholders"][0]["role"] == "Executive Sponsor"
