from app.evidence import evidence_issues

DOCS=[
    ("integrations-002","Native Salesforce integration is not currently supported."),
    ("faq-002","Sales representatives can schedule reminders for leads."),
    ("product_overview-002","FlowDesk helps teams organize leads and track pipelines."),
]

def test_salesforce_positive_claim_rejected():
    assert "unsupported_salesforce_sync" in evidence_issues(
        "Can you sync with Salesforce?",
        "FlowDesk can synchronize leads with Salesforce.", DOCS)

def test_salesforce_limit_accepted():
    assert not evidence_issues(
        "Can you sync with Salesforce?",
        "We don't support native Salesforce integration. Which data would you need to move?",
        DOCS)

def test_churn_prediction_hallucination_rejected():
    assert "unsupported_churn_prediction" in evidence_issues(
        "Can you predict churn?",
        "FlowDesk documents AI-powered lead prioritization and churn prediction.",
        DOCS)

def test_competitive_pricing_rejected():
    assert "unverified_marketing_claim" in evidence_issues(
        "Is your CRM expensive?", "FlowDesk offers flexible plans and competitive pricing.",
        DOCS)

def test_documented_followup_reminders_accepted():
    assert not evidence_issues(
        "Can it remind our representatives?",
        "Yes, FlowDesk provides follow-up reminders for leads. How do you track them today?",
        DOCS)

def test_generic_discovery_question_accepted():
    assert not evidence_issues(
        "We have teams in different cities.",
        "How are your teams currently coordinating lead follow-ups?",
        DOCS)

def test_lead_scoring_not_inferred_from_reminders():
    assert "unsupported_lead_scoring" in evidence_issues(
        "How do you prioritize leads?",
        "FlowDesk can automatically prioritize leads for your sales team.",
        DOCS)
