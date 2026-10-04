import time
import pytest
from fastapi.testclient import TestClient
from axiom_mem.server import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_in_session_streaming_recency(client):
    user_id = f"eval:test_stream_{int(time.time() * 1000)}"
    session_id = f"sess_stream_{int(time.time() * 1000)}"

    # Observation 1
    client.post("/add", json={
        "request_id": f"req_s1_{int(time.time() * 1000)}",
        "messages": [
            {"role": "user", "timestamp": 1700000000000, "content": "Telemetry stream: Device battery 95%, CPU temp 42C."}
        ],
        "user_id": user_id,
        "session_id": session_id
    })

    # Observation 2
    client.post("/add", json={
        "request_id": f"req_s2_{int(time.time() * 1000)}",
        "messages": [
            {"role": "user", "timestamp": 1700000010000, "content": "Telemetry stream: Device battery 88%, CPU temp 48C."}
        ],
        "user_id": user_id,
        "session_id": session_id
    })

    # Observation 3 (latest)
    client.post("/add", json={
        "request_id": f"req_s3_{int(time.time() * 1000)}",
        "messages": [
            {"role": "user", "timestamp": 1700000020000, "content": "Telemetry stream: Device battery 79%, CPU temp 55C."}
        ],
        "user_id": user_id,
        "session_id": session_id
    })

    # Query for latest reading
    resp = client.post("/search", json={
        "query": "What is the latest reported battery level and CPU temperature?",
        "user_id": user_id,
        "top_k": 3
    })
    assert resp.status_code == 200
    hits = resp.json()["data"]
    assert len(hits) == 3

    # Latest reading (Observation 3: 79%, 55C) MUST rank at position 1
    assert "79%" in hits[0]["content"]
    assert "55C" in hits[0]["content"]
