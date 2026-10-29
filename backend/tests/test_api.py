from fastapi.testclient import TestClient
from app.main import app

def test_health():
    assert TestClient(app).get("/health").json()["status"] == "ok"

def test_customer_gets_recommendation():
    with TestClient(app).websocket_connect("/ws/sessions/example") as ws:
        assert ws.receive_json()["type"]=="session.started"
        ws.send_json({"type":"transcript.final","event_id":"a","speaker":"customer","text":"This price is too expensive"})
        assert ws.receive_json()["type"]=="transcript.ack"
        assert ws.receive_json()["type"]=="recommendation.processing"
        event=ws.receive_json()
        assert event["type"]=="recommendation.ready"
        assert event["data"]["intent"]=="pricing_objection"

def test_sdr_turn_does_not_trigger():
    with TestClient(app).websocket_connect("/ws/sessions/example2") as ws:
        ws.receive_json()
        ws.send_json({"type":"transcript.final","event_id":"a","speaker":"sdr","text":"What is your current budget?"})
        assert ws.receive_json()["type"]=="transcript.ack"
