from app.quality import guard

def base(intent, suggestion, next_action="Ask a discovery question."):
    return {"intent":intent,"suggestion":suggestion,"reason":"Customer asked about the topic.","next_action":next_action,"source_ids":[]}

def test_dynamic_competitor_answer_is_preserved():
    rec=base("competitor_objection","What challenges are you experiencing with your current solution?")
    result, changed=guard(rec,"We already use another CRM. Why switch?",[])
    assert not changed and result["suggestion"]==rec["suggestion"]

def test_dynamic_pricing_answer_is_preserved():
    rec=base("pricing_objection","How much time does your team lose managing follow-ups, and what budget range are you considering?")
    result,changed=guard(rec,"Our CRM seems expensive. Why switch?",[])
    assert not changed and result==rec

def test_unseen_customer_question_preserves_ai_response():
    rec=base("other","How many contacts are you currently managing, and what process is slowing your team down?")
    result,changed=guard(rec,"Our lead intake is growing and we struggle to keep up.",[])
    assert not changed and result==rec

def test_mismatched_intent_is_not_replaced_with_canned_reply():
    rec=base("clarification","Which workflows are most important for your team right now?")
    result, changed=guard(rec,"We use another CRM. Why switch?",[])
    assert not changed and result["intent"]=="clarification"

def test_unsupported_free_offer_falls_back():
    rec=base("buying_signal","We can give you a free trial today.")
    result,changed=guard(rec,"Can we arrange a demo?",[])
    assert changed and result["intent"]=="clarification"
    assert "free" not in result["suggestion"].lower()

def test_free_consultation_in_next_action_blocked():
    rec=base("competitor_objection","What works well in your current CRM?","Offer a free consultation")
    result,changed=guard(rec,"We use another CRM.",[])
    assert changed and "free" not in result["next_action"].lower()

def test_unsupported_plan_fit_blocked():
    result,changed=guard(base("pricing_objection","The Starter plan is ideal for your team."),"Our pricing looks expensive.",[])
    assert changed and "ideal" not in result["suggestion"].lower()

def test_csv_sync_blocked():
    result,changed=guard(base("integration_question","CSV import supports synchronization with Salesforce."),"Can it integrate with Salesforce?",[])
    assert changed and "CSV import" not in result["suggestion"]

def test_csv_sync_reversed_blocked():
    result,changed=guard(base("integration_question","Synchronization with Salesforce is supported through CSV import."),"Can it integrate with Salesforce?",[])
    assert changed

def test_unverified_third_party_sync_blocked():
    rec=base("integration_question","We do not support Salesforce natively. Consider a third-party tool for synchronization.")
    result,changed=guard(rec,"Does FlowDesk integrate with Salesforce?",[])
    assert changed and "third-party" not in result["suggestion"]

def test_unverified_workaround_next_action_blocked():
    rec=base("integration_question","Which Salesforce data would you like to move?","Use an external integration tool to synchronize CRM data.")
    result,changed=guard(rec,"Do you integrate with Salesforce?",[])
    assert changed

def test_internal_instruction_blocked():
    result,changed=guard(base("competitor_objection","Explore how FlowDesk can enhance existing workflows."),"Why switch from our CRM?",[])
    assert changed and "Explore" not in result["suggestion"]

def test_sources_filtered_without_rewriting():
    rec={**base("feature_inquiry","We offer reminders for pending follow-ups."),"source_ids":["faq-002","unknown"]}
    result,changed=guard(rec,"Can you remind us about follow-ups?",["faq-002"])
    assert not changed and result["source_ids"]==["faq-002"]

def test_model_recommendation_preserved_even_with_pricing_and_switching():
    rec=base("pricing_objection","What would make an investment worthwhile given the follow-ups you currently miss?")
    result,changed=guard(rec,"Your CRM is expensive, why should we switch?",[])
    assert not changed and result["suggestion"]==rec["suggestion"]
