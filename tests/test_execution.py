import time
import pytest
from fastapi.testclient import TestClient
from axiom_mem.server import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_execution_procedural_boost_and_expansion(client):
    user_id = f"eval:test_exec_{int(time.time() * 1000)}"

    # Add procedural instructions
    client.post("/add", json={
        "request_id": f"req_steps_{int(time.time() * 1000)}",
        "messages": [
            {"role": "user", "content": "Step 1: Install dependencies with `pip install -e .`"},
            {"role": "user", "content": "Step 2: Initialize SQLite database schema with `python -m axiom_mem.store`"},
            {"role": "user", "content": "Step 3: Launch test runner with `pytest tests/`"}
        ],
        "user_id": user_id,
        "session_id": "sess_deploy"
    })

    # Add conversational noise
    client.post("/add", json={
        "request_id": f"req_chat_{int(time.time() * 1000)}",
        "messages": [
            {"role": "user", "content": "I like writing Python code because the syntax is clean."}
        ],
        "user_id": user_id,
        "session_id": "sess_chat"
    })

    resp = client.post("/search", json={
        "query": "How to install dependencies and run tests step by step?",
        "user_id": user_id,
        "top_k": 5
    })
    assert resp.status_code == 200
    hits = resp.json()["data"]
    assert len(hits) >= 3

    top_content = hits[0]["content"]
    assert any(term in top_content for term in ["Step 1", "Step 2", "Step 3", "pip install"])
