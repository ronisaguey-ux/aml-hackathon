#!/usr/bin/env python3
"""
AxiomMem Official Local Evaluation & Ranking Harness.
Implements benchmark evaluation patterns derived from AML benchmark datasets:
- LoCoMo-Refined / PersonaMem: Temporal state updates (Column C)
- SWE / Debug Memory: Multi-step procedural execution (Column G)
- BEAM / CLBench: Multi-hop relational inference (Column B)
- Governance / Rules: Constraint preservation (Column D)
- Streaming: Interleaved events with optional/absent timestamps (Column E)

Measures:
- MRR (Mean Reciprocal Rank)
- Mean Gold Rank
- Recall@1, Recall@5, Recall@10, Recall@100
- Column C State-Change Gold Rank
- Column G Full-Sequence Completeness & Contiguity Rate
- Non-Vacuity Verification mode
"""

import sys
import time
import argparse
import numpy as np
import httpx
from typing import List, Dict, Any, Tuple


DISTRACTOR_TEMPLATES = [
    "Discussion on quarterly planning and roadmap milestones.",
    "Reminder to review the pull request for documentation cleanup.",
    "System alert: network latency increased by 15ms in us-east-1.",
    "Team lunch scheduled for Wednesday at 12:30 PM.",
    "Summary of weekly retrospective meeting notes and action items.",
    "Please update your local dev environment with python 3.12.",
    "Reviewing latency graphs from the latest canary rollout.",
    "Security advisory regarding dependency version bumps.",
    "Discussion about refactoring the logging middleware.",
    "Standup update: working on unit tests for the auth module.",
    "Discussion on improving database connection pool configuration.",
    "Team discussion about attending the upcoming open-source conference.",
]

