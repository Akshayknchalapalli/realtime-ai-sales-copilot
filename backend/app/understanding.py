"""Small first-pass customer understanding task for local Qwen."""
import json
import httpx
from . import ollama_backend

async def understand(latest, context):
    schema={"type":"object","properties":{
        "situation":{"type":"string"},
        "need":{"type":"string"},
        "discovery_focus":{"type":"string"}},
        "required":["situation","need","discovery_focus"]}
    payload={"model":ollama_backend.CHAT_MODEL,"stream":False,"think":False,"format":schema,
       "options":{"temperature":0,"num_predict":240,"num_ctx":2048},
       "messages":[
          {"role":"system","content":"Extract customer facts for a sales representative. Summarize the CUSTOMER's situation, need, and one sensible discovery focus. Do not invent problems or product capabilities. These are internal notes, not spoken customer dialogue."},
          {"role":"user","content":"LATEST CUSTOMER:\n"+latest+"\nRECENT CONTEXT:\n"+context[-900:]}]}
    async with httpx.AsyncClient(timeout=90) as client:
        response=await client.post(ollama_backend.BASE+"/api/chat",json=payload)
        response.raise_for_status()
    raw=response.json().get("message",{}).get("content","")
    try:
        parsed=json.loads(raw)
        if not isinstance(parsed,dict) or any(not isinstance(parsed.get(k),str) for k in ("situation","need","discovery_focus")):
            raise ValueError("Incomplete briefing")
        return parsed
    except (json.JSONDecodeError,ValueError):
        # Truncated optional briefing must not stop the real model response.
        return {"situation":latest,"need":"Unknown","discovery_focus":"Ask about the customer's stated situation"}
