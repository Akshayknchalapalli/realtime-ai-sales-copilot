"""Document-backed SDR recovery, not an LLM response.

Used ONLY when the model's output violates verified product constraints or
fails speakability checks. Responses are explicitly labeled as recovery.
The fictional FlowDesk facts come from knowledge/*.md.
"""
import re

def recover(latest: str, passages: list[tuple[str, str]], intent: str) -> dict:
    q=latest.lower()
    all_sources={sid:txt for sid,txt in passages}
    source_ids=list(all_sources)
    def ids(prefixes):
        return [sid for sid in source_ids if sid.startswith(prefixes)]
    def result(suggestion, reason, next_action, sources):
        return dict(intent=intent,suggestion=suggestion,reason=reason,next_action=next_action,source_ids=sources)

    if "salesforce" in q:
        return result(
            "FlowDesk does not currently support native Salesforce integration. Which Salesforce records would your team need to transfer or keep synchronized?",
            "The product documentation explicitly states that native Salesforce integration is unavailable.",
            "Document the integration requirements without promising synchronization.",
            ids(("integrations",)))
    if re.search(r"\b(?:churn|cancel\w*|subscription.*predict|predict.*subscription)\b",q):
        return result(
            "I can't confirm that FlowDesk offers AI churn prediction. Which customer signals would you want to use to identify cancellation risk?",
            "AI churn prediction is not confirmed by the product knowledge base.",
            "Capture the required prediction use case and verify feasibility.",
            [])
    if re.search(r"\b(?:expensive|pricing|price|cost|budget|afford)\b",q):
        return result(
            "I understand your pricing concern. How much time is your team spending on manual follow-ups, and what outcome would justify the investment?",
            "The customer raises cost concerns; no unsupported pricing or plan-fit claim is needed.",
            "Qualify the business impact and review documented plans.",
            ids(("pricing","objections")))
    if re.search(r"\b(?:demo|demonstration|schedule a call)\b",q):
        return result(
            "Absolutely. Which day next week works best for a demonstration, and would you prefer to focus on lead tracking or follow-up reminders?",
            "The latest customer turn requests a demonstration.",
            "Agree on a specific day and demo focus.",
            [])
    if re.search(r"\b(?:already.*crm|switch|competitor|current crm)\b",q):
        return result(
            "What is working well with your current CRM, and which parts of your sales process would you most like to improve?",
            "Understand switching criteria rather than promising undocumented features.",
            "Discover pain points and compare only documented functionality.",
            [])
    if re.search(r"\b(?:remind|follow.up|reminder)\b",q):
        return result(
            "Yes, FlowDesk supports follow-up reminders for leads. How does your team currently track which follow-ups are due?",
            "Lead follow-up reminders are documented.",
            "Ask about existing follow-up processes.",
            ids(("faq","product_overview")))
    if re.search(r"\b(?:prioritiz|lead scor)\b",q):
        return result(
            "FlowDesk supports lead tracking and follow-up reminders, but I would need to confirm automated lead scoring. How do you currently decide which leads to contact first?",
            "The documented reminder feature does not establish automatic prioritization.",
            "Discover prioritization criteria without promising scoring.",
            ids(("faq","product_overview")))
    return result(
        "Could you describe the part of your workflow you'd most like to improve? I can confirm which documented capabilities apply.",
        "There isn't enough verified information for a more specific product commitment.",
        "Clarify the customer need and check product documentation.",
        [])
