# Phase 2 — Sender-aware ordered coercion state machine

**Goal:** Replace the coercion-grammar **stage-counting** in
`convergence/coercion_grammar.py` with a **sender-aware, ordered state machine**:
one coercer must drive `action → (objection → deflection)⁺ → fait_accompli` in
`seq` order, so a coercive envelope can no longer be falsely assembled from
different senders' messages or from out-of-order stage hits.

**Status:** design approved 2026-06-30. Sub-project 2 of the five-phase redesign;
Phases 0 (tooling/web hardening) and 1 (Signal provenance) are merged. Build
method: **Subagent-Driven Development**. Repo: `dsmcewan/Convergence`.

**Scope boundary:** Phase 2 changes only the *matching logic* in
`coercion_grammar.py` (and the tests that exercise it). The six stage regexes,
the REFUSAL/LEGITIMACY groupings, thread grouping, `classify_coercive`'s
signature, and every other engine layer are unchanged. The 5-corpus dynamics
eval must still score precision=recall=F1=1.00. Adversarial corpora, metric
rename, and the blind holdout are **Phase 3**.

---

## Context

`match_grammar()` today pools all stage hits in a thread and decides coercion by
**counting**: `cycles = min(len(refusal_seqs), len(legitimacy_seqs))` over the
"documentation war" before the fait, with
`complete = has_action and cycles >= 1 and has_fait`. Two flaws:

1. **Not sender-aware.** All hits in a thread count toward one envelope
   regardless of who sent them. Two parties in a normal dispute (A demands, B
   objects, A justifies, A finalizes — or worse, *different* people supplying
   different stages) can register as one "coercion grammar." Real coercion is one
   actor driving the envelope.
2. **Not ordered.** `min(count, count)` ignores temporal sequence — scattered or
   reverse-order hits register as "cycles." A genuine coercion grammar is an
   ordered progression in time.

Phase 1 gave every message/Signal explicit `actor` provenance; Phase 2 uses the
message sender to attribute envelope stages to a single coercer and walks the
hits in `seq` order.

## The state machine

`seq` is the canonical record order (monotonic position in the complete record),
so the machine processes a thread's stage hits sorted by `seq`. For each thread,
for each **candidate coercer** `C` — a sender with at least one stage-1 (action)
and one stage-6 (fait) hit — run:

```
S0         ──[ C's action (stage 1) ]──────────────▶ ACTED
ACTED      ──[ objection (stage 2), ANY sender ]───▶ CONTESTED
DEFLECTED  ──[ objection (stage 2), ANY sender ]───▶ CONTESTED      (next cycle)
CONTESTED  ──[ C's obstruction/question/justify (3/4/5) ]──▶ DEFLECTED   (cycles += 1)
DEFLECTED  ──[ C's fait (stage 6), requires cycles ≥ 1 ]──▶ COMPLETE
```

Transitions fire only on hits with strictly increasing `seq`. The **objection**
(stage 2) being deflected may come from any sender (it is the pushback being
steamrolled); **every other envelope stage (1, 3, 4, 5, 6) must be `C`'s.**

- **`complete` for `C`** ⇔ `C`'s action, then **≥1** ordered (objection →
  `C`-deflection) cycle, then `C`'s fait — strictly increasing in `seq`.
- A coercer's justification with no preceding objection is **not** a war cycle;
  the fait counts only after `cycles ≥ 1`.
- A reversed-chronology record (fait appears at a lower `seq` than the action)
  cannot reach COMPLETE.

`cycles` is now **the count of ordered objection→deflection pairs before the
fait** (replacing `min(len(refusal), len(legitimacy))`).

## Data + structure changes

- **`StageHit`** gains `sender: str` — `tag_stages` reads it from each message
  (`StageHit(seq, stage, name, cue, sender)`). Sender-awareness begins at tagging.
- **`GrammarMatch`** gains `coercer: str` — the sender who drove the envelope (the
  candidate `C` for which the machine completed, or the strongest partial). All
  existing fields remain: `thread, seqs, stages_present, has_action,
  has_fait_accompli, cycles, status_quo_seq, complete, summary`. `seqs` /
  `stages_present` now reflect the coercer's envelope hits; `summary` names the
  coercer.
- **`match_grammar(messages) -> list[GrammarMatch]`** keeps its signature.
  Internals: group by thread (unchanged); for each thread, iterate candidate
  coercers (senders with both an action and a fait), run the ordered machine over
  the thread's `seq`-sorted hits, and emit a `GrammarMatch` per coercer that shows
  activity. A thread may yield one coercer; if none completes, emit partial
  matches exactly where the old code would have (so "no activity" still `continue`s).
