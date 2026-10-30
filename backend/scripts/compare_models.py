"""Compare available local Ollama models on identical retrieved evidence.
Run: python -m scripts.compare_models
No response substitutions. Review printed recommendations for factual accuracy.
"""
import asyncio
import json
import statistics
import time
import httpx
from app import ollama_backend
from app.main import Turn, knowledge, retrieval_query, generate
from scripts.evaluate_scenarios import CASES

async def main():
    with httpx.Client(timeout=10) as client:
        response=client.get(ollama_backend.BASE+"/api/tags")
        response.raise_for_status()
        installed={m["name"] for m in response.json().get("models",[])}
    choices=[m for m in ("qwen3:4b","qwen3:1.7b") if m in installed]
    if not choices:
        print("No comparison model found. Run: ollama pull qwen3:4b")
        return
    initial=ollama_backend.CHAT_MODEL
    try:
        for model in choices:
            ollama_backend.CHAT_MODEL=model
            results=[]
            print("\nMODEL:",model,flush=True)
            for name, question, expected in CASES:
                turns=[Turn(event_id=name,speaker="customer",text=question)]
                docs=await asyncio.to_thread(knowledge.search,retrieval_query(turns),k=3)
                start=time.perf_counter()
                try:
                    rec=await generate(turns,docs)
                    elapsed=round((time.perf_counter()-start)*1000)
                    row={"case":name,"model":model,"expected_intent":expected,"predicted_intent":rec.intent,
                         "intent_match":expected==rec.intent,"latency_ms":elapsed,
                         "suggestion":rec.suggestion,"sources":rec.source_ids}
                    results.append(row)
                    print(json.dumps(row,ensure_ascii=False),flush=True)
                except Exception as exc:
                    print(json.dumps({"case":name,"error":str(exc)}),flush=True)
            if results:
                print(json.dumps({"model":model,"intent_matches":sum(r["intent_match"] for r in results),
                    "completed":len(results),"median_generation_ms":statistics.median(r["latency_ms"] for r in results),
                    "note":"Intent match is not factual accuracy. Review claims and speakability manually."}),flush=True)
    finally:
        ollama_backend.CHAT_MODEL=initial

if __name__=="__main__":
    asyncio.run(main())
