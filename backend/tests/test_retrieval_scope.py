from app.main import Knowledge

def test_critical_salesforce_limitation_is_retrieved():
    k=Knowledge.__new__(Knowledge)
    k.sections=[
        ("integrations-002","## Supported\nFlowDesk supports CSV import."),
        ("integrations-003","## Limitations\nA native Salesforce integration is not currently supported."),
        ("faq-002","## Follow-ups\nLead reminders are supported."),
    ]
    result=k.include_critical_evidence("Can Salesforce synchronize?",[k.sections[0],k.sections[2]],2)
    assert result[0][0]=="integrations-003"
    assert len(result)==2

def test_unrelated_retrieval_not_changed():
    k=Knowledge.__new__(Knowledge)
    k.sections=[("faq-002","## Follow-ups\nLead reminders are supported.")]
    hits=[k.sections[0]]
    assert k.include_critical_evidence("How do reminders work?",hits,3)==hits