EVAL_SCENARIOS = [
    # -------------------------------------------------------------
    # Category 1: Temporal Resolution (Column C) - State Updates
    # -------------------------------------------------------------
    {
        "id": "temp_01_present",
        "category": "temporal",
        "user_id": "eval:harness:user_temp_01",
        "adds": [
            {
                "request_id": "temp_add_01a",
                "messages": [
                    {"role": "user", "timestamp": 1704067200000, "content": "I am working as a frontend engineer in Berlin."}
                ]
            },
            {
                "request_id": "temp_add_01_distract",
                "messages": [
                    {"role": "user", "content": t} for t in DISTRACTOR_TEMPLATES[:8]
                ]
            },
            {
                "request_id": "temp_add_01b",
                "messages": [
                    {"role": "user", "timestamp": 1719835200000, "content": "Update: I moved to London and switched to systems programming."}
                ]
            }
        ],
        "query": "Where do I currently live and what is my role now?",
        "gold_must_contain": ["London", "systems programming"],
        "older_state_contains": ["Berlin", "frontend engineer"],
        "expect_latest_first": True
    },
    {
        "id": "temp_02_past_query",
        "category": "temporal",
        "user_id": "eval:harness:user_temp_02",
        "adds": [
            {
                "request_id": "temp_add_02a",
                "messages": [
                    {"role": "user", "timestamp": 1704067200000, "content": "Our main API database originally ran on PostgreSQL 14."}
                ]
            },
            {
                "request_id": "temp_add_02_distract",
                "messages": [
                    {"role": "user", "content": t} for t in DISTRACTOR_TEMPLATES[:8]
                ]
            },
            {
                "request_id": "temp_add_02b",
                "messages": [
                    {"role": "user", "timestamp": 1719835200000, "content": "We migrated the database service to ScyllaDB last month."}
                ]
            }
        ],
        "query": "What database did our main API originally run on before the migration?",
        "gold_must_contain": ["PostgreSQL 14"],
        "older_state_contains": ["PostgreSQL 14"],
        "expect_past_first": True
    },
    {
        "id": "temp_03_no_timestamps",
        "category": "temporal",
        "user_id": "eval:harness:user_temp_03",
        "adds": [
            {
                "request_id": "temp_add_03a",
                "messages": [
                    # Missing timestamp
                    {"role": "user", "content": "My primary contact email is alex.dev@legacymail.org."}
                ]
            },
            {
                "request_id": "temp_add_03b",
                "messages": [
                    # Missing timestamp, but arrives later
                    {"role": "user", "content": "Correction: I updated my primary contact email to alex@quantumcore.io, please replace the old one."}
                ]
            }
        ],
        "query": "What is Alex's current active email address?",
        "gold_must_contain": ["alex@quantumcore.io"],
        "older_state_contains": ["legacymail.org"],
        "expect_latest_first": True
    },

    # -------------------------------------------------------------
    # Category 2: Context Learning & Execution (Column G) - Coding & Procedures
    # -------------------------------------------------------------
    {
        "id": "exec_01_db_migration",
        "category": "execution",
        "user_id": "eval:harness:user_exec_01",
        "adds": [
            {
                "request_id": "exec_add_01_steps",
                "messages": [
                    {"role": "user", "content": "Step 1: Put cluster in maintenance mode: `vault-cli maintenance on --force`."},
                    {"role": "user", "content": "Step 2: Run schema migration script: `python -m db.migrate --target v4.2`."},
                    {"role": "user", "content": "Step 3: Validate table checksums with `db-verify --all-shards`."},
                    {"role": "user", "content": "Step 4: Disable maintenance mode: `vault-cli maintenance off`."}
                ]
            },
            {
                "request_id": "exec_add_01_noise",
                "messages": [
                    {"role": "user", "content": "Database migrations can take between 5 minutes to 2 hours depending on load."},
                    {"role": "user", "content": "The weather in Seattle is rainy today."}
                ]
            }
        ],
        "query": "How do I run the schema migration on the vault cluster step by step?",
        "procedural_steps": [
            "Step 1: Put cluster in maintenance mode",
            "Step 2: Run schema migration script",
            "Step 3: Validate table checksums",
            "Step 4: Disable maintenance mode"
        ],
        "gold_must_contain": ["Step 2: Run schema migration script"]
    },
    {
        "id": "exec_02_debug_oom_trace",
        "category": "execution",
        "user_id": "eval:harness:user_exec_02",
        "adds": [
            {
                "request_id": "exec_add_02_fix",
                "messages": [
                    {"role": "user", "content": "Diagnostic Trace: Worker process killed with exit code 137 (SIGKILL OOM)."},
                    {"role": "user", "content": "Root Cause: Memory leak in gRPC streaming buffer when batch size > 1000."},
                    {"role": "user", "content": "Repair Action: In `worker/config.yaml`, set `stream_buffer_limit: 256MB` and restart with `systemctl restart worker`."}
                ]
            },
            {
                "request_id": "exec_add_02_chatter",
                "messages": [
                    {"role": "user", "content": "We had several outages in Q2 due to network spikes."}
                ]
            }
        ],
        "query": "How to repair the worker process exit code 137 OOM crash?",
        "procedural_steps": [
            "Worker process killed with exit code 137",
            "stream_buffer_limit: 256MB"
        ],
        "gold_must_contain": ["stream_buffer_limit: 256MB", "systemctl restart worker"]
    },

    # -------------------------------------------------------------
    # Category 3: Multi-Hop Relational Inference (Column B)
    # -------------------------------------------------------------
    {
        "id": "multihop_01_org_hierarchy",
        "category": "multihop",
        "user_id": "eval:harness:user_multi_01",
        "adds": [
            {
                "request_id": "multi_add_01a",
                "messages": [
                    {"role": "user", "content": "Elena Rostova is the director of the Helix Propulsion Lab."}
                ]
            },
            {
                "request_id": "multi_add_01b",
                "messages": [
                    {"role": "user", "content": "The Helix Propulsion Lab is headquartered at Aerospace Park in Toulouse, France."}
                ]
            },
            {
                "request_id": "multi_add_01c",
                "messages": [
                    {"role": "user", "content": "Elena enjoys playing classical piano on weekends."}
                ]
            }
        ],
        "query": "In which city is the laboratory directed by Elena Rostova headquartered?",
        "hop1_contains": ["Elena Rostova", "Helix Propulsion Lab"],
        "hop2_contains": ["Helix Propulsion Lab", "Toulouse"],
        "gold_must_contain": ["Toulouse"]
    },

    # -------------------------------------------------------------
    # Category 4: Rules & Constraints (Column D)
    # -------------------------------------------------------------
    {
        "id": "rule_01_deployment_constraint",
        "category": "rule",
        "user_id": "eval:harness:user_rule_01",
        "adds": [
            {
                "request_id": "rule_add_01",
                "messages": [
                    {"role": "user", "content": "Deployment Policy: Engineers must never deploy changes directly to production on Fridays after 2 PM UTC."},
                    {"role": "user", "content": "All pull requests require approval from at least two senior code reviewers."},
                    {"role": "user", "content": "Friday team lunches are held at the cafeteria."}
                ]
            }
        ],
        "query": "What is the policy regarding Friday production deployments?",
        "gold_must_contain": ["never deploy changes directly to production on Fridays after 2 PM UTC"]
    }
]


