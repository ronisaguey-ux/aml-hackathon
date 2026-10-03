# IMPROVEMENT BRIEF — AxiomMem (Agent Memory Challenge 2026, Cycle 2)

**For:** the building agent. **From:** an independent verification pass already done.
**Target:** raise the competition score. Not "make it nicer" — make it score higher.

Read §0 and §1 before touching code. §1 is what is already proven to work — do not break it.

---

## 0. WHERE THIS STANDS

`github.com/ronisaguey-ux/aml-hackathon` @ `99dd59d` (tag `v0.1.0`) is **verified working**. An
independent harness cloned it fresh and drove the live API against the platform contract:

- `add` echoes `request_id`/`user_id`/`session_id` exactly, returns `success:true` ✓
- a memory is searchable **immediately** after add (no index lag) ✓
- one `user_id` cannot see another's memories ✓
- replaying a request is **idempotent** — exactly 1 copy ✓
- **Column G**: a "how do I run the migration" query returned all 4 procedural steps together ✓
- **Column C**: after a correction, the NEW value ranks #1 with the old kept below ✓
- its own suite passes ✓

**So the contract is not the problem. The score is the problem.** Your job is to move numbers on
their leaderboard.

**Two hard facts to design around:**

1. **You never write the answer.** The platform takes your `data[]`, in your returned order, feeds it
   to *their* answer model, and their judge scores it. **Your entire product is the content and the
   ORDER of up to 100 returned memories.** Nothing else you build is scored.
2. **The winning score in Cycle 1 was 58/100.** Mem0 (66k stars, funded) scored 41.4; MemPalace
   (59k stars) 39.5. **The bar is low and the field is beatable — but only by being better at the
   columns everyone is bad at, not by having a nicer vector store.**

---

## 1. THE CONTRACT — EXACT, AND ALREADY SATISFIED. DO NOT REGRESS IT.

- **`POST /add`** — `{request_id, messages[{role, timestamp, content}], user_id, session_id}`.
  `messages[].role` = `user|assistant`; **`messages[].timestamp` is OPTIONAL and in Unix
  MILLISECONDS as an INTEGER** (e.g. `1704067200000`). **It will very often be ABSENT** — handle that
  without losing temporal ordering (see §2.1). Response must be
  `{success:true, request_id, user_id, session_id}` with the identifiers echoed **exactly**;
  `success:true` only once **durably stored AND immediately searchable** (synchronous).
- **`POST /search`** — `{query, options?, user_id, top_k}`; `top_k` up to **100** in formal evals;
  `options` is a **top-level array present only for multiple-choice** and **never contains the gold
  answer**. Response `{data:[{id, content, score?, created_at?}]}` in **retrieval rank order**;
  `data[].id` and `data[].content` required (non-empty); **return `[]`, never omit `data`**.
- **Multimodal track**: `content` is an ordered `ContentPart[]` instead of a string — both in
  `messages[].content` on add and in `data[].content` on search. If you enter that track, this is the
  one structural difference.
- **⚠️ SENDING AN ISO-8601 STRING WHERE AN INT IS EXPECTED RETURNS 422 AND STORES NOTHING.** A
  verification probe did exactly that and every downstream check failed. The field is an **int**.

---

## 2. WHERE THE SCORE ACTUALLY LIVES — THE SEVEN CAPABILITY COLUMNS

Their leaderboard reports per-capability, and **the field's collapse is concentrated in two of them.**
Cycle-1 evidence: fact recall (A) is solved — everyone is at 50–90. The failures are:

| column | what it measures | field (cycle 1) | what to build |
|---|---|---|---|
| **G — Context Learning & Execution** | using remembered context to **execute** a task | **6.86 · 9.82 · 24.32 · 29.99 (winner)** | procedural continuity, code/stack-trace/command retention, whole-sequence retrieval |
| **C — Temporal Resolution** | the *current* state of a changing fact | weak across the board | latest-state-first ranking with history retained below |
| **B — Relational / Multi-hop** | connecting evidence across memories | mixed | entity bridging, 2-hop expansion |
| D — Personalization & rules | following stated constraints | mixed | constraint/procedure extraction and retrieval on rule-shaped queries |
| F — Governance / safety | evidence boundaries, uncertainty | mixed | never return another `user_id`'s memory, ever |
| A — Fact recall | direct recall | **already high** | do not spend effort here |
| E — Streaming | add/search as events unfold | new in cycle 2 | no batch assumptions |

