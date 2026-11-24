import os
os.environ["LLM_API_KEYS"] = "test-key-one,test-key-two"
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["ENABLE_FAILURE_SIMULATION"] = "true"

from fastapi.testclient import TestClient
from app.main import app
from app import main

def fake_ask(messages, failure_header=None):
    from app.llm import Result
    return Result("Test response", {"resolution_source":"LIVE_INFERENCE","model":"test/model","latency_ms":4,"input_tokens":12,"output_tokens":3,"key_id":"key_1","fallback_attempts":0})

def test_chat_and_history(monkeypatch):
    monkeypatch.setattr(main, "ask", fake_ask)
    with TestClient(app) as client:
        response = client.post("/chat", json={"session_id":"test-session","message":"hello"})
        assert response.status_code == 200
        assert response.json()["metadata"]["input_tokens"] == 12
        history = client.get("/sessions/test-session/messages")
        assert history.status_code == 200
        assert len(history.json()["messages"]) == 2

def test_validation():
    with TestClient(app) as client:
        assert client.post("/chat", json={"session_id":"x","message":"   "}).status_code == 422
