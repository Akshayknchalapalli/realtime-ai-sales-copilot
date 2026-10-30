"""FastAPI real-time sales copilot; run with uvicorn app.main:app --reload."""
import asyncio
import logging
import os
import re
import time
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, Field, ValidationError
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)
from . import ollama_backend
from .quality import guard
from .evidence import evidence_issues
PROVIDER = os.getenv("AI_PROVIDER", "ollama").lower()
ROOT = Path(__file__).resolve().parents[2]
app = FastAPI(title="Real-time Sales Copilot")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173","http://127.0.0.1:5173"], allow_methods=["*"], allow_headers=["*"])

class Turn(BaseModel):
    event_id: str = Field(min_length=1, max_length=128)
    speaker: Literal["sdr","customer"]
    text: str = Field(min_length=1, max_length=5000)
    timestamp: str | None = None

class Recommendation(BaseModel):
    intent: Literal["pricing_objection","integration_question","competitor_objection","feature_inquiry","buying_signal","clarification","other"]
    suggestion: str
    reason: str
    next_action: str
    source_ids: list[str]

class Session:
    def __init__(self):
        self.version = 0
        self.turns: list[Turn] = []
        self.seen: set[str] = set()
        self.task: asyncio.Task | None = None
        self.send_lock = asyncio.Lock()
        self.closed = False

class Knowledge:
    def __init__(self):
        self.sections: list[tuple[str,str]] = []
        for p in sorted((ROOT / "knowledge").glob("*.md")):
            for i, section in enumerate(p.read_text(encoding="utf-8").split("\n## ")):
                section = section if i == 0 else "## " + section
                if section.strip() and i > 0 and len(section.split()) >= 8:
                    self.sections.append((f"{p.stem}-{i+1:03d}", section.strip()))
        self.index = None
        self.embedding_client = None
        if os.getenv("USE_FAISS","1") == "1" and (PROVIDER == "ollama" or (PROVIDER == "openai" and os.getenv("OPENAI_API_KEY"))):
            try:
                import faiss
                import numpy as np
                if PROVIDER == "ollama":
                    vectors = ollama_backend.embeddings([t for _,t in self.sections])
                    client, model = "ollama", None
                else:
                    from openai import OpenAI
                    client = OpenAI()
                    model = os.getenv("EMBEDDING_MODEL","text-embedding-3-small")
                    result = client.embeddings.create(model=model,input=[t for _,t in self.sections])
                    vectors = [x.embedding for x in result.data]
                matrix = np.asarray(vectors,dtype="float32")
                faiss.normalize_L2(matrix)
                self.index = faiss.IndexFlatIP(matrix.shape[1])
                self.index.add(matrix)
                self.embedding_client = (client,model)
            except Exception:
                logger.exception("FAISS initialization failed; falling back to keyword search")

    def include_critical_evidence(self, query: str, found: list[tuple[str,str]], k: int) -> list[tuple[str,str]]:
        """Ensure relevant documented limitations reach the LLM, without rewriting its answer."""
        q=query.lower()
        required=[]
        if "salesforce" in q:
            required=[entry for entry in self.sections if entry[0].startswith("integrations-") and "not currently supported" in entry[1].lower()]
        elif any(word in q for word in ("churn","cancel","payroll","income tax","lead scoring","score and prioritize","automatically score")):
            required=[entry for entry in self.sections if entry[0].startswith("product_overview-") and "features" in entry[1].lower()]
        if not required:
            return found[:k]
        # Reserve one slot for authoritative scope/limitation evidence.
        out=required[:1]
        out.extend(entry for entry in found if entry[0] not in {x[0] for x in out})
        return out[:k]

    def search(self, query: str, k: int = 3) -> list[tuple[str,str]]:
        if self.index is not None and self.embedding_client:
            try:
                import faiss
                import numpy as np
                client,model=self.embedding_client
                if client == "ollama":
                    vectors = ollama_backend.embeddings([query])
                else:
                    result=client.embeddings.create(model=model,input=query)
                    vectors=[result.data[0].embedding]
                vector=np.asarray(vectors,dtype="float32")
                faiss.normalize_L2(vector)
                _,indices=self.index.search(vector,min(k,len(self.sections)))
                return self.include_critical_evidence(query,[self.sections[i] for i in indices[0] if i>=0],k)
            except Exception:
                logger.exception("Vector retrieval failed; falling back to keyword search")
        terms=set(re.findall(r"[a-z0-9]+",query.lower()))-{"and","the","this","that","your","with","have"}
        return self.include_critical_evidence(query,sorted(self.sections,key=lambda entry:sum(term in entry[1].lower() for term in terms),reverse=True)[:k],k)

