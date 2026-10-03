# BUILD BRIEF — Agent Memory Challenge 2026, Cycle 2

**For:** the building agent. **From:** research already done. **Target:** a real prize, not a demo.

You are building a memory system that competes on a live, externally-run benchmark. It must pass a
remote smoke test and then a scored full evaluation against systems from Tencent, Mem0 and 20+
universities. Nothing here is hypothetical — every requirement below was read off the organiser's own
interface guide and their published evaluation code.

---

## 0. THE ONE THING TO UNDERSTAND FIRST

**Read the cycle-1 leaderboard before writing a line of code, because it tells you exactly where to
aim.**

| rank | system | overall | A recall | B inference | C temporal | D govern | E personal | **G execution** | H safety |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **MemoraX** | **58.02** | 89.89 | 63.44 | 60.00 | 51.19 | 58.51 | **29.99** | 58.39 |
| 2 | MemOS | 45.89 | 68.95 | 53.41 | 56.53 | 44.30 | 48.73 | **9.82** | 56.13 |
| 3 | NTES-MEMORY-SMART | 44.21 | 55.57 | 46.80 | 20.60 | 31.24 | 56.96 | 27.74 | 29.03 |
| 5 | Cognee | 42.61 | 53.62 | 42.90 | 22.01 | 32.14 | 54.49 | 27.11 | 29.03 |
| 7 | TencentDB | 41.48 | 50.44 | 39.12 | 21.89 | 31.54 | 53.10 | 28.66 | 34.84 |
| 8 | **Mem0** (66k★) | **41.40** | 50.60 | 42.70 | 17.43 | 36.04 | 55.29 | **27.36** | 37.42 |
| 9 | **MemPalace** (59k★) | 39.48 | 58.77 | 51.59 | 30.59 | 33.16 | 57.14 | **6.86** | 43.87 |
| 10 | Vectorize Hindsight (45k★) | 38.54 | 46.43 | 40.43 | 16.87 | 34.83 | 55.69 | **24.32** | 39.35 |

Three facts jump out, and the whole strategy follows from them:

1. **The bar is LOW and the field is close.** The leader is at 58/100 and most systems sit at 38–46.
   A 66,000-star, well-funded commercial memory layer scores **41.40**. This is winnable.
2. **Everybody is good at retrieval and bad at USE.** Column A (explicit fact recall) is 50–90 for
   nearly everyone. **Column G ("Context Learning & Execution" — using remembered context to actually
   execute a task) is the lowest column for almost every system in the table**: 6.86, 9.82, 27.36,
   24.32. Even the winner only reaches 29.99.
3. **So the winning wedge is not "better recall" — it is "memory that survives into execution."**
   Every entrant is building a retrieval pipeline. Almost nobody is measuring whether the retrieved
   context is still *correct* after a long session.

**Design the system around column G.** Do not build another vector store with a reranker; that is
what the other fifteen systems are, and it is why they cluster at 41.

---

## 1. WHAT THE COMPETITION IS

- **Organiser:** CSIG (China Society of Image and Graphics); platform is the Agent Memory Leaderboard
  (AML), backed by ~20 universities (Tsinghua, Peking, Oxford, HKUST, NTU, SJTU, Zhejiang, Fudan…).
- **Prize pool:** ¥150,000 total, **¥50,000 per track**, open-source methods only.
  Per track: 1st ¥20,000 · two 2nd at ¥8,000 · three 3rd at ¥3,000 · Best Technical Innovation ¥5,000.
  *(≈ $2,800 for first in a track — plus the technical-innovation prize is a separate ¥5,000 that a
  novel method can win even without topping the table.)*
- **Three tracks, ranked independently:** **Textual Memory**, **Coding Memory**, **Multimodal Memory**.
- **Two divisions:** Open-source Methods (prize-eligible, needs a public repo at a fixed commit) and
  Commercial Products (ranked separately, **not** prize-eligible).
- **Deadlines:** materials due **2026-10-31 23:59 UTC+8**; evaluation queue closes **2026-11-04**;
  results mid-November. **Two Full evaluations per key per track**, second only after 30 days.
- **Entry is free.** You pay your own hosting; the organiser pays for answer generation and judging.

### The two tracks worth entering

