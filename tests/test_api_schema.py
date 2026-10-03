import pytest
from fastapi.testclient import TestClient
from axiom_mem.server import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_health_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_add_response_exact_echo(client):
    req_id = "eval:run_test:req_001"
    user_id = "eval:run_test:user_001"
    sess_id = "eval:run_test:session_001"

    payload = {
        "request_id": req_id,
        "messages": [
            {"role": "user", "timestamp": 1704067200000, "content": "Fact one."}
        ],
        "user_id": user_id,
        "session_id": sess_id
    }
    resp = client.post("/add", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["request_id"] == req_id
    assert body["user_id"] == user_id
    assert body["session_id"] == sess_id


def test_search_response_schema_and_empty(client):
    user_id = "eval:run_test:empty_user_999"
    payload = {
        "query": "anything",
        "user_id": user_id,
        "top_k": 10
    }
    resp = client.post("/search", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert isinstance(body["data"], list)
    assert body["data"] == []


def test_multimodal_content_part_handling(client):
    user_id = "eval:mm_user"
    req_id = "eval:mm_req_01"
    payload = {
        "request_id": req_id,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "This is multimodal text part."},
                    "Raw string part"
                ]
            }
        ],
        "user_id": user_id,
        "session_id": "mm_sess"
    }
    resp = client.post("/add", json=payload)
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    s_resp = client.post("/search", json={
        "query": "multimodal text part",
        "user_id": user_id,
        "top_k": 5
    })
    assert s_resp.status_code == 200
    hits = s_resp.json()["data"]
    assert len(hits) > 0
    assert "multimodal text part" in hits[0]["content"]