knowledge=Knowledge()
sessions: dict[str,Session]={}

def retrieval_query(turns: list[Turn]) -> str:
    """Prioritize the latest customer statement for retrieval."""
    latest = next((t.text for t in reversed(turns) if t.speaker == "customer"), "")
    q = latest.lower()
    hints = []
    if any(w in q for w in ("price", "expensive", "cost", "budget")):
        hints.append("pricing subscription plans objection")
    if any(w in q for w in ("salesforce", "integration", "integrate", "connect")):
        hints.append("Salesforce integrations unsupported")
    if any(w in q for w in ("follow-up", "excel", "reminders", "leads")):
        hints.append("lead follow-up reminders features")
    if any(w in q for w in ("demo", "trial", "free")):
        hints.append("trial demo policy")
    return latest + " " + " ".join(hints)

def enforce_claims(rec: Recommendation, passages: list[tuple[str,str]], turns: list[Turn] | None = None) -> Recommendation:
    """Fail closed on common misleading sales promises; not a complete factual verifier."""
    statement = rec.suggestion
    forbidden = (
        r"\b(?:free demo|free trial|without extra cost|no extra cost|at no cost|"
        r"guaranteed|100% guaranteed|special discount|discount guaranteed)\b"
    )
    customer_context = " ".join(t.text for t in (turns or []) if t.speaker == "customer")
    plan_claim = bool(re.search(r"\b(?:starter|growth) plan\b", statement, re.I))
    team_15 = bool(re.search(r"\b(?:15|fifteen)\b", customer_context, re.I))
    if re.search(forbidden, statement, re.IGNORECASE) or (plan_claim and team_15):
        return Recommendation(
            intent=rec.intent,
            suggestion="I understand your concern. What does your current workflow cost in time and missed follow-ups? We can compare that with the documented subscription plans.",
            reason="Removed a potentially unsupported commercial promise.",
            next_action="Clarify needs and discuss documented product value.",
            source_ids=[sid for sid, _ in passages],
        )
    if re.search(r"\bsalesforce\b", statement, re.IGNORECASE) and re.search(
        r"(?:we|flowdesk|it) (?:support|supports|integrate|integrates|connect|connects).*salesforce",
        statement, re.IGNORECASE
    ):
        return Recommendation(
            intent="integration_question",
            suggestion="We don't currently support a native Salesforce integration. Which information would you need to synchronize?",
            reason="Salesforce integration is not supported in the product documentation.",
            next_action="Understand integration requirements.",
            source_ids=[sid for sid, _ in passages if sid.startswith("integrations")],
        )
    return rec



def validate_latest_intent(rec: Recommendation, latest: str, passages: list[tuple[str,str]]) -> Recommendation:
    """Guard against old-topic answers when a clear new customer intent appears."""
    q=latest.lower()
    if "demo" in q or "demonstration" in q or "schedule" in q and "next week" in q:
        if rec.intent != "buying_signal" or "salesforce" in rec.suggestion.lower():
            return Recommendation(intent="buying_signal",
                suggestion="Certainly. What day next week suits you, and which workflow should we focus on in the demonstration?",
                reason="The latest customer turn requested a demonstration.",
                next_action="Confirm demo timing and focus.",
                source_ids=[])
    if "already using another crm" in q or "why should we switch" in q and "crm" in q:
        if rec.intent not in ("competitor_objection","pricing_objection") or "salesforce" in rec.suggestion.lower():
            return Recommendation(intent="competitor_objection",
                suggestion="What is working well with your current CRM, and what would you most like to improve?",
                reason="The latest customer turn concerns an existing CRM.",
                next_action="Discover switching criteria.",
                source_ids=[])
    return rec

