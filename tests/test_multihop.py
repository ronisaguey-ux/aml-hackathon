import time
import pytest
from fastapi.testclient import TestClient
from axiom_mem.server import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_multihop_premise_expansion_and_ordering(client):
    user_id = f"eval:test_multihop_{int(time.time() * 1000)}"

    # Hop 1: connects query entity (Project Quasar) to bridge entity (Dr. Vikram Mehta)
    client.post("/add", json={
        "request_id": f"req_h1_{int(time.time() * 1000)}",
        "messages": [
            {"role": "user", "timestamp": 1700000000000, "content": "Project Quasar was established by quantum physicist Dr. Vikram Mehta."}
        ],
        "user_id": user_id,
        "session_id": "sess_quasar_1"
    })

    # Hop 2: connects bridge entity (Dr. Vikram Mehta) to target answer (University of Cambridge)
    client.post("/add", json={
        "request_id": f"req_h2_{int(time.time() * 1000)}",
        "messages": [
            {"role": "user", "timestamp": 1700000010000, "content": "Dr. Vikram Mehta earned his doctorate degree at the University of Cambridge."}
        ],
        "user_id": user_id,
        "session_id": "sess_quasar_2"
    })

    # Query targeting the multi-hop relational path
    resp = client.post("/search", json={
        "query": "Which academic institution conferred the doctoral degree of Project Quasar's founder?",
        "user_id": user_id,
        "top_k": 5
    })
    assert resp.status_code == 200
    hits = resp.json()["data"]
    assert len(hits) >= 2

    # Both hops must be present, adjacent, and strictly ordered: Hop 1 (source/anchor) at Rank 1, Hop 2 (target) at Rank 2
    assert "Project Quasar" in hits[0]["content"]
    assert "University of Cambridge" in hits[1]["content"]
