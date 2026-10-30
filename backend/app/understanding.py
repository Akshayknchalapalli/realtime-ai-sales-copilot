"""Small first-pass customer understanding task for local Qwen."""
import json
import httpx
from .ollama_backend import BASE, CHAT_MODEL

async def understand(latest, context):
    schema={"type":"object","properties":{
        "situation":{"type":"string"},
        "need":{"type":"string"},
        "discovery_focus":{"type":"string"}},
        "required":["situation","need","discovery_focus"]}
    payload={"model":CHAT_MODEL,"stream":False,"think":False,"format":schema,
       "options":{"temperature":0,"num_predict":100,"num_ctx":2048},
       "messages":[
          {"role":"system","content":"Extract customer facts for a sales representative. Summarize the CUSTOMER's situation, need, and one sensible discovery focus. Do not invent problems or product capabilities. These are internal notes, not spoken customer dialogue."},
          {"role":"user","content":"LATEST CUSTOMER:\n"+latest+"\nRECENT CONTEXT:\n"+context[-900:]}]}
    async with httpx.AsyncClient(timeout=90) as client:
        response=await client.post(BASE+"/api/chat",json=payload)
        response.raise_for_status()
    return json.loads(response.json()["message"]["content"])
