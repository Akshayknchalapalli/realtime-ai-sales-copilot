"""Shared recommendation finalization for the demo."""
import re
from .quality import guard, latest_intent
from .evidence import evidence_issues
from .recovery import recover

def finalize(raw, latest, passages):
    checked, rejected = guard(raw, latest, [sid for sid, _ in passages])
    flags = evidence_issues(latest, raw.get("suggestion", ""), passages)
    expected = latest_intent(latest)
    intent = expected or raw.get("intent", "clarification")
    reply = raw.get("suggestion", "").lower()
    question = latest.lower()
    mismatch = bool(expected and raw.get("intent") != expected)
    irrelevant = bool(re.search(r"churn|cancel|predict.*subscription", question)) and not bool(re.search(r"churn|cancel|predict|confirm|verify", reply))
    marketing = bool(re.search(r"seamless integrations?|streamlined workflows?|competitive pricing|flexible (?:pricing|plans)", reply))
    if rejected or flags or mismatch or irrelevant or marketing:
        return recover(latest, passages, intent), "verified_recovery", flags
    checked["intent"] = intent
    return checked, "ai_generated", []
