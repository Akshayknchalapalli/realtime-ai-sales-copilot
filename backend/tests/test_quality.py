import os
os.environ["AI_PROVIDER"] = "offline"
from app.main import Recommendation, Turn, enforce_claims, retrieval_query

def test_latest_customer_focus():
    turns=[
      Turn(event_id="1",speaker="customer",text="I need pricing"),
      Turn(event_id="2",speaker="sdr",text="What else?"),
      Turn(event_id="3",speaker="customer",text="Does it connect with Salesforce?"),
    ]
    q=retrieval_query(turns)
    assert "Salesforce" in q
    assert "pricing" not in q

def test_unsupported_free_demo_removed():
    rec=Recommendation(intent="pricing_objection", suggestion="Try our free demo without extra cost.",
                       reason="Sales concern",next_action="Show demo",source_ids=["pricing-002"])
    fixed=enforce_claims(rec,[("pricing-002","Starter plan costs INR 1,999/month")])
    assert "free demo" not in fixed.suggestion.lower()
    assert "without extra cost" not in fixed.suggestion.lower()

def test_unsupported_salesforce_removed():
    rec=Recommendation(intent="integration_question",
                       suggestion="We support Salesforce integration.",
                       reason="Integration",next_action="Integrate",source_ids=["integrations-002"])
    fixed=enforce_claims(rec,[("integrations-002","Native Salesforce integration not supported")])
    assert "don't currently support" in fixed.suggestion.lower()

def test_ordinary_recommendation_preserved():
    rec=Recommendation(intent="clarification",suggestion="How many leads do you handle?",
                       reason="Discovery",next_action="Qualify",source_ids=[])
    assert enforce_claims(rec,[]) == rec

def test_15_person_team_plan_not_assumed():
    turns=[Turn(event_id="x",speaker="customer",text="We have 15 sales reps. Your product is expensive.")]
    rec=Recommendation(intent="pricing_objection",
                       suggestion="The Starter plan is the right fit for your team.",
                       reason="Plan",next_action="Buy",source_ids=["pricing-002"])
    result=enforce_claims(rec,[("pricing-002","Starter for a small team")],turns)
    assert "starter plan is the right fit" not in result.suggestion.lower()

def test_buying_signal_supersedes_salesforce():
    from app.main import validate_latest_intent
    old=Recommendation(intent="clarification",suggestion="We don't integrate with Salesforce.",
        reason="old context",next_action="Sync",source_ids=[])
    result=validate_latest_intent(old,"Can we schedule a demonstration next week?",[])
    assert result.intent == "buying_signal"
    assert "salesforce" not in result.suggestion.lower()

def test_competitor_supersedes_integration():
    from app.main import validate_latest_intent
    old=Recommendation(intent="clarification",suggestion="Check Salesforce integration.",
        reason="old context",next_action="Sync",source_ids=[])
    result=validate_latest_intent(old,"We're already using another CRM. Why should we switch to FlowDesk?",[])
    assert result.intent == "competitor_objection"
    assert "salesforce" not in result.suggestion.lower()
