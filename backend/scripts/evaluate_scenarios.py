"""Evaluate the actual Ollama + RAG recommendation path against labeled, unseen scenarios.

Run from backend: python -m scripts.evaluate_scenarios
Requires Ollama running and the models in backend/.env.
"""
import asyncio
import json
import time
import re
from app.main import Turn, knowledge, retrieval_query, generate, Recommendation
from app.quality import guard, safe_abstention
from app.evidence import evidence_issues

CASES = [
    ("lead_priority","Our leads come from several websites and we cannot prioritize them. What should we do?","feature_inquiry"),
    ("team_coordination","We have three sales teams across different cities. How could CRM help coordinate follow-ups?","feature_inquiry"),
    ("churn_prediction","Can your product predict which customers will cancel subscriptions using AI?","feature_inquiry"),
    ("pricing","We use Excel but your CRM seems expensive. Why should we switch?","pricing_objection"),
    ("salesforce","Can FlowDesk synchronize leads with Salesforce?","integration_question"),
    ("buying","Can we schedule a demonstration next week?","buying_signal"),
    ("competitor","We're already using another CRM. What would improve if we switched?","competitor_objection"),
    ("reminders","Can your CRM remind our representatives about pending follow-ups?","feature_inquiry"),
]
async def main():
    results=[]
    for name,query,expected in CASES:
        started=time.perf_counter()
        turns=[Turn(event_id=name,speaker="customer",text=query)]
        try:
            sources=await asyncio.to_thread(knowledge.search,retrieval_query(turns),k=3)
            rec=await generate(turns,sources)
            safe, corrected=guard(rec.model_dump(),query,[sid for sid,_ in sources])
            evidence_flags=evidence_issues(query,safe["suggestion"],sources)
            if evidence_flags:
                safe=safe_abstention(query)
                corrected=True
            review_flags=[]
            if re.search(r"\\b(?:competitive pricing|flexible plans|predict churn|predict cancellations|synchronize leads with Salesforce)\\b",rec.suggestion,re.I):
                review_flags.append("potentially_unsupported_claim")
            if re.sub(r"[^a-z0-9]+"," ",rec.suggestion.lower()).strip()==re.sub(r"[^a-z0-9]+"," ",query.lower()).strip():
                review_flags.append("customer_question_echo")
            results.append({"scenario":name,"expected_intent":expected,"predicted_intent":rec.intent,
              "intent_match":rec.intent==expected,"origin":"safety_fallback" if corrected else "ai_generated",
              "elapsed_ms":round((time.perf_counter()-started)*1000),
              "review_flags":review_flags,"evidence_flags":evidence_flags,"raw_suggestion":rec.suggestion,"raw_reason":rec.reason,"raw_next_action":rec.next_action,
              "suggestion":safe["suggestion"],"sources":safe["source_ids"]})
        except Exception as exc:
            results.append({"scenario":name,"error":str(exc)})
    for row in results:
        print(json.dumps(row,ensure_ascii=False))
    valid=[r for r in results if "intent_match" in r]
    if valid:
        print(f"Intent agreement: {sum(r['intent_match'] for r in valid)}/{len(valid)}; fallbacks: {sum(r['origin']=='safety_fallback' for r in valid)}/{len(valid)}. Compare raw_suggestion with suggestion to diagnose false positives.")
if __name__=="__main__":
    asyncio.run(main())