**Priority: G and C first — they are the differentiators and the measured weaknesses. Then D (rules),
then E (streaming, new this cycle and therefore where nobody has a tuned system).**

### 2.1 Temporal resolution (C) — go deeper than "latest wins"
- **`timestamp` is optional.** When present, it is the ground truth for ordering. When **absent**,
  derive order from message position within the request and from `request_id` arrival order — never
  from wall-clock at ingest, which collapses a replayed history into one instant.
- **State-change detection must cover more verbs than it does now.** "relocated to / changed to /
  reverted" is a start; add *moved, switched, upgraded, migrated, renamed, replaced, updated,
  corrected, no longer, previously, instead of, actually, sorry*. A missed verb = an old value
  ranked first = a wrong answer.
- **Question-shaped queries need the state, not the mention.** "What is X now / currently / these
  days" must surface the newest value; "what was X before / originally" must surface the older one.
  Detect the tense in the query and bias the ranking accordingly — this is cheap and almost nobody
  does it.
- **Return the trajectory, ordered.** Their answer model prefers *"the most recent supported
  memory"*; give it the newest first and the superseded ones after, explicitly labelled, so it can
  cite the change.

### 2.2 Execution continuity (G) — the biggest single lever
- **Retrieve the whole procedure, not the best-matching line.** When any step of a numbered/ordered
  sequence matches, return **all** steps of that sequence, **in order**, before other results. The
  downstream model must not have to reassemble a procedure from fragments.
- Recognise and keep intact: numbered/bulleted procedures, shell commands and their flags, stack
  traces, error messages, code blocks, config keys, file paths, test names, and "if X then Y"
  conditionals. These are what a coding-memory query is *about*.
- **Order matters more than score.** Their answer model reads top-down. Put the executed-context
  block first, then supporting evidence.
- For the **Coding Memory** track specifically: implementation context, debugging traces, failures,
  tests, and the *technical decision* behind a change. A query like "why did we do X" wants the
  decision and its rationale together, not twenty code lines.

### 2.3 Multi-hop (B) and rules (D)
- **Bridge on entities that actually recur.** Extract names, identifiers, file paths, services,
  and dates; when two memories share a bridge entity, they belong together. Cap expansion at 2 hops
  and budget it — unbounded expansion dilutes the top-100 and costs precision.
- **Rule/procedure queries need the constraint text verbatim.** "Always do X before Y", "never
  commit to main", "the deadline is Z" — keep the sentence, do not paraphrase it into an embedding.

### 2.4 Streaming (E) — new this cycle, least-tuned by everyone
Add and Search interleave as events arrive. Two consequences: **no end-of-run batch pass is
available**, and a query may arrive before the relevant memory does. Make sure (a) nothing depends
on a post-hoc reindex, (b) a search that finds nothing returns `[]` cleanly rather than erroring,
and (c) incremental state (a running summary, an entity table) is updated **per add**, not lazily.

---

## 3. RANKING IS THE PRODUCT — MEASURE IT, DO NOT TUNE IT BY FEEL

The single highest-leverage thing you can build is a **local scoring harness** that tells you whether
a change helped. Without it every change is a guess, and the platform gives only **two Full
evaluations per key** — you cannot afford to spend them discovering regressions.

Build it:
1. **Derive a local eval set** from the public pipeline code in the AML repo
   (`github.com/AML-memory/agent-memory-leaderboard` → `data/{locomo-refined,beam,personamem,
   longmemeval-s,scriptmem,clbench}/pipeline.py`). Those files show the question shapes, the
   generation prompts and the judge rules — **read them, they are the oracle for what to optimise.**
2. **Replay real histories** through `/add`, then run the queries through `/search`, and score
   `recall@k` and **rank of the gold memory** — not just "is it in the top 100".
3. **Make every change pass or fail that harness** before it ships. Record the number before and
   after, in the findings file (§5).
4. **Specifically measure:** rank-of-gold for state-change questions (C), and whether the full
   sequence is present for procedural ones (G). Those are the two columns being targeted.
5. **Watch the order, not only the membership.** A gold memory at rank 90 and at rank 1 are the same
   `recall@100` and completely different answers. Report mean reciprocal rank.

