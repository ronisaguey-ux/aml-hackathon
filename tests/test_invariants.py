import time
import pytest
from fastapi.testclient import TestClient
from axiom_mem.server import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_immediate_visibility_invariant(client):
    user_id = f"eval:invar:vis_user_{int(time.time() * 1000)}"
    req_id = f"eval:invar:vis_req_{int(time.time() * 1000)}"
    unique_text = f"The unique verification code is ALPHA_OMEGA_{int(time.time() * 1000)}"

    add_resp = client.post("/add", json={
        "request_id": req_id,
        "messages": [
            {"role": "user", "content": unique_text}
        ],
        "user_id": user_id,
        "session_id": "session_vis"
    })
    assert add_resp.status_code == 200
    assert add_resp.json()["success"] is True

    # Immediate search in the exact same fraction of a second
    search_resp = client.post("/search", json={
        "query": unique_text,
        "user_id": user_id,
        "top_k": 5
    })
    assert search_resp.status_code == 200
    data = search_resp.json()["data"]
    assert len(data) > 0, "Immediate visibility invariant failed: new memory not found immediately!"
    assert unique_text in data[0]["content"]


def test_user_isolation_invariant(client):
    user_a = f"eval:invar:user_A_{int(time.time() * 1000)}"
    user_b = f"eval:invar:user_B_{int(time.time() * 1000)}"
    req_a = f"req_A_{int(time.time() * 1000)}"

    secret_message = "Private key shard for User A: SEC-998877"

    # Insert for user A
    client.post("/add", json={
        "request_id": req_a,
        "messages": [{"role": "user", "content": secret_message}],
        "user_id": user_a,
        "session_id": "session_A"
    })

    # User B queries for secret message
    leak_check = client.post("/search", json={
        "query": "Private key shard",
        "user_id": user_b,
        "top_k": 10
    })
    assert leak_check.status_code == 200
    b_data = leak_check.json()["data"]
    assert len(b_data) == 0, f"Critical security breach: user isolation violated! User B received: {b_data}"


def test_idempotency_invariant(client):
    user_id = f"eval:invar:idem_user_{int(time.time() * 1000)}"
    req_id = f"eval:invar:idem_req_{int(time.time() * 1000)}"
    fact = "Idempotency test target statement."

    payload = {
        "request_id": req_id,
        "messages": [{"role": "user", "content": fact}],
        "user_id": user_id,
        "session_id": "session_idem"
    }

    # First add
    r1 = client.post("/add", json=payload)
    assert r1.status_code == 200
    assert r1.json()["success"] is True

    # Duplicate add
    r2 = client.post("/add", json=payload)
    assert r2.status_code == 200
    assert r2.json()["success"] is True
    assert r2.json()["request_id"] == req_id

    # Verify no duplicate stored
    res = client.post("/search", json={"query": fact, "user_id": user_id, "top_k": 10})
    matches = [m for m in res.json()["data"] if fact in m["content"]]
    assert len(matches) == 1, f"Idempotency violated: found {len(matches)} duplicates."
