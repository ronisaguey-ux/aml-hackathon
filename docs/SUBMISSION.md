# AML Challenge 2026 — Official Submission & Deployment Dossier (v0.3.0)

This dossier details the architecture, configuration, deployment units, and verification steps for **AxiomMem v0.3.0** on the Agent Memory Leaderboard (AML) Cycle 2.

---

## 1. Competition Entry Registration

- **Division**: **Open-source Methods** (Eligible for ¥150,000 prize pool).
- **Target Tracks**:
  - **Coding Memory** (Primary track: Multi-step procedural workflows, debugging traces, and execution contiguity).
  - **Textual Memory** (Secondary track: Temporal state changes, multi-hop reasoning, strict constraints).
- **Repository URL**: `https://github.com/ronisaguey-ux/aml-hackathon.git`
- **Submitted Version Tag**: `v0.3.0`
- **Model & Embedding Configuration**:
  - **Submitted Engine**: Local ONNX Runtime with `BAAI/bge-small-en-v1.5` via `fastembed` (100% open-source, offline reproducible, zero third-party API dependencies).
  - **Academic Board Adapter**: Fully implemented and tested adapter for OpenAI `text-embedding-v4` (`EMBEDDING_PROVIDER=openai`).
  - **Data Retention Hygiene**: 30-day automated purge active (`AXIOM_DATA_RETENTION_DAYS=30`).

---

## 2. Benchmark & Leaderboard Capability Performance

Evaluated against the un-saturated 66-scenario benchmark suite (`scripts/eval_harness.py`) with 50+ background distractor floods per scenario (over 3,300 noise memories):

| Capability Metric | Evaluated Score | Broken Ranking Contrast (`--test-broken`) | Non-Vacuity Status |
|:---|:---:|:---:|:---|
| **Overall MRR** | **0.6494** | **0.2375** | Decisive drop (-63.4%) |
| **Mean Gold Rank** | **8.39** | **28.94** | Real variance over 50+ distractors |
| **Recall@1** | **51.5%** | **15.2%** | Hard semantic retrieval |
| **Recall@5** | **83.3%** | **30.3%** | Strong top-tier presence |
| **Recall@10** | **92.4%** | **39.4%** | Comprehensive coverage |
| **Column C (Temporal State Updates)** | **0.6211 MRR** | **0.2143 MRR** | Tense-aware past vs present routing |
| **Column G (Procedural Execution)** | **0.7889 MRR** | **0.0277 MRR** | Monotonic chronological sequence |
| **Column B (Multi-Hop Relational)** | **0.5563 MRR** | **0.2475 MRR** | Dual-hop linking across sessions |
| **Column D (Rules & Constraints)** | **1.0000 MRR** | **0.0481 MRR** | 100% Rank-1 verbatim rule retention |
| **Column E (Streaming Interleaved)** | **0.3792 MRR** | **0.0867 MRR** | Synchronous add-to-search visibility |
| **Column F (Governance & Negatives)** | **1.0000 MRR** | **1.0000 MRR** | 100% clean uncertainty on absent targets |

---

## 3. Production Deployment & Keep-Alive Daemon

### 3.1 Service Unit (`deploy/axiom-mem.service`)
To ensure reboot safety and automated crash recovery, AxiomMem runs as a managed `systemd` service:

```ini
[Unit]
Description=AxiomMem Agent Memory Service (AML Challenge Cycle 2)
After=network.target

[Service]
Type=simple
WorkingDirectory=/home/roni/Roni_workspace/aml-challenge
ExecStart=/home/roni/Roni_workspace/aml-challenge/.venv/bin/python scripts/run_server.py --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3
Environment=PYTHONUNBUFFERED=1
Environment=AXIOM_DATA_DIR=/home/roni/Roni_workspace/aml-challenge/data
Environment=AXIOM_DATA_RETENTION_DAYS=30
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
```

Enable and start with:
```bash
cp deploy/axiom-mem.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now axiom-mem.service
```

### 3.2 24/7 Keep-Alive & Health Monitoring (`deploy/keepalive_monitor.py`)
To prevent dropouts during unattended evaluation windows (0.5–2 days after submission), run the continuous keep-alive probe:

```bash
python deploy/keepalive_monitor.py --base-url http://localhost:8000 --interval 60 --log-file data/keepalive.log &
```

---

## 4. Public HTTPS Endpoint & Verification

The platform requires public endpoints conforming to the AML specification. AxiomMem v0.3.0 supports both root and versioned routes:
- `GET https://<domain>/health`
- `POST https://<domain>/add` & `POST https://<domain>/v1/memories/add`
- `POST https://<domain>/search` & `POST https://<domain>/v1/memories/search`

### 4.1 Live Active Public Deployment
- **Active Public URL**: `https://acid-reproductive-calculations-downloads.trycloudflare.com`
- **Host System**: Linux (x86_64), Python 3.12/3.14 virtualenv
- **Process Management**: Managed via systemd user units:
  - `axiom-mem.service`: Core FastAPI engine with local ONNX fastembed runtime
  - `axiom-mem-tunnel.service`: Isolated Cloudflare edge tunnel
  - `axiom-mem-keepalive.service`: 24/7 continuous health monitor logging to `data/keepalive.log` every 60s

### 4.2 External Reachability & Curl Verification Output
Verified live over the public internet:

```bash
# 1. External Health Check
curl -s https://acid-reproductive-calculations-downloads.trycloudflare.com/health
# Output:
# {"status":"ok","service":"AxiomMem","version":"0.3.0","uptime_seconds":33.78,"embedding_provider":"fastembed"}

# 2. External Search Endpoint
curl -s -X POST https://acid-reproductive-calculations-downloads.trycloudflare.com/v1/memories/search \
  -H "Content-Type: application/json" \
  -d '{"query": "production database host", "top_k": 2}'
# Output:
# {"data":[{"id":"mem_f084e4b00f585fb2","content":"Our production database host is db.us-east-1.internal.acme.net","score":0.0328,"created_at":"2026-10-03T05:38:47Z"}]}

# 3. External Smoke Test Suite
.venv/bin/python scripts/smoke_test.py --base-url https://acid-reproductive-calculations-downloads.trycloudflare.com
# Output:
# [1/6] Testing Health Endpoint... ✅ Health endpoint OK
# [2/6] Testing Add & Immediate Visibility Invariant... ✅ Add successful (99.40 ms). Field echo exact.
# [3/6] Testing Idempotency on request_id... ✅ Idempotency strictly maintained without duplicate records.
# [4/6] Testing Absolute User Isolation... ✅ Isolation verified: foreign user sees empty array [] with zero leaks.
# [5/6] Testing Empty Query / Zero Matches Schema... ✅ Empty query schema compliant (data: []).
# [6/6] Testing Multiple-Choice Options-aware Ranking... ✅ Options-aware ranking passed. Pure memory grounded.
# 🎉 ALL SMOKE TESTS PASSED! System is ready for AML evaluation queue.
```

---

## 5. Submission Procedure

1. **Submit Endpoint**: Enter `https://acid-reproductive-calculations-downloads.trycloudflare.com` on the official AML submission portal.
2. **Commit Hash**: Freeze at the release tag `v0.3.0`.
3. **Queue Smoke Check**: Observe real-time logs via `journalctl --user -u axiom-mem -f` and `data/keepalive.log` as the AML evaluation bot initiates verification probes.
4. **Full Evaluation**: After smoke verification succeeds, the platform scheduler automatically runs the benchmark suite.