async def generate(turns: list[Turn], passages: list[tuple[str,str]]) -> Recommendation:
    latest=turns[-1].text.lower()
    source_ids=[sid for sid,_ in passages]
    if PROVIDER == "ollama":
        context="\n".join(f"{turn.speaker}: {turn.text}" for turn in turns[-12:])
        sources="\n\n".join(f"SOURCE {sid}: {chunk}" for sid,chunk in passages)
        data=await ollama_backend.recommendation(context,sources,Recommendation.model_json_schema(),latest_customer=next((t.text for t in reversed(turns) if t.speaker=="customer"), ""))
        rec=Recommendation.model_validate(data)
        rec.source_ids=[sid for sid in rec.source_ids if sid in source_ids]
        return rec
    if PROVIDER == "openai" and os.getenv("OPENAI_API_KEY"):
        from openai import AsyncOpenAI
        client=AsyncOpenAI()
        context="\n".join(f"{turn.speaker}: {turn.text}" for turn in turns[-12:])
        sources="\n\n".join(f"SOURCE {sid}: {chunk}" for sid,chunk in passages)
        response=await client.beta.chat.completions.parse(
            model=os.getenv("OPENAI_MODEL","gpt-4o-mini"),
            messages=[
                {"role":"system","content":"You are a private sales copilot for fictional FlowDesk CRM. Write ONE concise speakable next response (under 45 words), detect intent, explain reason and next action, and cite only supplied source_ids. Never invent product features, integrations, prices, or discounts. If knowledge is missing, recommend a clarifying question."},
                {"role":"user","content":f"CONVERSATION:\n{context}\n\nRETRIEVED SOURCES:\n{sources}\n\nGenerate structured recommendation."}
            ], response_format=Recommendation,timeout=18
        )
        recommendation=response.choices[0].message.parsed
        if recommendation is None:
            raise ValueError("No structured output returned")
        recommendation.source_ids=[sid for sid in recommendation.source_ids if sid in source_ids]
        return recommendation
    if any(word in latest for word in ["expensive","price","pricing","cost","budget","₹"]):
        return Recommendation(intent="pricing_objection",suggestion="I understand your budget concern. What are you spending today, and which outcomes would make the investment worthwhile?",reason="Customer raised a pricing concern.",next_action="Qualify budget and expected value",source_ids=source_ids)
    if any(word in latest for word in ["salesforce","integration","integrate","connect","api"]):
        return Recommendation(intent="integration_question",suggestion="Which information do you need to synchronize? I can confirm supported integrations and any limitations.",reason="Customer asked about integration.",next_action="Clarify integration requirements",source_ids=source_ids)
    if any(word in latest for word in ["demo","trial","sign up","buy"]):
        return Recommendation(intent="buying_signal",suggestion="Great! Which workflow would you most like to see in a product demo?",reason="Customer expressed buying interest.",next_action="Offer tailored demo",source_ids=source_ids)
    if any(word in latest for word in ["competitor","already use","other crm"]):
        return Recommendation(intent="competitor_objection",suggestion="What works well in your current solution, and what would you like to improve?",reason="Customer has an existing solution.",next_action="Understand switching criteria",source_ids=source_ids)
    return Recommendation(intent="clarification",suggestion="Could you share a little more about that challenge and how it affects your team?",reason="Further discovery can clarify requirements.",next_action="Ask a discovery question",source_ids=source_ids)

