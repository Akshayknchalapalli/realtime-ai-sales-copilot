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
UNVERIFIED_INTEGRATION_WORKAROUND = re.compile(
    r"\b(?:third.party|external|zapier|make\.com)\b.{0,110}\b(?:sync\w*|synchroniz\w*|integrat\w*|connect\w*)\b|"
    r"\b(?:sync\w*|synchroniz\w*|integrat\w*)\b.{0,110}\b(?:third.party|external|zapier|make\.com)\b", re.I
)
CSV_SYNC = re.compile(
    r"\b(?:csv|excel)\b.{0,90}\b(?:sync\w*|synchroniz\w*|real.time integration)\b|"
    r"\b(?:sync\w*|synchroniz\w*)\b.{0,90}\b(?:csv|excel)\b", re.I
)

def latest_intent(text: str) -> str | None:
    q=text.lower()
    if re.search(r"\b(?:schedule|book|arrange)\b.{0,50}\b(?:demo|demonstration)\b|\b(?:demo|demonstration)\b",q):
        return "buying_signal"
    # Explicit pricing concerns outweigh generic comparisons or switching language.
    if re.search(r"\b(?:expensive|pricing|price|cost|budget|afford\w*|cheaper)\b",q):
        return "pricing_objection"
    if re.search(r"\b(?:salesforce|integrat\w*|connect to)\b",q):
        return "integration_question"
    if re.search(r"\b(?:already (?:use|using)|current crm|another crm|why (?:should|would) we switch)\b",q):
        return "competitor_objection"
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

def safe_abstention(latest: str) -> dict:
    """Neutral fallback only when a known risky claim or malformed suggestion is found."""
    return {
        "intent": "clarification",
        "suggestion": "I want to make sure I give you accurate information. Could you clarify your requirements while I check the relevant product details?",
        "reason": "The generated response failed a safety or speakability check; no unverified capability was promised.",
        "next_action": "Check product documentation and confirm the capability before making a commitment.",
        "source_ids": [],
    }


def unsupported_claim_or_echo(suggestion: str, latest: str) -> bool:
    """Known regression checks; not comprehensive evidence verification."""
    normalized = lambda t: re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()
    if normalized(suggestion) == normalized(latest):
        return True
    # Reject near-verbatim questions about the same feature, even with changed subject.
    if (suggestion.strip().endswith("?") and
        (re.search(r"\\b(?:can|does|how)\\s+(?:flowdesk|your crm)\\b", suggestion, re.I))
        and len(set(normalized(suggestion).split()) & set(normalized(latest).split())) >= 5):
        return True
    # FlowDesk documentation explicitly denies native Salesforce synchronization.
    if re.search(r"\\bsalesforce\\b", suggestion, re.I):
        if re.search(r"\\b(?:can|does|will|offers?|provides?|supports?)\\b.{0,90}\\b(?:sync\\w*|synchroniz\\w*|integrat\\w*|connect\\w*)\\b.{0,90}\\bsalesforce\\b", suggestion, re.I):
            return True
        if re.search(r"\\b(?:sync\\w*|synchroniz\\w*|integrat\\w*)\\b.{0,75}\\b(?:with|to)\\s+salesforce\\b", suggestion, re.I) and not re.search(r"\\b(?:not|don't|doesn't|cannot|can't|unsupported|no native)\\b", suggestion, re.I):
            return True
    # Predictive churn analytics are not documented in this fictional CRM knowledge base.
    if re.search(r"\\b(?:cancel\\w*|churn|retention risk)\\b", latest, re.I):
        if re.search(r"\\b(?:we|flowdesk|our crm)\\s+(?:can|will|do|does|offer\\w*)\\b.{0,100}\\b(?:analyz\\w*|predict\\w*|identify risk|forecast\\w*)\\b", suggestion, re.I):
            return True
    return False


def guard(recommendation: dict, latest: str, allowed_source_ids: list[str]) -> tuple[dict, bool]:
    """Preserve dynamic model responses unless a specific safety or formatting check fails.

    This is a narrow risk filter, not a replacement intent classifier or fact checker.
    """
    rec = dict(recommendation)
    rec["source_ids"] = [sid for sid in rec.get("source_ids", []) if sid in allowed_source_ids]
    combined = " ".join(str(rec.get(k, "")) for k in ("suggestion", "reason", "next_action"))
    if (OFFERS.search(combined) or SALESFORCE_AFFIRMATION.search(combined)
            or CSV_SYNC.search(combined)
            or UNVERIFIED_INTEGRATION_WORKAROUND.search(combined)
            or PLAN_FIT.search(combined)):
        return safe_abstention(latest), True
    suggestion = str(rec.get("suggestion", "")).strip()
    if not 4 <= len(suggestion.split()) <= 45 or INTERNAL_LANGUAGE.search(suggestion) or unsupported_claim_or_echo(suggestion, latest):
        return safe_abstention(latest), True
    return rec, False
