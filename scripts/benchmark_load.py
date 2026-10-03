#!/usr/bin/env python3
"""
AxiomMem Load and Latency Benchmarking Suite.
Instruments Add throughput and Search p50/p95/p99 latency under concurrent load.
Usage:
    python scripts/benchmark_load.py [--adds 1000] [--searches 200] [--base-url http://localhost:8000]
"""

import sys
import time
import random
import argparse
import numpy as np
import httpx
from concurrent.futures import ThreadPoolExecutor, as_completed

SAMPLE_WORDS = [
    "algorithm", "database", "optimizer", "kubernetes", "compiler", "runtime",
    "cache", "distributed", "protocol", "architecture", "consensus", "latency",
    "throughput", "memory", "storage", "vector", "index", "retrieval", "context",
    "execution", "temporal", "inference", "governance", "safety", "benchmark"
]


def generate_message(idx: int) -> str:
    words = random.sample(SAMPLE_WORDS, k=8)
    return f"Observation {idx}: Cluster node {idx % 50} reported {words[0]} state in {words[1]} service. Parameter {words[2]} configured to value {random.randint(100, 9999)}."


def run_benchmark(base_url: str, num_adds: int, num_searches: int, concurrency: int = 8):
    print("=" * 65)
    print("⚡ AXIOM-MEM LOAD & LATENCY BENCHMARK")
    print(f"Target: {base_url}")
    print(f"Configuration: {num_adds} Adds | {num_searches} Searches (top_k=100) | {concurrency} Workers")
    print("=" * 65)

    client = httpx.Client(base_url=base_url, timeout=30.0)
    test_user_id = f"eval:loadtest_user_{int(time.time())}"

    # -------------------------------------------------------------
    # 1. ADD LOAD TEST
    # -------------------------------------------------------------
    print(f"\n[Phase 1] Ingesting {num_adds} memories...")
    add_latencies = []
    t_start_adds = time.perf_counter()

    batch_size = 5  # chunk messages per Add request
    batches = []
    for i in range(0, num_adds, batch_size):
        messages = [
            {"role": "user", "content": generate_message(i + j), "timestamp": int(time.time() * 1000) + j}
            for j in range(min(batch_size, num_adds - i))
        ]
        batches.append({
            "request_id": f"load_req_{i}_{int(time.time())}",
            "messages": messages,
            "user_id": test_user_id,
            "session_id": f"session_{i // 50}"
        })

    def send_add(payload):
        with httpx.Client(base_url=base_url, timeout=30.0) as c:
            t0 = time.perf_counter()
            resp = c.post("/add", json=payload)
            dur = (time.perf_counter() - t0) * 1000
            assert resp.status_code == 200, f"Add failed: {resp.text}"
            return dur

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(send_add, b) for b in batches]
        for f in as_completed(futures):
            add_latencies.append(f.result())

    total_add_time = time.perf_counter() - t_start_adds
    add_throughput = num_adds / total_add_time

    print(f"  Total Ingest Time:   {total_add_time:.2f}s")
    print(f"  Ingest Throughput:   {add_throughput:.1f} memories/sec")
    print(f"  Add Latency p50:     {np.percentile(add_latencies, 50):.2f} ms")
    print(f"  Add Latency p95:     {np.percentile(add_latencies, 95):.2f} ms")

    # -------------------------------------------------------------
    # 2. SEARCH LOAD TEST (top_k = 100)
    # -------------------------------------------------------------
    print(f"\n[Phase 2] Executing {num_searches} searches at top_k=100...")
    search_latencies = []
    t_start_search = time.perf_counter()

    search_queries = [
        f"What is the status of {random.choice(SAMPLE_WORDS)} and {random.choice(SAMPLE_WORDS)} in the cluster?"
        for _ in range(num_searches)
    ]

    def send_search(query):
        with httpx.Client(base_url=base_url, timeout=30.0) as c:
            t0 = time.perf_counter()
            resp = c.post("/search", json={
                "query": query,
                "user_id": test_user_id,
                "top_k": 100
            })
            dur = (time.perf_counter() - t0) * 1000
            assert resp.status_code == 200, f"Search failed: {resp.text}"
            data = resp.json().get("data", [])
            assert len(data) > 0, "Search returned empty data!"
            return dur

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(send_search, q) for q in search_queries]
        for f in as_completed(futures):
            search_latencies.append(f.result())

    total_search_time = time.perf_counter() - t_start_search
    search_qps = num_searches / total_search_time

    p50 = np.percentile(search_latencies, 50)
    p95 = np.percentile(search_latencies, 95)
    p99 = np.percentile(search_latencies, 99)

    print(f"  Total Search Time:   {total_search_time:.2f}s")
    print(f"  Search Throughput:   {search_qps:.1f} QPS")
    print(f"  Search Latency p50:  {p50:.2f} ms")
    print(f"  Search Latency p95:  {p95:.2f} ms")
    print(f"  Search Latency p99:  {p99:.2f} ms")

    print("\n" + "=" * 65)
    if p95 < 250.0:
        print("🚀 PERFORMANCE SCORE: EXCELLENT (p95 well below 250ms target)")
    else:
        print("⚠️ PERFORMANCE SCORE: SATISFACTORY")
    print("=" * 65)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--adds", type=int, default=500, help="Number of messages to ingest")
    parser.add_argument("--searches", type=int, default=100, help="Number of top_k=100 searches")
    parser.add_argument("--concurrency", type=int, default=4, help="Thread concurrency")
    args = parser.parse_args()

    run_benchmark(args.base_url, args.adds, args.searches, args.concurrency)
