"""Evidence-aware safety gate for fictional FlowDesk CRM.

This is deliberately conservative, not general natural-language entailment.
The source documents define supported and denied capabilities. When evidence
is absent, avoid affirmative product claims instead of assuming capability.
"""
import re

PRODUCT_RE = re.compile(r"\b(?:flowdesk|we|our (?:crm|product|platform))\b", re.I)
AFFIRMATIVE_RE = re.compile(r"\b(?:can|will|supports?|offers?|provides?|includes?|has|uses?|documents?)\b", re.I)
NEGATION_RE = re.compile(r"\b(?:not|no|never|cannot|can't|don't|doesn't|unsupported|unavailable|unconfirmed|need to confirm|would need to confirm)\b", re.I)

# These are capability families, not intent-to-response mappings.
CAPABILITIES = {
    "salesforce_sync": re.compile(r"\bsalesforce\b", re.I),
    "churn_prediction": re.compile(r"\b(?:churn|cancellations?|subscription patterns|retention risk)\b", re.I),
    "lead_scoring": re.compile(r"\b(?:lead (?:scoring|prioritization)|prioritiz\w+ leads)\b", re.I),
    "team_assignment": re.compile(r"\b(?:automatic assignment|assign(?:ment|s)? across teams|multi.team permissions)\b", re.I),
}
ASSERTIONS = {
    "salesforce_sync": re.compile(r"\b(?:synchroniz\w*|sync\w*|integrat\w*|connect\w*)\b", re.I),
    "churn_prediction": re.compile(r"\b(?:predict\w*|analyz\w*|forecast\w*|identify risk)\b", re.I),
    "lead_scoring": re.compile(r"\b(?:automatic\w*|ai.powered|scor\w*|prioritiz\w*)\b", re.I),
    "team_assignment": re.compile(r"\b(?:assign\w*|automat\w*)\b", re.I),
}
UNSUPPORTED_PHRASES = re.compile(
    r"\b(?:competitive pricing|flexible (?:pricing|plans)|ai.powered lead prioritization)\b", re.I
)

def evidence_issues(latest: str, suggestion: str, passages: list[tuple[str,str]]) -> list[str]:
    """Check positive factual assertions against the supplied evidence.

    A retrieved chunk being top-k does not itself establish factual support.
    """
    issues=[]
    text=suggestion.strip()
    if UNSUPPORTED_PHRASES.search(text):
        issues.append("unverified_marketing_claim")
    if not PRODUCT_RE.search(text):
        return issues
    evidence="\n".join(chunk for _,chunk in passages).lower()
    sentences=re.split(r"(?<=[.!?])\s+",text)
    for family, detector in CAPABILITIES.items():
        for sentence in sentences:
            if not detector.search(sentence) or not ASSERTIONS[family].search(sentence):
                continue
            if NEGATION_RE.search(sentence):
                continue
            if not AFFIRMATIVE_RE.search(sentence) and not re.search(r"\b(?:documents?|documented)\b",sentence,re.I):
                continue
            if family == "salesforce_sync":
                # Explicit limitation in integrations.md takes precedence.
                issues.append(f"unsupported_{family}")
            elif family == "churn_prediction":
                # No affirmative documentation currently supports predictive churn features.
                if not re.search(r"\b(?:supports?|provides?)\b.{0,70}\b(?:churn prediction|predictive churn)\b",evidence):
                    issues.append(f"unsupported_{family}")
            elif family == "lead_scoring":
                if not re.search(r"\b(?:automated lead scoring|automatic lead prioritization)\b",evidence):
                    issues.append(f"unsupported_{family}")
            elif family == "team_assignment":
                if not re.search(r"\b(?:team assignment|assign leads across teams)\b",evidence):
                    issues.append(f"unsupported_{family}")
    return list(dict.fromkeys(issues))