- **`classify_coercive(messages)`** is unchanged: `any(m.complete for m in
  match_grammar(messages))`.
- The six stage regexes and `_REFUSAL`/`_LEGITIMACY` are **unchanged**.

## Eval (must hold) + consumers

- **The 5 labeled dynamics corpora must still score precision = recall = F1 =
  1.00** under the new machine (`demo --eval`, `evaluate_dynamics`):
  - `dyn_coercive` → one coercer completes the ordered envelope → coercive (TP).
  - `dyn_cooperative`, `dyn_parallel`, `dyn_conflicted` → no single-coercer ordered
    envelope → not coercive (TN).
  - `dyn_high_conflict` (the **hard negative** — hostile, many stage hits, but no
    one coercer driving an ordered action→cycle→fait) → not coercive (TN).
- **Verification risk (must check during build):** if `dyn_coercive`'s envelope is
  actually split across senders or out of `seq` order, the strict machine would
  reject it (a false negative, dropping the eval below 1.00). The build MUST
  confirm `dyn_coercive` still completes under the new machine. If it genuinely
  does not, **surface it** and re-baseline the corpus *only with explicit
  justification* — never weaken the machine to force a pass.
- `evaluation.py` (`evaluate`, `evaluate_dynamics`, `metrics`) is unchanged — it
  consumes `match_grammar`/`classify_coercive` through their stable signatures.

## Testing

- **Sender-awareness unit test:** an envelope whose stages are split across **two
  senders** (e.g. sender A's action + sender B's deflections + sender A's fait, or
  the deflections from a different sender than the action) does **NOT** complete.
- **Ordering unit test:** the same stage cues arranged in **reverse `seq` order**
  (fait before the cycle before the action) do **NOT** complete.
- **Positive unit test:** a clean single-coercer ordered envelope (one sender:
  action → objection(other) → that sender's justify → that sender's fait)
  completes, with the correct `coercer` and `cycles ≥ 1`.
- **Hard-negative unit test:** a hostile two-party exchange with many stage hits
  but no single ordered coercer stays **not complete** (mirrors `high_conflict`).
- **Eval regression:** `evaluate_dynamics` still returns precision=recall=F1=1.00;
  `tests/test_dynamics_corpora.py` / `tests/test_coercion_grammar.py` updated for
  the new `GrammarMatch` shape (`coercer` field, `cycles` semantics) while the
  classification outcomes hold.
- All Phase-0/1 gates stay green: `ruff`, `mypy`, coverage ≥ 80%, tests ×2,
  demo-data-drift, on Python 3.10–3.12; Pages test-gated.

## Exit criteria

- `coercion_grammar.py` decides coercion via the sender-aware ordered state
  machine; `StageHit.sender` and `GrammarMatch.coercer` are populated; `cycles` is
  the ordered objection→deflection count.
- The 5-corpus dynamics eval is precision=recall=F1=1.00 (verified, with
  `dyn_coercive` confirmed to complete); the sender-split and reverse-order unit
  tests pass; `classify_coercive`'s signature unchanged.
- `ruff`/`mypy`/coverage(≥80)/drift green on 3.10–3.12; no change to the stage
  regexes, other layers, or corpora (unless a justified `dyn_coercive` re-baseline
  proves necessary — flagged, not silent).

## Decisions log (brainstorming, 2026-06-30)

- **Attribution:** one coercer owns stages 1/3/4/5/6; the objection (2) being
  deflected may come from any sender. The coercer drives their own envelope.
- **Ordering:** a *complete* envelope is `C`'s action → ≥1 ordered
  (objection → `C`-deflection) cycle → `C`'s fait, strictly increasing in `seq`. A
  reversed-chronology record cannot complete.
- **Eval discipline:** keep the 5-corpus eval at 1.00; verify `dyn_coercive` still
  completes; re-baseline a corpus only with explicit justification. Phase 2 adds
  direct sender-split and reverse-order unit tests; the full adversarial corpora,
  metric rename, and blind holdout are Phase 3.
- **Interface stability:** `match_grammar` and `classify_coercive` keep their
  signatures; `StageHit` gains `sender`, `GrammarMatch` gains `coercer`.

## Non-goals (Phase 2 — YAGNI)

- No adversarial regression corpora (mixed senders / interleaved threads / subject
  mismatch / unrelated-pattern contamination) — Phase 3.
- No metric rename and no blind holdout corpus — Phase 3.
- No change to the six stage regexes, the REFUSAL/LEGITIMACY groups, thread
  grouping, or any other engine layer.
- No new corpora and no change to existing corpus data (barring a justified,
  surfaced `dyn_coercive` re-baseline if the strict machine legitimately requires
  it).
