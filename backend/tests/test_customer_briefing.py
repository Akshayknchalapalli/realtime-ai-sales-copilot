"""Regression for the reported 15 SDR / 500 leads / Excel conversation.
This tests orchestration, not actual model accuracy.
"""
import asyncio
from app import main

CUSTOMER=("We have 15 sales representatives and receive around 500 leads "
          "every day from our website and marketing campaigns. "
          "We currently manage everything in Excel.")

def test_latest_customer_briefing_reaches_generation(monkeypatch):
    seen={}
    async def fake_understand(latest, context):
        seen["latest"]=latest
        return {"situation":"15 sales reps handle 500 leads per day in Excel",
                "need":"lead management at scale",
                "discovery_focus":"ask what problems the manual workflow causes"}
    async def fake_generate(context, sources, schema, latest_customer="", understanding=None):
        seen["briefing"]=understanding
        seen["model_latest"]=latest_customer
        return {"intent":"feature_inquiry",
                "suggestion":"Handling 500 leads daily with Excel is a lot to coordinate. Which part of the process is hardest for your team?",
                "reason":"The buyer described lead volume and manual tracking.",
                "next_action":"Ask which manual step is taking the most time.",
                "source_ids":["faq-002"]}
    monkeypatch.setattr(main,"PROVIDER","ollama")
    monkeypatch.setenv("OLLAMA_TWO_STAGE","1")
    monkeypatch.setattr(main,"understand",fake_understand)
    monkeypatch.setattr(main.ollama_backend,"recommendation",fake_generate)
    turns=[main.Turn(event_id="1",speaker="sdr",text="How do you manage leads?"),
           main.Turn(event_id="2",speaker="customer",text=CUSTOMER)]
    result=asyncio.run(main.generate(turns,[("faq-002","Lead reminders are supported.")]))
    assert seen["latest"]==CUSTOMER
    assert seen["model_latest"]==CUSTOMER
    assert "500 leads" in seen["briefing"]["situation"]
    assert result.next_action.startswith("Ask")
    assert result.suggestion.startswith("Handling 500 leads")

def test_other_speaker_turn_is_not_latest_customer(monkeypatch):
    async def fake_understand(latest, context):
        assert latest==CUSTOMER
        return {"situation":CUSTOMER,"need":"unknown","discovery_focus":"ask"}
    async def fake_generate(context,sources,schema,latest_customer="",understanding=None):
        assert latest_customer==CUSTOMER
        return {"intent":"clarification","suggestion":"How do you currently organize those leads?",
                "reason":"Need to clarify the workflow.","next_action":"Ask about lead organization.","source_ids":[]}
    monkeypatch.setattr(main,"PROVIDER","ollama")
    monkeypatch.setattr(main,"understand",fake_understand)
    monkeypatch.setattr(main.ollama_backend,"recommendation",fake_generate)
    turns=[main.Turn(event_id="1",speaker="customer",text=CUSTOMER),
           main.Turn(event_id="2",speaker="sdr",text="What challenges do you face?")]
    result=asyncio.run(main.generate(turns,[]))
    assert result.intent=="clarification"
