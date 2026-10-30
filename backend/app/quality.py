"""Conservative, deterministic output guardrails for the interview MVP.

This is not a full fact checker. It protects documented high-risk claims and
requires suggestions to sound like words an SDR could say aloud.
"""
import re

OFFERS = re.compile(
    r"\b(?:free (?:demo|trial|consultation|setup)|complimentary|without (?:any |extra )?cost|"
    r"no (?:extra )?cost|at no (?:extra )?cost|guaranteed? (?:results|savings)|"
    r"(?:special|guaranteed) discount|(?:discount|trial) (?:is )?available)\b", re.I
)
PLAN_FIT = re.compile(
    r"\b(?:starter|growth) plan\b.{0,65}\b(?:fits?|right for|suitable|ideal|recommend|best)\b|"
    r"\b(?:recommend|choose|go with)\b.{0,45}\b(?:starter|growth)\b", re.I
)
INTERNAL_LANGUAGE = re.compile(
    r"^\s*(?:explore|focus on|suggest|recommend|highlight|consider|offer|discuss|"
    r"emphasize|position|mention|ask (?:the )?customer)\b", re.I
)
SALESFORCE_AFFIRMATION = re.compile(
    r"\b(?:we|flowdesk|our (?:product|crm))\s+(?:do\s+)?(?:support|supports|integrate|integrates|connect|connects)\b"
    r".{0,80}\bsalesforce\b|\bsalesforce\b.{0,60}\b(?:is supported|is integrated|works natively)\b", re.I
)
CSV_SYNC = re.compile(
    r"\b(?:csv|excel)\b.{0,90}\b(?:sync\w*|synchroniz\w*|real.time integration)\b|"
    r"\b(?:sync\w*|synchroniz\w*)\b.{0,90}\b(?:csv|excel)\b", re.I
)

def latest_intent(text: str) -> str | None:
    q=text.lower()
    if re.search(r"\b(?:schedule|book|arrange)\b.{0,50}\b(?:demo|demonstration)\b|\b(?:demo|demonstration)\b",q):
        return "buying_signal"
    if re.search(r"\b(?:already (?:use|using)|current crm|another crm|why (?:should|would) we switch)\b",q):
        return "competitor_objection"
    if re.search(r"\b(?:salesforce|integrat\w*|connect to)\b",q):
        return "integration_question"
    if re.search(r"\b(?:expensive|pricing|price|cost|budget)\b",q):
        return "pricing_objection"
    return None

def fallback(intent: str, latest: str, source_ids: list[str]) -> dict:
    if intent == "buying_signal":
        return dict(intent=intent,suggestion="Certainly. What day works best for a demonstration, and which workflow would you like us to focus on?",reason="Customer requested a demonstration.",next_action="Confirm timing and demonstration focus.",source_ids=[])
    if intent == "competitor_objection":
        return dict(intent=intent,suggestion="What is working well with your current CRM, and what would you most like to improve?",reason="Customer has an existing CRM and wants to understand the value of switching.",next_action="Discover current pain points and switching criteria.",source_ids=[])
    if intent == "integration_question":
        return dict(intent=intent,suggestion="We don't currently support native Salesforce integration. Which data would you need to move or synchronize?",reason="Native Salesforce integration is not documented as available.",next_action="Understand whether one-time import meets the need; do not promise continuous synchronization.",source_ids=[sid for sid in source_ids if sid.startswith("integrations")])
    if intent == "pricing_objection":
        return dict(intent=intent,suggestion="I understand the pricing concern. What are missed follow-ups costing your team, and what budget are you considering?",reason="Customer raised a cost concern; plan eligibility is not documented.",next_action="Clarify needs before recommending a specific plan.",source_ids=[sid for sid in source_ids if sid.startswith(("pricing","objections"))])
    return dict(intent="clarification",suggestion="Could you tell me a little more about the challenge you want to solve?",reason="More customer context is needed.",next_action="Ask a discovery question.",source_ids=[])

def guard(recommendation: dict, latest: str, allowed_source_ids: list[str]) -> tuple[dict,bool]:
    """Return a vetted structured recommendation and whether it was replaced."""
    rec=dict(recommendation)
    rec["source_ids"]=[x for x in rec.get("source_ids",[]) if x in allowed_source_ids]
    intent=latest_intent(latest)
    # A clear latest intent wins over stale conversation history.
    if intent and rec.get("intent") != intent:
        return fallback(intent,latest,allowed_source_ids),True
    combined=" ".join(str(rec.get(x,"")) for x in ("suggestion","reason","next_action"))
    if OFFERS.search(combined) or SALESFORCE_AFFIRMATION.search(combined) or CSV_SYNC.search(combined):
        return fallback(intent or rec.get("intent","clarification"),latest,allowed_source_ids),True
    if PLAN_FIT.search(combined):
        return fallback(intent or "pricing_objection",latest,allowed_source_ids),True
    suggestion=str(rec.get("suggestion","")).strip()
    if len(suggestion.split())>45 or len(suggestion.split())<4 or INTERNAL_LANGUAGE.search(suggestion):
        return fallback(intent or rec.get("intent","clarification"),latest,allowed_source_ids),True
    return rec,False
