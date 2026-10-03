import time
import pytest
from fastapi.testclient import TestClient
from axiom_mem.server import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_options_aware_ranking(client):
    user_id = f"eval:test_opt_{int(time.time() * 1000)}"

    client.post("/add", json={
        "request_id": f"req_opt_1_{int(time.time() * 1000)}",
        "messages": [
            {"role": "user", "content": "Server Alpha is running on port 8000."},
            {"role": "user", "content": "Server Beta is running on port 9090."}
        ],
        "user_id": user_id,
        "session_id": "sess_servers"
    })

    # Search with options distinguishing port 9090
    resp = client.post("/search", json={
        "query": "Which port is server Beta using?",
        "options": ["A. 8000", "B. 9090", "C. 3000", "D. 5432"],
        "user_id": user_id,
        "top_k": 2
    })
    assert resp.status_code == 200
    hits = resp.json()["data"]
    assert len(hits) > 0
    assert "9090" in hits[0]["content"]
    assert "Beta" in hits[0]["content"]