**Non-vacuity rule:** before trusting the harness, verify it **fails** on a deliberately broken
ranking (reverse the results). A scorer that cannot fail measures nothing — a grader in this project
scored a deliberately broken module 20/20 because its assertions were bare comparisons that never
raised.

---

## 4. ROBUSTNESS — THE THINGS THAT ZERO A SUBMISSION

Each of these has cost someone a competition. Treat them as hard requirements, not polish.

- **Latency under load.** Their `top_k=100` search must return inside their timeout at eval scale.
  Measure p50/p95/p99 at concurrency, not single-shot. (The last measured figure was 10.9 QPS,
  p50 316 ms — re-measure after every change and keep a number.)
- **Determinism.** The same query on the same corpus must return the same order. A tie broken by
  dict iteration order makes results unreproducible; add a stable tiebreak.
- **Degradation.** If the embedding path fails, fall back to lexical rather than returning `[]`.
  Returning empty looks like "no memory" and scores as a miss.
- **Isolation is absolute.** `user_id` scoping must hold even when `session_id` differs, even on a
  cache hit, even in an embedding-index scan. This is a governance column *and* a correctness one.
- **Idempotency under retry.** Their harness retries with the **same `request_id`**. A duplicate
  write inflates rank noise and can push a wrong memory up.
- **No secret in the repo** (it is public), **no training on eval data**, **minimise logging**, and
  the declared retention (30 days) must actually hold.
- **Every declared field must be honoured.** Optional means optional — accept and ignore an unknown
  field rather than 422ing on it. A 422 on a field you did not expect is an instant smoke failure.

---

## 5. HOW TO WORK, AND HOW TO RECORD IT

**Do not batch findings.** Record **each finding as its own JSON object, the moment it is found**,
appending to a file so nothing is lost if the session dies:

`/home/roni/Roni_workspace/aml-challenge/aml-findings.jsonl` (one JSON object per line):

```json
{"id":"AML-001","area":"contract|column_G|column_C|ranking|robustness|perf",
 "severity":"critical|high|medium|low",
 "title":"<one line>",
 "evidence":"<what was RUN and what it PRINTED — a command and its output, not an opinion>",
 "file":"<path:line if applicable>",
 "change":"<what was changed, or proposed>",
 "before":"<metric before, if measured>",
 "after":"<metric after>",
 "verify":"<the exact command that proves it>",
 "status":"open|fixed|wontfix|error",
 "date":"<ISO date>"}
```

Rules that make the file worth having:
- **`evidence` is a command and its real output.** "should work" is not evidence. A finding with no
  reproduction is a `severity:low` note, not a finding.
- **`status:error` is allowed and useful.** Record what you tried and how it failed; that is how the
  next agent avoids re-walking it.
- **One finding per line, appended immediately.** Never rewrite the whole file (a full-file rewrite
  from memory has silently destroyed data twice on this project — re-read, then append).
- **Write the before/after number whenever a change is performance- or score-related.** Without it,
  nobody can tell a fix from a rearrangement.

At the end, produce **`aml-findings-summary.json`**: counts by area and status, the changes that
moved a measured number, and **an explicit list of what is still unknown**. Do not present an
unmeasured claim as a result.

---

## 6. DEFINITION OF DONE

1. The **live contract still passes** — re-run the independent verification harness after every
   change (`scripts/verify_axiommem.sh` in the ccai repo drives add/search, isolation, idempotency,
   Column G and Column C against a fresh clone). **All checks green.**
2. A **local ranking harness exists** and prints a recall@k and MRR number, and is **proven
   non-vacuous** by failing on a reversed ranking.
3. **Column C** improves on the harness: mean rank of the gold memory for state-change questions.
4. **Column G** improves on the harness: full-sequence presence for procedural questions.
5. Latency p50/p95 recorded at the eval `top_k=100`, under concurrency.
6. `aml-findings.jsonl` holds one object per finding, with real evidence, plus the summary JSON.
7. The public repo is at a **fixed commit** with the exact version that was evaluated, and its README
   runs in one command.

**Report back with:** the commit, every measured before/after, the verification harness's output,
and an honest list of what is still unmeasured. **An accurate "this did not help" is worth more than
an optimistic claim** — two Full evaluations are all there are.