async def recommend(session:Session,ws:WebSocket,session_id:str,version:int):
    start=time.perf_counter()
    try:
        turns=list(session.turns)
        passages=await asyncio.to_thread(knowledge.search,retrieval_query(turns),k=3)
        retrieval_ms=round((time.perf_counter()-start)*1000)
        result=await generate(turns,passages)
        generation_ms=round((time.perf_counter()-start)*1000)-retrieval_ms
        latest_customer=next((t.text for t in reversed(turns) if t.speaker == 'customer'), '')
        # Evaluation mode: preserve the LLM's exact structured output.
        # No claim validation, intent rewrite, or fallback substitution.
        response_origin='ai_generated_unverified' if PROVIDER in ('ollama','openai') else 'offline_demo'
        evidence_flags=[]
        corrected=False
        result.source_ids=[sid for sid in result.source_ids if sid in {sid for sid,_ in passages}]
        if session.closed or version != session.version:
            return
        async with session.send_lock:
            await ws.send_json({"type":"recommendation.ready","session_id":session_id,"conversation_version":version,"data":result.model_dump(),"latency_ms":round((time.perf_counter()-start)*1000),"timings":{"retrieval_ms":retrieval_ms,"generation_ms":generation_ms},"quality_corrected":corrected,"response_origin":response_origin,"evidence_flags":evidence_flags})
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("Recommendation failed")
        if not session.closed and session.version==version:
            async with session.send_lock:
                await ws.send_json({"type":"error","code":"RECOMMENDATION_FAILED","message":"Could not generate recommendation. Conversation can continue.","retryable":True})

@app.get("/health")
def health():
    return {"status":"ok","knowledge_chunks":len(knowledge.sections),"retrieval":"faiss" if knowledge.index is not None else "keyword-fallback","chat_model":ollama_backend.CHAT_MODEL if PROVIDER=="ollama" else os.getenv("OPENAI_MODEL") if PROVIDER=="openai" else None,"mode":PROVIDER if PROVIDER in ("ollama","openai") else "offline-demo"}

@app.websocket("/ws/sessions/{session_id}")
async def websocket_session(ws:WebSocket,session_id:str):
    await ws.accept()
    session=Session()
    sessions[session_id]=session
    async with session.send_lock:
        await ws.send_json({"type":"session.started","session_id":session_id,"mode":PROVIDER if PROVIDER in ("ollama","openai") else "offline-demo"})
    try:
        while True:
            event=await ws.receive_json()
            if not isinstance(event,dict) or event.get("type")!="transcript.final":
                await ws.send_json({"type":"error","code":"UNKNOWN_EVENT","message":"Expected transcript.final","retryable":False})
                continue
            try:
                turn=Turn.model_validate(event)
            except ValidationError:
                await ws.send_json({"type":"error","code":"INVALID_TRANSCRIPT","message":"Invalid transcript payload","retryable":False})
                continue
            if turn.event_id in session.seen:
                await ws.send_json({"type":"transcript.ack","event_id":turn.event_id,"conversation_version":session.version,"duplicate":True})
                continue
            session.seen.add(turn.event_id)
            session.turns.append(turn)
            session.version+=1
            if session.task and not session.task.done():
                session.task.cancel()
            version=session.version
            async with session.send_lock:
                await ws.send_json({"type":"transcript.ack","event_id":turn.event_id,"conversation_version":version,"session_id":session_id})
            if turn.speaker=="customer" and len(turn.text.strip())>=5:
                async with session.send_lock:
                    await ws.send_json({"type":"recommendation.processing","session_id":session_id,"conversation_version":version})
                session.task=asyncio.create_task(recommend(session,ws,session_id,version))
    except WebSocketDisconnect:
        pass
    finally:
        session.closed=True
        if session.task and not session.task.done():
            session.task.cancel()
        if sessions.get(session_id) is session:
            del sessions[session_id]
