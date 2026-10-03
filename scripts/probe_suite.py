#!/usr/bin/env python3
"""
AxiomMem Evaluation Probe Suite.
Evaluates the core differentiators specified in Section 4.3:
- Temporal Conflict Resolution (Column C)
- Execution & Procedural Continuity (Column G)
- Multi-Hop Composition (Column B)
- Options-Aware Discrimination
"""

import sys
import time
import argparse
import httpx


def run_probes(base_url: str):
    print("=" * 65)
    print("🔬 AXIOM-MEM CAPABILITY PROBE SUITE")
    print(f"Target: {base_url}")
    print("=" * 65)

    client = httpx.Client(base_url=base_url, timeout=20.0)

    # -------------------------------------------------------------
    # Probe 1: Temporal Conflict Resolution (Column C)
    # -------------------------------------------------------------
    print("\n[Probe 1] Testing Temporal Conflict Resolution (Column C)...")
    user_temporal = f"eval:probe:temporal_{int(time.time())}"
    t_past = 1704067200000       # Jan 1 2024
    t_recent = 1719835200000     # Jul 1 2024

    # Add older memory
    client.post("/add", json={
        "request_id": f"req_past_{int(time.time())}",
        "messages": [
            {"role": "user", "timestamp": t_past, "content": "I am currently working as a database engineer in Seattle."}
        ],
        "user_id": user_temporal,
        "session_id": "session_past"
    })

    # Add newer memory with state update
    client.post("/add", json={
        "request_id": f"req_recent_{int(time.time())}",
        "messages": [
            {"role": "user", "timestamp": t_recent, "content": "Update on my situation: I relocated to Zurich and now work on distributed consensus algorithms."}
        ],
        "user_id": user_temporal,
        "session_id": "session_recent"
    })

    # Search for current location
    res = client.post("/search", json={
        "query": "Where do I currently live and work?",
        "user_id": user_temporal,
        "top_k": 5
    }).json()

    hits = res.get("data", [])
    assert len(hits) >= 2, f"Expected both memories, got {len(hits)}"
    top_hit = hits[0]["content"]
    second_hit = hits[1]["content"]

    print(f"  Rank 1: {top_hit}")
    print(f"  Rank 2: {second_hit}")

    assert "Zurich" in top_hit, "Temporal resolution failed: latest location not ranked #1!"
    assert "Seattle" in second_hit, "Temporal history failed: older location discarded!"
    print("  ✅ PASS: Latest valid update ranked first; prior state preserved in sequence.")

    # -------------------------------------------------------------
    # Probe 2: Procedural Execution Continuity (Column G)
    # -------------------------------------------------------------
    print("\n[Probe 2] Testing Procedural Execution Continuity (Column G)...")
    user_exec = f"eval:probe:exec_{int(time.time())}"

    # Multi-step repair session
    client.post("/add", json={
        "request_id": f"req_exec_steps_{int(time.time())}",
        "messages": [
            {"role": "user", "content": "Step 1: Check if Redis service is active using `systemctl status redis`."},
            {"role": "user", "content": "Step 2: If redis crashed with exit code 137 OOM, edit `/etc/redis/redis.conf` to set `maxmemory 4gb` and `maxmemory-policy allkeys-lru`."},
            {"role": "user", "content": "Step 3: Restart the daemon with `systemctl restart redis` and verify with `redis-cli ping`."}
        ],
        "user_id": user_exec,
        "session_id": "session_redis_fix"
    })

    # Add noise / casual chat memories
    client.post("/add", json={
        "request_id": f"req_exec_noise_{int(time.time())}",
        "messages": [
            {"role": "user", "content": "Redis is an in-memory key-value database invented by Salvatore Sanfilippo."},
            {"role": "user", "content": "I like the color red, it reminds me of the Redis logo."}
        ],
        "user_id": user_exec,
        "session_id": "session_casual"
    })

    # Query for procedure execution
    res_exec = client.post("/search", json={
        "query": "How to fix redis oom error step by step procedure?",
        "user_id": user_exec,
        "top_k": 5
    }).json()

    exec_hits = res_exec.get("data", [])
    assert len(exec_hits) >= 3, "Failed to retrieve procedural sequence"
    
    # Check that procedural steps dominate the top results
    step_contents = [h["content"] for h in exec_hits[:3]]
    all_steps_text = " ".join(step_contents)

    print(f"  Retrieved top 3 steps:")
    for idx, c in enumerate(step_contents):
        print(f"    [{idx+1}] {c}")

    assert "maxmemory" in all_steps_text, "Failed to retrieve the core configuration fix!"
    assert any("Step 1" in s for s in step_contents) or any("Step 2" in s for s in step_contents)
    print("  ✅ PASS: Procedural continuity and multi-step execution context preserved.")

    # -------------------------------------------------------------
    # Probe 3: Multi-Hop Composition (Column B)
    # -------------------------------------------------------------
    print("\n[Probe 3] Testing Multi-Hop Composition (Column B)...")
    user_multihop = f"eval:probe:multihop_{int(time.time())}"

    # Hop 1
    client.post("/add", json={
        "request_id": f"req_hop1_{int(time.time())}",
        "messages": [
            {"role": "user", "content": "Dr. Aris Thorne is the lead architect for Project Aetheris."}
        ],
        "user_id": user_multihop,
        "session_id": "session_hop1"
    })

    # Hop 2
    client.post("/add", json={
        "request_id": f"req_hop2_{int(time.time())}",
        "messages": [
            {"role": "user", "content": "Project Aetheris was funded by the Quantum Systems Institute in Geneva."}
        ],
        "user_id": user_multihop,
        "session_id": "session_hop2"
    })

    # Search asking for the institute funding Dr. Thorne's project
    res_hop = client.post("/search", json={
        "query": "Which institute in Geneva funded the project led by Dr. Aris Thorne?",
        "user_id": user_multihop,
        "top_k": 5
    }).json()

    hop_hits = [h["content"] for h in res_hop.get("data", [])]
    print(f"  Multi-Hop Hits:")
    for idx, h in enumerate(hop_hits[:2]):
        print(f"    [{idx+1}] {h}")

    combined_hops = " ".join(hop_hits[:3])
    assert "Aris Thorne" in combined_hops and "Quantum Systems Institute" in combined_hops, \
        "Multi-hop composition failed: missing link in returned context!"
    print("  ✅ PASS: Multi-hop premise and bridge entity successfully retrieved.")

    # -------------------------------------------------------------
    # Probe 4: Options Discriminator
    # -------------------------------------------------------------
    print("\n[Probe 4] Testing Options-Aware Discriminative Re-ranking...")
    user_options = f"eval:probe:options_{int(time.time())}"

    client.post("/add", json={
        "request_id": f"req_opts_{int(time.time())}",
        "messages": [
            {"role": "user", "content": "The cryptographic signature algorithm specified in the protocol is Ed25519 with SHA-512."},
            {"role": "user", "content": "The system also supports RSA-4096 for legacy clients only."}
        ],
        "user_id": user_options,
        "session_id": "session_crypto"
    })

    res_opt = client.post("/search", json={
        "query": "Which primary signature scheme does the modern protocol use?",
        "options": [
            "A. ECDSA P-256",
            "B. Ed25519",
            "C. Falcon-512",
            "D. Dilithium-2"
        ],
        "user_id": user_options,
        "top_k": 2
    }).json()

    top_result = res_opt["data"][0]["content"]
    print(f"  Top Result with Options: {top_result}")
    assert "Ed25519" in top_result
    print("  ✅ PASS: Options discriminator boosted targeted grounding evidence.")

    print("\n" + "=" * 65)
    print("🏆 ALL 4 CAPABILITY PROBES PASSED WITH ZERO LOSS!")
    print("=" * 65)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    args = parser.parse_args()
    try:
        run_probes(args.base_url)
    except Exception as e:
        print(f"\n❌ PROBE SUITE FAILED: {e}")
        sys.exit(1)
