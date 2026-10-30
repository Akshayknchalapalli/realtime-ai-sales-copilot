import asyncio
from app import understanding

class FakeResponse:
    def raise_for_status(self): pass
    def json(self):
        return {"message":{"content":'{"situation":"15 reps","need":"tracking","discovery_focus":"unfinished'}}
class FakeClient:
    def __init__(self,**kwargs): pass
    async def __aenter__(self): return self
    async def __aexit__(self,*args): pass
    async def post(self,*args,**kwargs): return FakeResponse()

def test_truncated_briefing_keeps_customer_question(monkeypatch):
    monkeypatch.setattr(understanding.httpx,"AsyncClient",FakeClient)
    latest="We have 15 sales reps and 500 leads daily in Excel."
    result=asyncio.run(understanding.understand(latest,latest))
    assert result["situation"]==latest
    assert result["need"]=="Unknown"