- **Coding Memory** — "can an agent retrieve, filter and reuse relevant engineering experience from
  earlier work in the same repository." 12 repos, 150 base SWE tasks, 1,290 time-constrained,
  fine-grained-annotated historical tasks. **Development Memory** (reuse architectural decisions and
  prior patterns) and **Debug Memory** (reuse past diagnostic traces and repair strategies).
- **Textual Memory** — long conversations, cross-session history, explicit fact recall, multi-hop
  relations, temporal/event understanding, memory governance, personalization, rules & process
  execution, safety. 10+ datasets (PersonaMem, LoCoMo-Refined, CLBench, BEAM, LongMemEval, ScriptMem),
  1,500+ histories, ~5,000 questions. Cycle 2 adds **Streaming Memory** — Add/Search happen as events
  unfold, no static archive.

**Enter both if feasible** — they are independent evaluations and independent prize pools. Start with
**Coding Memory** (closest to the measured result we already have; see §5).

---

## 2. THE EXACT API CONTRACT

This was read off the organiser's live API guide. **Implement it byte-for-byte.** A schema mismatch
fails the smoke test and you never get scored.

You host **two HTTP endpoints**. The platform calls them; you never call the platform.

### 2.1 `POST /add`

```json
{
  "request_id": "eval:<run_id>:locomo_refined:conv-0:chunk-0",
  "messages": [
    { "role": "user", "timestamp": 1704067200000, "content": "raw memory text" }
  ],
  "user_id": "eval:<run_id>:locomo:conv-0",
  "session_id": "eval:<run_id>:sample:0"
}
```

| field | required | rules |
|---|---|---|
| `request_id` | yes | idempotency key. **Retries reuse the same value** — dedupe on it and echo it back. |
| `messages` | yes | in **source order**; store and process in that order |
| `messages[].role` | yes | `user` or `assistant` |
| `messages[].content` | yes | **string** for Textual/Coding. `ContentPart[]` only for Multimodal. |
| `messages[].timestamp` | no | Unix **milliseconds**. Chunking must not change it or the order. |
| `user_id` | yes | **memory isolation scope** — every Search for this user carries the same value |
| `session_id` | yes | source conversation/session identifier |

**Response:**

```json
{ "success": true, "request_id": "...", "user_id": "...", "session_id": "..." }
```

`success` must be `true` **only after the messages are durably stored AND immediately searchable**.
Echo the three identifiers **exactly** as received — the platform checks them.

### 2.2 `POST /search`

```json
{
  "query": "Which answer best matches the memory?",
  "options": ["A. First answer", "B. Second answer"],
  "user_id": "eval:<run_id>:locomo:conv-0",
  "top_k": 100
}
```

| field | required | rules |
|---|---|---|
| `query` | yes | the benchmark question. String for Textual/Coding; `ContentPart[]` for Multimodal. |
| `options` | conditional | present at top level for **multiple-choice**; absent for open questions. **Never contains the gold answer.** |
| `user_id` | yes | same scope as the matching Add |
| `top_k` | yes | max results; **formal evaluations use 100** |

**Response:**

```json
{ "data": [ { "id": "mem_123", "content": "remembered fact text", "score": 0.87,
              "created_at": "2026-07-01T12:00:00Z" } ] }
```

| field | required | rules |
|---|---|---|
| `data` | yes | array in **retrieval rank order**. Return `[]` when empty — **never omit `data`**. |
| `data[].id` | yes | stable identifier |
| `data[].content` | yes | non-empty string. **This text is what gets shown to the answer model, in this order.** |
| `data[].score` | no | higher must mean more relevant |
| `data[].created_at` | no | source/persistence timestamp |

### 2.3 What the platform does with your `data`

**You do not answer the question.** The platform takes your returned `content` strings, renders them
into its own prompt, calls its own model, and judges the result itself. Its published pipeline shows:

- Answer prompt: *"Use only the provided memories… Your memories are episodic raw observations. Reason
  about what they imply. Do not refuse just because the answer is not stated verbatim."*
- It is told to prefer the **most recent supported memory** when memories conflict, to convert relative
  times into dates when the timestamp makes it clear, and to return the **shortest correct phrase**.
