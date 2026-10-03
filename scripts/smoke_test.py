#!/usr/bin/env python3
"""
AxiomMem Official Smoke Test Suite.
Verifies all AML API invariants and schema compliance locally or against remote endpoint.
Usage:
    python scripts/smoke_test.py [--base-url http://localhost:8000]
"""

import sys
import time
import argparse
import httpx


def run_smoke_test(base_url: str):
    print("=" * 60)
    print(f"🧪 Running AML Smoke Tests against {base_url}")
    print("=" * 60)

    client = httpx.Client(base_url=base_url, timeout=15.0)

    # 1. Health check
    print("[1/6] Testing Health Endpoint...")
    resp = client.get("/health")
    assert resp.status_code == 200, f"Health check failed: {resp.status_code} {resp.text}"
    health_data = resp.json()
    assert health_data.get("status") == "ok", f"Health status not ok: {health_data}"
    print("  ✅ Health endpoint OK")

    # 2. Add Endpoint & Immediate Visibility
    print("[2/6] Testing Add & Immediate Visibility Invariant...")
    test_user_id = f"eval:smoke_run:user_{int(time.time())}"
    test_session_id = "eval:smoke_run:session_0"
    test_req_id = f"eval:smoke_run:req_{int(time.time())}"
    timestamp_ms = int(time.time() * 1000)

    secret_fact = "The secret deployment code for server cluster is DELTA-9418."

    add_payload = {
        "request_id": test_req_id,
        "messages": [
            {
                "role": "user",
                "timestamp": timestamp_ms,
                "content": f"Please remember: {secret_fact}"
            }
        ],
        "user_id": test_user_id,
        "session_id": test_session_id
    }

    t0 = time.perf_counter()
    add_resp = client.post("/add", json=add_payload)
    add_latency = (time.perf_counter() - t0) * 1000
    assert add_resp.status_code == 200, f"Add failed: {add_resp.status_code} {add_resp.text}"
    add_data = add_resp.json()

    # Exact field echo verification
    assert add_data.get("success") is True, f"Success not true: {add_data}"
    assert add_data.get("request_id") == test_req_id, f"request_id mismatch: {add_data}"
    assert add_data.get("user_id") == test_user_id, f"user_id mismatch: {add_data}"
    assert add_data.get("session_id") == test_session_id, f"session_id mismatch: {add_data}"
    print(f"  ✅ Add successful ({add_latency:.2f} ms). Field echo exact.")

    # Immediate search
    t0 = time.perf_counter()
    search_payload = {
        "query": "What is the secret deployment code?",
        "user_id": test_user_id,
        "top_k": 10
    }
    search_resp = client.post("/search", json=search_payload)
    search_latency = (time.perf_counter() - t0) * 1000
    assert search_resp.status_code == 200, f"Search failed: {search_resp.status_code} {search_resp.text}"
    search_data = search_resp.json()
    assert "data" in search_data, "Response missing required 'data' field"
    assert len(search_data["data"]) > 0, "Immediate visibility failed: no memories found!"
    top_hit = search_data["data"][0]
    assert secret_fact in top_hit["content"], f"Fact not found in top hit: {top_hit}"
    assert "id" in top_hit and top_hit["id"]
    assert "created_at" in top_hit and top_hit["created_at"]
    print(f"  ✅ Immediate visibility verified ({search_latency:.2f} ms). Found top hit: {top_hit['id']}")

    # 3. Idempotency on request_id
    print("[3/6] Testing Idempotency on request_id...")
    add_resp_retry = client.post("/add", json=add_payload)
    assert add_resp_retry.status_code == 200
    retry_data = add_resp_retry.json()
    assert retry_data.get("success") is True
    assert retry_data.get("request_id") == test_req_id

    # Count search results should not duplicate
    search_resp_dup = client.post("/search", json=search_payload)
    dup_data = search_resp_dup.json()
    matching_hits = [m for m in dup_data["data"] if secret_fact in m["content"]]
    assert len(matching_hits) == 1, f"Idempotency failure: found {len(matching_hits)} duplicates!"
    print("  ✅ Idempotency strictly maintained without duplicate records.")

    # 4. User Isolation Boundary
    print("[4/6] Testing Absolute User Isolation...")
    other_user_id = f"eval:smoke_run:different_user_{int(time.time())}"
    isolation_resp = client.post("/search", json={
        "query": "What is the secret deployment code?",
        "user_id": other_user_id,
        "top_k": 10
    })
    assert isolation_resp.status_code == 200
    iso_data = isolation_resp.json()
    assert "data" in iso_data
    assert isinstance(iso_data["data"], list)
    assert len(iso_data["data"]) == 0, f"Isolation failure! Leaked memories: {iso_data['data']}"
    print("  ✅ Isolation verified: foreign user sees empty array [] with zero leaks.")

    # 5. Empty Results Schema ('data' must never be omitted)
    print("[5/6] Testing Empty Query / Zero Matches Schema...")
    nonexistent_user = f"eval:nobody_{int(time.time())}"
    empty_resp = client.post("/search", json={
        "query": "Completely non-existent memory query xyz12345",
        "user_id": nonexistent_user,
        "top_k": 50
    })
    assert empty_resp.status_code == 200
    empty_data = empty_resp.json()
    assert "data" in empty_data, "'data' field omitted on empty result!"
    assert empty_data["data"] == [], f"Expected empty list, got: {empty_data['data']}"
    print("  ✅ Empty query schema compliant (data: []).")

    # 6. Options-aware Search
    print("[6/6] Testing Multiple-Choice Options-aware Ranking...")
    # Add a memory about programming language versions
    client.post("/add", json={
        "request_id": f"eval:options_req_{int(time.time())}",
        "messages": [
            {"role": "user", "content": "Our production backend uses Python 3.12 and FastAPI."}
        ],
        "user_id": test_user_id,
        "session_id": test_session_id
    })

    options_search_resp = client.post("/search", json={
        "query": "Which version is our production backend running?",
        "options": ["A. Python 3.10", "B. Python 3.12", "C. Node.js 18", "D. Ruby 3.2"],
        "user_id": test_user_id,
        "top_k": 10
    })
    assert options_search_resp.status_code == 200
    opt_data = options_search_resp.json()
    assert len(opt_data["data"]) > 0
    top_content = opt_data["data"][0]["content"]
    assert "Python 3.12" in top_content
    # Confirm no fake option content is returned as memory
    for m in opt_data["data"]:
        assert not m["content"].startswith("B. Python 3.12"), "Option text illegally returned as memory!"
    print("  ✅ Options-aware ranking passed. Pure memory grounded.")

    print("=" * 60)
    print("🎉 ALL SMOKE TESTS PASSED! System is ready for AML evaluation queue.")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    args = parser.parse_args()
    try:
        run_smoke_test(args.base_url)
    except Exception as e:
        print(f"\n❌ SMOKE TEST FAILED: {e}")
        sys.exit(1)
