from app.pipeline import finalize

DOCS=[
    ("faq-002","FlowDesk helps teams organize leads and schedule follow-up reminders."),
    ("integrations-002","A native Salesforce integration is not currently supported."),
    ("pricing-001","FlowDesk has published plan prices; no discounts are promised."),
]
def raw(s, intent="feature_inquiry"):
    return dict(intent=intent,suggestion=s,reason="Respond to the customer's question.",next_action="Clarify needs.",source_ids=["faq-002"])

def test_salesforce_recovery_is_topic_specific():
    rec, origin, _=finalize(raw("FlowDesk supports Salesforce integration.","integration_question"),"Can you synchronize with Salesforce?",DOCS)
    assert origin=="verified_recovery" and "does not currently support" in rec["suggestion"]
    assert rec["intent"]=="integration_question"

def test_churn_recovery_not_reminder_repetition():
    rec, origin, _=finalize(raw("FlowDesk offers follow-up reminders."),"Can you predict who will cancel subscriptions?",DOCS)
    assert origin=="verified_recovery" and "churn prediction" in rec["suggestion"]
    assert "reminders" not in rec["suggestion"]

def test_pricing_recovery_remains_pricing():
    rec,origin,_=finalize(raw("FlowDesk offers competitive pricing with flexible plans.","pricing_objection"),"This CRM is expensive. Why should we switch?",DOCS)
    assert origin=="verified_recovery" and rec["intent"]=="pricing_objection"
    assert "pricing concern" in rec["suggestion"]

def test_reminder_answer_stays_model_generated():
    rec,origin,_=finalize(raw("Yes, FlowDesk supports follow-up reminders for leads. How does your team track them?"),"Can you remind us about follow-ups?",DOCS)
    assert origin=="ai_generated" and "follow-up reminders" in rec["suggestion"]

def test_question_echo_recovers_to_usable_answer():
    rec,origin,_=finalize(raw("Can FlowDesk remind representatives about follow-ups?"),"Can FlowDesk remind representatives about follow-ups?",DOCS)
    assert origin=="verified_recovery" and rec["suggestion"].startswith("Yes, FlowDesk")

def test_competitor_marketing_claim_is_not_delivered():
    rec,origin,_=finalize(raw("FlowDesk offers seamless integrations and streamlined workflows.","competitor_objection"),"We have another CRM. Why switch?",DOCS)
    assert origin=="verified_recovery" and "seamless" not in rec["suggestion"]

def test_wrong_intent_is_corrected_without_canned_generic_text():
    rec,origin,_=finalize(raw("What works well with your current CRM?","competitor_objection"),"Our CRM seems expensive. Why switch?",DOCS)
    assert origin=="verified_recovery" and rec["intent"]=="pricing_objection"
