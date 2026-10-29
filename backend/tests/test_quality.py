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
