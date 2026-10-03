# AxiomMem Architecture Specification

AxiomMem is a high-performance agent memory system engineered for **Agent Memory Challenge 2026 (AML Cycle 2)**, specifically targeting the **Coding Memory** and **Textual Memory** tracks.

---

## 1. System Philosophy: Designing for Execution (Column G)

In AML Cycle 1, the leaderboard revealed a fundamental asymmetry across top entrants:
- Entrants achieve **50% to 90%** on explicit fact recall (Column A).
- Entrants collapse to **6.86% to 29.99%** on Context Learning & Execution (Column G).

Standard RAG architectures fail execution tasks because they chunk contiguous instructions and code traces into isolated fragments, returning disjointed snippets out of order. When the evaluation model attempts to run SWE tasks or multi-step procedures, missing prerequisites cause complete task failures.

AxiomMem treats **execution stability and sequential continuity** as the primary optimization target:
1. **Procedural Integrity**: Detects code blocks, stack traces, shell commands, and directive rules.
2. **Sequential Expansion**: When a procedural step is retrieved, adjacent operational steps within the session flow are automatically pulled into context in execution order.
3. **Temporal Coherence**: When facts update across turns, latest states receive precedence without erasing the historical trajectory.
4. **Options Discrimination**: Grounding multiple-choice options with pure memory evidence without ever fabricating synthetic answers.

---

## 2. Core Architecture Pipeline

```
              ┌────────────────────────────────────────────────────────┐
              │                   API Gateway Layer                    │
              │         POST /add        │       POST /search          │
              └───────────────┬────────────────────────▲───────────────┘
                              │                        │
                              ▼                        │
              ┌───────────────────────────┐            │
              │  SQLite Store (WAL Mode)  │            │
              │  - Idempotent (request_id)│            │
              │  - Strict user_id isolate │            │
              │  - FTS5 Porter Stemmer    │            │
              │  - BLAS Embedding Blobs   │            │
              └───────────────┬───────────┘            │
                              │                        │
                              ▼                        │
              ┌───────────────────────────┐            │
              │   Hybrid Retrieval Engine │            │
              │  - BM25 Lexical (FTS5)    │            │
              │  - Dense Semantic Vector  │            │
              │  - Reciprocal Rank Fusion │            │
              └───────────────┬───────────┘            │
                              │                        │
                              ▼                        │
              ┌────────────────────────────────────────┴───────────────┐
              │                    Retention Layer                     │
              │  1. Multi-Hop Composition (Column B)                   │
              │  2. Procedural Continuity & Expansion (Column G)       │
              │  3. Temporal Update & Recency Resolver (Column C)      │
              │  4. Options Discriminative Re-ranking                  │
              └────────────────────────────────────────────────────────┘
```

---

## 3. Subsystem Breakdown

### 3.1 Store Layer (`axiom_mem/store/db.py`)
- **Engine**: SQLite with Write-Ahead Logging (`PRAGMA journal_mode = WAL;`, `PRAGMA synchronous = NORMAL;`).
- **Isolation**: Every SQL query enforces `WHERE user_id = ?`. Cross-user data contamination is mathematically impossible.
- **Idempotency**: Retries with the same `request_id` are identified via the `requests` table and acknowledged without duplicate memory generation.
- **Immediate Visibility**: Every write transaction commits immediately to disk before returning `{"success": true}`, eliminating eventual consistency smoke test failures.

### 3.2 Index Layer (`axiom_mem/index/`)
- **BM25 Lexical Index (`bm25.py` / FTS5)**:
  SQLite FTS5 full-text search with unicode61 tokenizer and Porter stemmer. Enables sub-millisecond retrieval of exact code symbols, error codes, commit hashes, and identifiers.
- **Dense Embedding Adapter (`embeddings.py`)**:
  Swappable adapter pattern:
  - `FastEmbedAdapter`: Local ONNX runtime using `BAAI/bge-small-en-v1.5` (zero network overhead, ~40-50 adds/sec on CPU).
  - `OpenAIEmbeddingAdapter`: Conforming to the AML academic division constraints (`text-embedding-v4`).
  - `HashEmbeddingAdapter`: Zero-dependency feature hashing fallback.
- **Hybrid Fusion (`hybrid.py`)**:
  Combines BM25 and Dense ranks using Reciprocal Rank Fusion:
  $$RRF(d) = \frac{w_{\text{bm25}}}{k + \text{rank}_{\text{bm25}}(d)} + \frac{w_{\text{dense}}}{k + \text{rank}_{\text{dense}}(d)}$$
  Where $k = 60$. Dense matrix operations use vectorized BLAS dot products.

### 3.3 Retention Layer (`axiom_mem/retention/`)
- **Temporal Resolver (`temporal.py`)**:
  Detects update markers (`moved to`, `changed to`, `updated to`, `reverted`). Normalizes timestamp deltas and boosts current valid states while keeping prior states in lower rank positions for complete historical context. Formats timestamps as ISO-8601 strings.
- **Execution Retainer (`execution.py`)**:
  Classifies operational content (code blocks, command line syntax, multi-step instructions). For execution queries, expands adjacent sequence turns within the matching session so the agent receives the complete procedure.
- **Composition Expander (`composition.py`)**:
  Extracts named entities and bridge concepts from top candidate memories, issuing targeted 2-hop lookups to ensure multi-premise questions have both links present in context.
- **Options Discriminator (`discriminator.py`)**:
  When multiple-choice `options` are provided, computes discriminative relevance between memories and candidate options, boosting memories that provide decision-making evidence.
