import asyncio
from app import main

def test_default_single_stage_skips_extra_understanding_call(monkeypatch):
    monkeypatch.setattr(main,"PROVIDER","ollama")
    monkeypatch.delenv("OLLAMA_TWO_STAGE",raising=False)
    async def forbidden(*args,**kwargs):
        raise AssertionError("Unnecessary extra model call")
    recorded={}
    async def fake_recommendation(context,sources,schema,latest_customer="",understanding=None):
        recorded["latest"]=latest_customer
        recorded["understanding"]=understanding
        return {"intent":"buying_signal","suggestion":"What time next Tuesday works for the demo?",
                "reason":"The buyer requested a demo.","next_action":"Confirm the preferred time.","source_ids":[]}
    monkeypatch.setattr(main,"understand",forbidden)
    monkeypatch.setattr(main.ollama_backend,"recommendation",fake_recommendation)
    latest="I'd like a demo next Tuesday, what time can we schedule?"
    turns=[main.Turn(event_id="1",speaker="customer",text="Your CRM seems expensive"),
           main.Turn(event_id="2",speaker="customer",text=latest)]
    rec=asyncio.run(main.generate(turns,[]))
    assert recorded["understanding"] is None
    assert recorded["latest"]==latest
    assert rec.intent=="buying_signal"
