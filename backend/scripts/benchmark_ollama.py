"""Benchmark local Ollama chat models on fixed sales scenarios, no FastAPI needed.
Run: python scripts/benchmark_ollama.py --models qwen3:4b qwen3:1.7b
"""
import argparse
import json
import statistics
import time
import httpx

CASES = [
 ("pricing", "We have 15 SDRs using Excel and miss follow-ups. Your CRM seems expensive. Why switch?"),
 ("integration", "Does FlowDesk integrate with Salesforce?"),
 ("buying", "Can we schedule a demo next week?"),
 ("competitor", "We already use another CRM. Why switch?"),
]
KNOWLEDGE = ("FlowDesk CRM is fictional. Starter INR 1999/month, Growth INR 4999/month; "
             "seat limits undocumented. Supports reminders and pipeline tracking. "
             "Native Salesforce integration not supported. Google Sheets CSV import is supported. "
             "No free trial or discount is promised.")
def run_case(client, model, text):
    payload={"model":model,"stream":False,"think":False,"keep_alive":"30m",
             "format":"json",
             "options":{"temperature":0.1,"num_predict":150,"num_ctx":2048},
             "messages":[
               {"role":"system","content":"You are a sales copilot. Return JSON with keys suggestion, intent, reason, next_action. Reply to latest question in under 45 words; do not invent features, pricing or free offers."},
               {"role":"user","content":f"PRODUCT: {KNOWLEDGE}\nCUSTOMER: {text}"}]}
    started=time.perf_counter()
    result=client.post("/api/chat",json=payload)
    result.raise_for_status()
    data=result.json()
    return {"wall_ms":round((time.perf_counter()-started)*1000),
            "load_ms":round(data.get("load_duration",0)/1e6),
            "prompt_ms":round(data.get("prompt_eval_duration",0)/1e6),
            "generation_ms":round(data.get("eval_duration",0)/1e6),
            "tokens":data.get("eval_count",0),
            "answer":data.get("message",{}).get("content","")}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--models",nargs="+",default=["qwen3:4b","qwen3:1.7b"])
    p.add_argument("--url",default="http://127.0.0.1:11434")
    a=p.parse_args()
    with httpx.Client(base_url=a.url,timeout=180) as client:
        for model in a.models:
            print("\nMODEL:",model)
            metrics=[]
            for label,question in CASES:
                try:
                    r=run_case(client,model,question)
                    metrics.append(r["wall_ms"])
                    print(json.dumps({"scenario":label,**r},ensure_ascii=False))
                except Exception as exc:
                    print("FAILED",label,type(exc).__name__,str(exc))
            if metrics:
                print("median_ms:",statistics.median(metrics),"max_ms:",max(metrics))
if __name__=="__main__":
    main()
