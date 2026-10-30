from app.quality import guard

def base(intent, suggestion, next_action="Ask a relevant discovery question."):
    return {"intent":intent,"suggestion":suggestion,"reason":"Customer raised the issue.","next_action":next_action,"source_ids":[]}

def test_internal_instruction_replaced():
    r, changed=guard(base("competitor_objection","Explore how FlowDesk CRM can enhance existing workflows."),"We're already using another CRM. Why switch?",[])
    assert changed and r["suggestion"].startswith("What is working well")

def test_free_consultation_in_next_action_replaced():
    r, changed=guard(base("competitor_objection","What would you like to improve?","Offer a free consultation"),"We already use another CRM.",[])
    assert changed and "free" not in r["next_action"].lower()

def test_buying_signal_overrides_previous_integration():
    r,changed=guard(base("integration_question","We don't integrate with Salesforce."),"Can we schedule a demonstration next week?",[])
    assert changed and r["intent"]=="buying_signal"

def test_direct_spoken_answer_accepted():
    r,changed=guard(base("competitor_objection","What works well in your current CRM, and what would you like to improve?"),"We're already using another CRM.",[])
    assert not changed

def test_unverified_plan_fit_blocked():
    r,changed=guard(base("pricing_objection","The Starter plan is ideal for your team."),"Our pricing looks expensive.",[])
    assert changed and "ideal" not in r["suggestion"]

def test_synchronization_not_confused_with_csv_import():
    r,changed=guard(base("integration_question","CSV import supports synchronization with Salesforce."),"Can it integrate with Salesforce?",[])
    assert changed and "synchronization with Salesforce" not in r["suggestion"]

def test_sources_restricted():
    r,changed=guard({**base("feature_inquiry","We offer reminders for lead follow-ups."),"source_ids":["faq-002","made-up"]},"Can you remind us about follow-ups?",["faq-002"])
    assert not changed and r["source_ids"]==["faq-002"]
