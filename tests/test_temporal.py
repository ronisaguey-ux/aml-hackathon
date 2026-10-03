import time
import pytest
from fastapi.testclient import TestClient
from axiom_mem.server import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_temporal_resolution_and_iso_format(client):
    user_id = f"eval:test_temp_{int(time.time() * 1000)}"

    t_earlier = 1704067200000  # 2024-01-01
    t_later = 1719835200000    # 2024-07-01

    # Earlier state
    client.post("/add", json={
        "request_id": f"req_early_{int(time.time() * 1000)}",
        "messages": [
            {"role": "user", "timestamp": t_earlier, "content": "I am currently living in Montreal."}
        ],
        "user_id": user_id,
        "session_id": "sess_1"
    })

    # Updated state
    client.post("/add", json={
        "request_id": f"req_late_{int(time.time() * 1000)}",
        "messages": [
            {"role": "user", "timestamp": t_later, "content": "I moved to Vancouver last month."}
        ],
        "user_id": user_id,
        "session_id": "sess_2"
    })

    resp = client.post("/search", json={
        "query": "Where do I currently live?",
        "user_id": user_id,
        "top_k": 5
    })
    assert resp.status_code == 200
    hits = resp.json()["data"]
    assert len(hits) >= 2

    # Latest should be ranked first
    assert "Vancouver" in hits[0]["content"]
    assert "Montreal" in hits[1]["content"]

    # Check ISO-8601 formatting on created_at
    for hit in hits:
        assert hit["created_at"].endswith("Z")
        assert "T" in hit["created_at"]