- Judging is strict on lists (gold `A,B,C` vs answer `A,B,C,D` = **WRONG**) and strict on time
  granularity (month ≠ day ≠ year), but generous about paraphrases and extra non-contradictory detail
  elsewhere.

**The design consequence is the single most important implementation insight:** your job is to put the
**right evidence, in the right order, at the top of the list**, phrased as a raw observation. Ranking
order is the product. A perfect retrieval set returned in bad order scores worse than a merely good set
returned in good order.

### 2.4 Hard operational requirements

- **Synchronous:** a Search issued immediately after a successful Add MUST see the new memory. No
  eventual consistency, no async indexer lag. This is the single most common smoke-test failure.
- **Idempotent** on `request_id`.
- **User isolation is absolute** — never leak one `user_id`'s memories into another's Search. The
  platform tests this.
- **Stable, publicly reachable endpoints.** No auth surprises; the key is bound at application time.
- **Data hygiene:** evaluation data is for the evaluation only. Do not train on it, do not analyse it,
  minimise logs, and **delete within 30 days** of the run. Say so in the repo.
- **Version pinning:** the submitted version is frozen at Full-evaluation start and bound to the repo
  commit. Tag it.

---

## 3. TWO DIVISIONS — PICK OPEN-SOURCE, AND OBEY THE MODEL RULES

**Open-source Methods** is the only prize-eligible division: you need a **public GitHub repo at a
fixed commit**, plus method description, authors and reproduction materials. A repo alone is NOT a
submission — you must still host the live Add/Search API. (Cycle 2 explicitly dropped the
"repo-only, platform deploys it" route.)

**If entering the academic/open leaderboard, the component models are constrained:** embedding must be
`text-embedding-v4`, and any LLM component must be `gpt-4o-mini`. Rerankers are unrestricted. If you
want to use a self-trained or other open-weights model, that belongs on the industrial board instead.
**Check which board the prize applies to before choosing — the ¥150k pool is described as open-source
methods.** Architect so the embedding model is a swappable adapter; do not hardcode it.

---

## 4. ARCHITECTURE TO BUILD

Build the thing the leaderboard says nobody has built: **a memory system whose retrieval is stable
under a long session.** Three layers, deliberately separated.

### 4.1 Store — append-only, order-preserving, timestamped
- Keep every message with its `timestamp` and arrival order. Never mutate history in place.
- Dedupe on `request_id` (idempotency).
- Partition strictly by `user_id`; `session_id` is a grouping key, not a security boundary.
- Persist **to disk**, not to process memory — a restart during a scored run must not lose state.

### 4.2 Index — the part everyone else already does
- Dense embeddings for semantic recall + a cheap lexical index (BM25) for exact names, numbers, IDs.
- **Hybrid retrieval with reciprocal-rank fusion**, then a reranker. This is table stakes; do not skip
  it, and do not imagine it is the differentiator.
- **Always return at least `top_k` items when that many exist.** Returning 10 when 100 were requested
  throws away evidence the answer model could have used.

### 4.3 The differentiator — a retention layer over the top
This is the wedge, and it is where the engineering effort should go:

- **Temporal resolution.** The judge is strict about time. Detect conflicting/updated facts (a user who
  moved city, a value that was superseded) and **rank the latest valid version first**, while still
  returning the superseded one lower down so the answer model can see the change. Cycle 1 shows
  temporal (column C) is weak almost everywhere — 16.87, 17.43, 20.60 for the big systems.
- **Composition.** For multi-hop questions, return the *linked* evidence for both hops rather than the
  single best-matching chunk. Column B separates the winner (63.44) from the pack (39–53).
- **Execution support (column G — the real prize).** When the query looks like it must be *used* rather
  than merely recalled (procedures, rules, "how do I", multi-step), return **complete, ordered
  procedural context**, not top-scoring fragments. This is the column where the entire field collapses
  to 6–30. A system that lifts G even to 50 wins the track.
- **Options-aware ranking.** When `options` is present, use them as *ranking signal only* — never
  return an option as if it were a memory, and never emit the answer. Score each memory by how much it
  discriminates between the offered options. This is free accuracy that most entrants ignore.
- **Evidence over summaries.** Return raw, verbatim observation text with names, numbers and dates
  intact. The answer model is explicitly told to preserve specific names and to reason about raw
  episodic observations — a paraphrase is a lossy middleman and it is what costs points.