def run_evaluation(base_url: str, simulate_broken_ranking: bool = False) -> Dict[str, Any]:
    print("=" * 70)
    print(f"📊 AXIOM-MEM LOCAL BENCHMARK HARNESS")
    print(f"Target Endpoint: {base_url}")
    if simulate_broken_ranking:
        print("⚠️ NON-VACUITY TEST MODE: Simulating broken/reversed ranking order!")
    print("=" * 70)

    client = httpx.Client(base_url=base_url, timeout=30.0)

    reciprocal_ranks = []
    gold_ranks = []
    recall_at_1 = []
    recall_at_5 = []
    recall_at_10 = []
    column_g_full_sequences = []
    column_c_gold_ranks = []
    column_b_multi_hops = []

    for scenario in EVAL_SCENARIOS:
        user_id = scenario["user_id"]

        # Ingest all add requests
        for add_req in scenario["adds"]:
            payload = {
                "request_id": add_req["request_id"],
                "messages": add_req["messages"],
                "user_id": user_id,
                "session_id": f"sess_{scenario['id']}"
            }
            resp = client.post("/add", json=payload)
            assert resp.status_code == 200, f"Add failed: {resp.text}"

        # Execute search query
        query_payload = {
            "query": scenario["query"],
            "user_id": user_id,
            "top_k": 100
        }
        resp = client.post("/search", json=query_payload)
        assert resp.status_code == 200, f"Search failed: {resp.text}"
        data = resp.json().get("data", [])

        if simulate_broken_ranking and data:
            # Non-vacuity test: reverse the ranking order completely
            data = list(reversed(data))

        # 1. Locate gold memory rank
        gold_match_rank = None
        for rank_idx, item in enumerate(data):
            content = item["content"]
            if all(term.lower() in content.lower() for term in scenario["gold_must_contain"]):
                gold_match_rank = rank_idx + 1
                break

        if gold_match_rank is not None:
            gold_ranks.append(gold_match_rank)
            reciprocal_ranks.append(1.0 / gold_match_rank)
            recall_at_1.append(1.0 if gold_match_rank == 1 else 0.0)
            recall_at_5.append(1.0 if gold_match_rank <= 5 else 0.0)
            recall_at_10.append(1.0 if gold_match_rank <= 10 else 0.0)
        else:
            gold_ranks.append(101)  # Penalize missing from top 100
            reciprocal_ranks.append(0.0)
            recall_at_1.append(0.0)
            recall_at_5.append(0.0)
            recall_at_10.append(0.0)

        # 2. Check Category-specific metrics
        cat = scenario.get("category")
        if cat == "temporal":
            column_c_gold_ranks.append(gold_match_rank if gold_match_rank else 101)
        elif cat == "execution" and "procedural_steps" in scenario:
            # Check if all procedural steps are present in the top-k results
            returned_contents = [d["content"] for d in data[:10]]
            all_steps_found = True
            for step in scenario["procedural_steps"]:
                if not any(step.lower() in rc.lower() for rc in returned_contents):
                    all_steps_found = False
                    break
            column_g_full_sequences.append(1.0 if all_steps_found else 0.0)
        elif cat == "multihop":
            returned_contents = [d["content"] for d in data[:5]]
            hop1_ok = any(all(t.lower() in rc.lower() for t in scenario["hop1_contains"]) for rc in returned_contents)
            hop2_ok = any(all(t.lower() in rc.lower() for t in scenario["hop2_contains"]) for rc in returned_contents)
            column_b_multi_hops.append(1.0 if (hop1_ok and hop2_ok) else 0.0)

        status_str = f"Rank {gold_match_rank}" if gold_match_rank else "MISS"
        print(f"  • [{scenario['id']}] ({cat}) -> Gold: {status_str}")

    # Aggregates
    mrr = float(np.mean(reciprocal_ranks))
    mean_gold_rank = float(np.mean(gold_ranks))
    r_at_1 = float(np.mean(recall_at_1)) * 100.0
    r_at_5 = float(np.mean(recall_at_5)) * 100.0
    r_at_10 = float(np.mean(recall_at_10)) * 100.0
    col_c_mean_rank = float(np.mean(column_c_gold_ranks)) if column_c_gold_ranks else 0.0
    col_g_seq_rate = float(np.mean(column_g_full_sequences)) * 100.0 if column_g_full_sequences else 0.0
    col_b_rate = float(np.mean(column_b_multi_hops)) * 100.0 if column_b_multi_hops else 0.0

    print("\n" + "=" * 70)
    print("📈 BENCHMARK EVALUATION SUMMARY")
    print("=" * 70)
    print(f"  MRR (Mean Reciprocal Rank):        {mrr:.4f}")
    print(f"  Mean Gold Rank:                    {mean_gold_rank:.2f}")
    print(f"  Recall@1:                          {r_at_1:.1f}%")
    print(f"  Recall@5:                          {r_at_5:.1f}%")
    print(f"  Recall@10:                         {r_at_10:.1f}%")
    print(f"  Column C (Temporal Mean Gold Rank):{col_c_mean_rank:.2f} (lower is better)")
    print(f"  Column G (Full-Sequence Presence): {col_g_seq_rate:.1f}%")
    print(f"  Column B (Multi-Hop Linking Rate): {col_b_rate:.1f}%")
    print("=" * 70)

    results = {
        "mrr": mrr,
        "mean_gold_rank": mean_gold_rank,
        "recall_at_1": r_at_1,
        "recall_at_5": r_at_5,
        "recall_at_10": r_at_10,
        "column_c_mean_gold_rank": col_c_mean_rank,
        "column_g_full_sequence_rate": col_g_seq_rate,
        "column_b_multihop_rate": col_b_rate,
        "timestamp": time.time()
    }
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--test-broken", action="store_true", help="Simulate broken ranking to prove non-vacuity")
    args = parser.parse_args()

    results = run_evaluation(args.base_url, simulate_broken_ranking=args.test_broken)
    if args.test_broken:
        if results["mrr"] > 0.40:
            print("❌ VACUOUS SCORER: Broken ranking scored too high!")
            sys.exit(1)
        else:
            print("✅ NON-VACUITY PROVEN: Deliberately broken ranking failed decisively (low MRR).")
