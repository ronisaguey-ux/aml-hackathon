# AML FOLLOW-UP — AxiomMem v0.3.0 (what still blocks the prize)

**Repo:** `github.com/ronisaguey-ux/aml-hackathon` @ `bef9aa1` (v0.2.0)
**Verified independently this session** — all contract checks pass, pytest clean, and I re-ran your
`eval_harness.py` myself: **7/7 → MRR 1.0000**, and `--test-broken` drops to **0.25**. The harness
is non-vacuous. The work is real.

**But 1.0000 is a warning, not a win.** Read §1 first.

---

## 1. THE SCORE IS SATURATED ON SEVEN CASES — that is the biggest risk now

`eval_harness.py` scores **7 hand-authored scenarios** (`temp_01..03`, `exec_01..02`,
`multihop_01`, `rule_01`). Every one returns **Rank 1**. Three consequences:

1. **A perfect score on a 7-case set tells you the set is easy, not that the system is good.** The
   real evaluation is **150 coding tasks × 2 settings = 300 units** (Coding track) and 5,000+
   questions over 1,500+ histories (Textual). Seven cases is 2 % of one track.
2. **Your own gold phrases appear verbatim in the memories.** The scorer checks
   `all(term.lower() in content.lower() ...)` — so every gold scenario passes on *substring match*,
   which is lexical lookup, not retrieval. The AML datasets contain paraphrase, distractor noise,
   multi-hop, and temporal conflict. Your 1.0000 does not demonstrate you handle any of that.
3. **You have already overfitted to it.** AML-002/003/004 were fixed by tuning against these seven
   cases. That is fitting the test, and it will not generalise.

**Do this:** expand the harness to **at least 60 scenarios** derived from the **real** public
pipelines (`data/{locomo-refined,beam,personamem,longmemeval-s,scriptmem,clbench}/pipeline.py`), with:
- **Paraphrased gold queries** — the question must NOT contain the memory's words verbatim. Test
  semantics, not substring.
- **Distractor floods** — 50+ irrelevant memories per scenario, including topically-similar decoys.
- **Temporal conflict sets** — several dated values for the same fact, gold is the one the query tense
  asks for.
- **Multi-hop** where the two hops are in *different* sessions.
- **Negatives** — queries whose answer is genuinely absent, which must return `[]` or low-confidence
  rather than a confident wrong memory.

Then **report the score as a range with per-category breakdown**, not one number. **A fall from
1.0000 to e.g. 0.72 on a harder set is a better artifact** — it is honest and it tells you where to
work. Do not tune the 60-case set until it reads 1.0000; that reproduces the same trap one level up.

**Non-vacuity hole to fix too:** in `--test-broken`, **Column G stayed at 100 %** and Column B at
100 %. A broken-ranking check that leaves two columns perfect means those two scorers do not depend
on order — so they cannot detect the failure mode they exist to detect. Make the broken mode
**shuffle within the sequence** (not reverse the whole list) and assert Column G drops.

---

## 2. THE HARD BLOCKER: IT IS NOT PUBLICLY HOSTED

The platform calls **your** `https://…/add` and `/search`. Right now there is a server on
`127.0.0.1` and a `docs/SUBMISSION.md` that says "run a bare quick tunnel". That is not submittable:

- A **`trycloudflare` quick tunnel is ephemeral** — the URL changes on every restart and it dies with
  the shell. The evaluation runs **0.5–2 days after you submit** and the queue closes Nov 4. A tunnel
  that drops mid-evaluation scores **zero**.
- There is no **restart-on-boot**, no **health check**, no **persistent URL**.

**Do this — in order:**
1. **Pin a permanent hostname.** Either a named Cloudflare Tunnel on a domain we control (preferred,
   matches the existing `cloudflared` stack on this box) or a small VPS with Caddy. **One stable
   HTTPS URL that survives a restart.**
2. **Run it as a service** (`systemd` unit or Docker with `restart: unless-stopped`), so a crash or a
   reboot brings it back. Include the exact unit file in the repo.
3. **Prove external reachability** from outside the box (not `localhost`), and paste the command and
   its output into `docs/SUBMISSION.md`.
4. **A 24/7 keep-alive + health check** hitting `/health` every minute, with the failure logged. The
   evaluation window is long and unattended.
5. **Rate/size sanity** — confirm `top_k=100` at eval concurrency returns inside the platform timeout
   through the tunnel (tunnel hops add latency; your local p50 of 176 ms will not be the p50 they see).

**This is the one thing that makes every other number irrelevant if it is missing.** A perfect
system behind a dead URL scores nothing.

---

## 3. MODEL COMPLIANCE IS DECLARED, NOT TESTED

`docs/SUBMISSION.md` says the academic board constrains embeddings to **`text-embedding-v4`** and LLM
components to **`gpt-4o-mini`**. The code **defaults to FastEmbed**, with the compliant adapter
present but presumably unused. Whichever board we enter:

- **If the academic/open-source board:** the **evaluated run must be made with `text-embedding-v4`**,
  and the `REPRODUCIBILITY.md` numbers must come from that configuration. **Re-run the 60-case harness
  with the compliant embedding** and record it — an evaluator can reproduce the declared version and
  will check.
- **If the industrial board:** re-run with the default and say so explicitly.
- **Either way, state in `SUBMISSION.md` exactly which provider+model produced the submitted
  numbers**, and make the default in `config.py` match the declared one so a redeploy cannot silently
  run the other.

Also verify: **rerankers are unrestricted** but any LLM component must be the permitted model. If a
cross-encoder or a local model is doing ranking, that is allowed — but say which.

---

## 4. SCALE AND DURABILITY — untested at real volume

Measured so far: ~54 mems/s ingest, 16.3 QPS at `top_k=100`, on ~**250 adds / 100 searches**. The real
evaluation is **orders of magnitude larger** (thousands of histories, 5,000+ questions).

- **Ingest the full published corpus volume** (not 250 rows) and re-measure. Does search degrade as
  the index grows? A linear-scan dense index over 10⁵+ memories will.
- **Concurrency:** measure p95/p99 at realistic parallelism, not p50 single-threaded.
- **Persistence across restart:** kill the process mid-evaluation-simulation and confirm nothing is
  lost and idempotency still holds (the `request_id` contract must survive a restart).
- **Disk:** SQLite WAL growth over a long run. Confirm the 30-day purge actually runs and that it
  cannot delete data inside an active evaluation.
- **Determinism:** the same query on the same corpus must return the same order every time, including
  after a restart. Add a stable tiebreak if any tie is resolved by dict/insertion order.

---

## 5. STILL ON THE TABLE FROM THE BUILD BRIEF

Carry these forward — they are the columns being targeted and they are cheap relative to their value:

- **Column E (Streaming)** — new in Cycle 2 and **the least-tuned by everyone**. Add/Search interleave
  as events arrive, with no end-of-run batch pass. Confirm nothing waits on a post-hoc reindex and that
  incremental state (running summary, entity table) updates **per add**.
- **Column D (rules/constraints)** — keep the constraint sentence verbatim; do not paraphrase a rule
  into an embedding. `rule_01` covers one case; add 5+ rule scenarios (deadlines, "never do X",
  ordering constraints) to the expanded harness.
- **Column F (governance)** — evidence boundaries and **uncertainty**. When nothing relevant is found,
  returning `[]` is correct; returning a low-confidence wrong memory is a governance failure. Assert
  this in the harness with the negative cases from §1.
- **Multimodal track** — if entering it, `content` is an ordered `ContentPart[]`, not a string, in
  both `messages[].content` and `data[].content`. Only worth it if Textual/Coding are solid first.

---

## 6. HOUSEKEEPING

- **Re-tag after every change.** `v0.2.0` now points at `77558ed` while `main` is `bef9aa1` — a
  mismatch. **The frozen version submitted must be the exact commit the repo is tagged at.** Tag
  `v0.3.0` on the final commit and state that hash in `SUBMISSION.md`.
- **`REPRODUCIBILITY.md`** must reproduce the **harder harness** numbers (§1), the **compliant-model**
  numbers (§3), and name the commit. A repro doc that only reproduces the easy 7-case 1.0000 is a
  liability.
- **Keep recording findings one by one** in `aml-findings.jsonl`, append-only, each with **a command
  and its real output**. Record the **failures** too (`status:"error"`) — a dead end documented is a
  dead end the next run does not repeat. This worked; keep doing it.
- **No secrets in the repo** (public). Confirm again after any deploy config is added — service files
  and compose files are a common place for a token to leak.

---

## 7. DEFINITION OF DONE FOR v0.3.0

1. A **stable public HTTPS URL** resolves from outside this box, is **restart-safe**, and the exact
   verification command plus its output is in `docs/SUBMISSION.md`. **(Blocks everything else.)**
2. The harness scores **≥60 scenarios** with paraphrase / distractors / temporal conflict / multi-hop
   / negatives, and reports **per-category results**, not one number.
3. `--test-broken` now also **drops Column G and Column B** — every column can fail.
4. The submitted configuration names its **exact embedding + model**, matches the board's constraint,
   and `config.py`'s default equals it. The declared numbers come from that config.
5. Scale numbers recorded at corpus-realistic volume, with p95/p99 and a restart-durability check.
6. Repo tagged at the submitted commit; `REPRODUCIBILITY.md` reproduces the **harder** numbers.
7. Findings file carries every new finding, including failures, with real evidence.

**Report back with:** the public URL + the external-reachability command output, the harder harness's
**full per-category table**, the Column-G broken-mode result, and the exact commit + config the
submitted numbers came from.

**A drop in the headline number with an honest, harder harness behind it is a better submission than
1.0000 on seven cases.** An evaluator who reproduces 1.0000 and then finds it was seven hand-picked
examples will discount everything else in the repo.