### 4.4 Non-negotiables
- **Do not hardcode, do not cross-sample share state, do not inject prompts.** The rules name these as
  disqualifying, and the platform inspects run logs.
- **Do not put a `gold`-shaped field anywhere** in your responses.
- Keep a `created_at` on every memory even if optional — it costs nothing and it is what the temporal
  capability is scored on.

---

## 5. WHY WE HAVE AN EDGE (use this in the writeup and as design evidence)

We already hold a **measured, controlled result** about exactly the capability this competition scores
weakly. From a 60-turn experiment on Gemma-4-12B, same model, same task, same budget:

| | bounded-context policy | baseline |
|---|---|---|
| task steps completed | **60/60** | 60/60 |
| mid-session facts recalled at the end | **60/60, in order** | 9/60, unordered |
| prefix-cache reuse | **81.3%** | 30.8% |
| compute cost | **118,817 units** | 484,957 units |

**Same execution quality, 6.7× better long-horizon recall, 4.08× cheaper.** That is a directly
transferable result: it says a memory layer that preserves *instructions* verbatim while discarding
superseded bulky artefacts retains far more usable context at a fraction of the cost. **That is the
design principle for §4.3, and it is a genuinely different bet from everyone else's RAG pipeline.**

It also gives the submission a **verifiable reproducibility story** the field lacks: an artifact
section pointing at a public repo with committed result files, a comparison tool that reproduces the
tables, and a citation check. Judges reward exactly this. Reuse the pattern.

---

## 6. BUILD ORDER (each step has an observable pass/fail)

1. **Scaffold the two endpoints** against the exact schemas in §2. Verify with `curl` locally —
   including the `[]`-not-omitted empty case and exact identifier echo.
2. **Get a public HTTPS endpoint.** A tunnel or small VM is fine. Verify from *outside* the host —
   a local `curl` proves nothing about reachability.
3. **Implement store + hybrid index + reranker.** Load-test: 10k Add calls, then 200 Search calls at
   `top_k=100`. Instrument p50/p95 latency. A scored run hammers you; a timeout is a failed task.
4. **Prove the two hard invariants** — write these as tests, not as assertions in a README:
   - **immediate visibility:** Add → Search in the same second returns the new memory;
   - **isolation:** a Search for `user_id=A` never returns a memory written for `user_id=B`.
5. **Build the retention layer** (§4.3), then measure each capability with a small self-made probe set
   before submitting — **including a temporal-conflict probe and a procedural multi-step probe.**
6. **Repository hygiene:** public repo, fixed commit tag, README stating the method, the component
   models used, and the 30-day deletion policy. Record the exact commit hash the submission is pinned
   to.
7. **Register, get the key, run Smoke**, fix, then spend a Full evaluation. **You get two.** Do not
   burn the first one on an untested build — finish steps 1–6 first.

---

## 7. THINGS THAT WILL SILENTLY COST THE PRIZE

- Returning a list where the answer model cannot find the evidence, because rank order was wrong.
- Async indexing → Search misses the just-added memory → **smoke failure**, before scoring even starts.
- Exceeding the latency budget under the platform's concurrency and getting marked as a failed task.
- `data` omitted instead of `[]` on an empty result.
- Assuming you must generate an answer. **You must not** — the platform does that and will treat a
  generated answer inside `content` as noise at best.
- Forgetting the model constraints (§3) and being scored on the wrong board.
- A repo that does not reproduce: if the paper/repo says one number and the artifacts say another,
  that is the documented fastest route to rejection in every judged research competition.

---

## 8. DEFINITION OF DONE

- [ ] `/add` and `/search` live on a public endpoint, schema-exact, synchronous, idempotent, isolated.
- [ ] Immediate-visibility and user-isolation tests exist and pass.
- [ ] Latency measured under load, with the numbers written into the repo.
- [ ] Retention layer implemented, with a documented reason for each ranking rule.
- [ ] Public repo at a tagged commit; README states method, models, licence and the 30-day deletion rule.
- [ ] Smoke test **passed**.
- [ ] At least one Full evaluation completed with results recorded — **and a second one held in reserve.**
