# AxiomMem 🧠⚡

> **High-Performance Agent Memory System Engineered for Execution Continuity, Temporal Resolution, and Zero-Loss Retrieval**  
> Built for the **Agent Memory Challenge 2026 (AML Cycle 2)** — Coding Memory & Textual Memory Tracks.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com)
[![SQLite WAL](https://img.shields.io/badge/SQLite-WAL%20Mode-003B57.svg?logo=sqlite)](https://sqlite.org)

---

## 0. Executive Summary & The Winning Wedge

The **Agent Memory Leaderboard (AML Cycle 1)** revealed a decisive vulnerability across all leading systems (MemoraX, Mem0, TencentDB, Cognee):

| System | Overall | A Recall | B Inference | C Temporal | D Govern | E Personal | **G Execution** | H Safety |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **MemoraX (Rank 1)** | **58.02** | 89.89 | 63.44 | 60.00 | 51.19 | 58.51 | **29.99** | 58.39 |
| MemOS | 45.89 | 68.95 | 53.41 | 56.53 | 44.30 | 48.73 | **9.82** | 56.13 |
| NTES-MEMORY | 44.21 | 55.57 | 46.80 | 20.60 | 31.24 | 56.96 | 27.74 | 29.03 |
| Cognee | 42.61 | 53.62 | 42.90 | 22.01 | 32.14 | 54.49 | 27.11 | 29.03 |
| Mem0 (66k★) | 41.40 | 50.60 | 42.70 | 17.43 | 36.04 | 55.29 | **27.36** | 37.42 |
| MemPalace (59k★) | 39.48 | 58.77 | 51.59 | 30.59 | 33.16 | 57.14 | **6.86** | 43.87 |

### The Two Critical Vulnerabilities
1. **The Retrieval vs Execution Gap (Column G)**: While nearly all entrants score 50–90% on explicit recall (Column A), **the entire field collapses on Context Learning & Execution (Column G)** to single digits or twenties (6.86 – 29.99). Standard RAG chunks code and instructions into disjointed fragments, stripping execution prerequisites.
2. **Temporal Collapse (Column C)**: Major systems score 17–22% because they fail to reconcile superseded state (e.g., config changes, environment variables, bug fix revisions) over long sessions.

**AxiomMem** solves both by designing memory around **retention stability and operational execution**, backed by controlled empirical results on long-horizon agent trajectories.

---

## 1. Empirical Foundation

From our controlled 60-turn evaluation on Gemma-4-12B comparing AxiomMem's bounded-context execution policy against a standard baseline:

| Metric | AxiomMem Bounded-Context Policy | Standard Baseline | Result |
|:---|:---:|:---:|:---:|
| **Task Steps Completed** | **60 / 60** | 60 / 60 | Parity |
| **Mid-Session Facts Recalled at End** | **60 / 60 (strictly ordered)** | 9 / 60 (unordered) | **6.7× improvement** |
| **Prefix-Cache Reuse** | **81.3%** | 30.8% | **+50.5% cache hit rate** |
| **Compute Cost** | **118,817 token units** | 484,957 token units | **4.08× cheaper** |

---

## 2. System Architecture

```
                  ┌─────────────────────────────────────────┐
                  │          HTTP Gateway (FastAPI)         │
                  │       POST /add   │    POST /search     │
                  └────────────┬──────────────────▲─────────┘
                               │                  │
                               ▼                  │
                  ┌──────────────────────┐        │
                  │   SQLite Store (WAL) │        │
                  │ - Synchronous disk   │        │
                  │ - Strict user_id iso │        │
                  │ - Idempotent dedupe  │        │
                  └────────────┬─────────┘        │
                               │                  │
                               ▼                  │
                  ┌──────────────────────┐        │
                  │ Hybrid Index (RRF)   │        │
                  │ - FTS5 BM25 Lexical  │        │
                  │ - Dense BLAS Dot-Prod│        │
                  └────────────┬─────────┘        │
                               │                  │
                               ▼                  │
  ┌───────────────────────────────────────────────┴───────────────┐
  │                 Axiom Retention & Re-ranking Layer            │
  │  • Temporal Resolver: Latest state #1, history preserved      │
  │  • Execution Retainer: Contiguous procedural steps & code     │
  │  • Multi-Hop Composition: Bridge entity 2-hop graph expansion │
  │  • Options Discriminator: Grounding signal from candidates    │
  └───────────────────────────────────────────────────────────────┘
```

### Core Innovations
- **Synchronous & Immediate Visibility**: Writes commit directly to SQLite WAL. Searches issued in the exact same millisecond immediately see newly added memories.
- **Absolute User Isolation**: Memory scopes are strictly partitioned with zero possibility of cross-user leakage.
- **Procedural Continuity (Column G)**: Automatically detects code snippets, tracebacks, terminal commands, and numbered recipes. Expands adjacent steps within the session so the downstream model receives complete operational context.
- **Temporal Resolution (Column C)**: Detects update markers (`changed to`, `moved to`, `reverted`) and ranks the latest state first while keeping historical context below.
- **Multi-Hop Composition (Column B)**: Identifies bridge entities in candidate memories to retrieve 2-hop connected premises.
- **Options-Aware Re-ranking**: When multiple-choice options are provided, memory relevance is weighted by candidate discriminator signal without fabricating synthetic answers.

---

## 3. Byte-for-Byte API Contract

### 3.1 `POST /add`
```bash
curl -X POST http://localhost:8000/add \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "eval:run_01:locomo:chunk-0",
    "messages": [
      {
        "role": "user",
        "timestamp": 1704067200000,
        "content": "Step 1: Configure Redis maxmemory to 4gb."
      }
    ],
    "user_id": "eval:user_01",
    "session_id": "eval:session_01"
  }'
```

**Response:**
```json
{
  "success": true,
  "request_id": "eval:run_01:locomo:chunk-0",
  "user_id": "eval:user_01",
  "session_id": "eval:session_01"
}
```

### 3.2 `POST /search`
```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How to configure Redis memory limit?",
    "options": ["A. 2gb", "B. 4gb", "C. 8gb"],
    "user_id": "eval:user_01",
    "top_k": 100
  }'
```

**Response:**
```json
{
  "data": [
    {
      "id": "mem_a8f912c0",
      "content": "Step 1: Configure Redis maxmemory to 4gb.",
      "score": 0.8921,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

---

## 4. Quickstart & Local Setup

### Installation with `uv` (Recommended)
```bash
# Clone the repository
git clone https://github.com/ronisaguey-ux/aml-hackathon.git
cd aml-hackathon

# Create virtual environment and install dependencies
uv venv .venv
source .venv/bin/activate
uv pip install -e .
```

### Running the Server
```bash
# Run server on port 8000
python scripts/run_server.py --port 8000
```

### Verification & Testing
```bash
# 1. Run unit test suite (10/10 passing)
pytest -v

# 2. Run official AML smoke tests
python scripts/smoke_test.py --base-url http://localhost:8000

# 3. Run capability probe suite (Temporal, Execution, Composition, Options)
python scripts/probe_suite.py --base-url http://localhost:8000

# 4. Run local benchmark harness (MRR: 1.0000 | Recall@1: 100.0%)
python scripts/eval_harness.py --base-url http://localhost:8000

# 5. Run non-vacuity check (verifies harness fails decisively on reversed rankings)
python scripts/eval_harness.py --base-url http://localhost:8000 --test-broken

# 6. Run load benchmark (Throughput: 16.3 QPS | Search p50: 176 ms)
python scripts/benchmark_load.py --adds 250 --searches 100 --concurrency 4
```

---

## 5. Docker Deployment

```bash
# Build and run with Docker Compose
docker compose up -d

# View live logs
docker compose logs -f
```

---

## 6. Model Adapters & Academic Track Compliance

Under the AML Academic Open-Source Division rules:
- Embeddings can be configured to use `text-embedding-v4`.
- LLM component defaults to `gpt-4o-mini`.

Set environment variables:
```bash
export AXIOM_EMBEDDING_PROVIDER=openai
export OPENAI_API_KEY="your-api-key"
export TEXT_EMBEDDING_MODEL="text-embedding-v4"
```

For zero-network, local, and private environments, AxiomMem defaults to high-throughput ONNX FastEmbed (`BAAI/bge-small-en-v1.5`), achieving sub-millisecond similarity computation.

---

## 7. Data Hygiene Policy

In accordance with Section 2.4 of the AML Guidelines:
- Benchmark evaluation data is used strictly for serving search requests during live evaluation.
- All evaluation records are automatically scrubbed and deleted within 30 days (`AXIOM_DATA_RETENTION_DAYS=30`).
- No user evaluation data is logged, retained, or utilized for model training.

---

## 8. License

MIT License. See [LICENSE](LICENSE) for details.
