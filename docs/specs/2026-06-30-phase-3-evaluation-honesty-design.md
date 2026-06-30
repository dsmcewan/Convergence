# Phase 3 — Evaluation honesty: adversarial corpora + honest metrics + blind holdout

**Goal:** Prove the Phase-2 ordered, sender-aware coercion discriminator's
discipline **honestly**. Three coordinated workstreams: (1) expand the eval with
**adversarial corpora** in both directions — negative traps that fool a stage
*counter* but not the ordered/sender-aware machine, and robustness positives that
must survive noise; (2) **reframe the metrics** so they cannot be misread as
statistical generalization; (3) add a **fresh-subagent-authored blind holdout** to
detect overfitting of the hand-built rules to `dyn_coercive`.

**Status:** design approved 2026-06-30. Sub-project 3 of the five-phase redesign;
Phases 0 (tooling/web hardening), 1 (Signal provenance), 2 (sender-aware ordered
state machine) are merged. Build method: **Subagent-Driven Development**. Repo:
`dsmcewan/Convergence`.

**Scope boundary:** Phase 3 changes only the **evaluation surface** — corpora
(`data/`), the eval module (`convergence/evaluation.py`), and tests. It does **not**
change the engine's matching logic: the six stage regexes, the
`_REFUSAL`/`_LEGITIMACY` groups, `match_grammar`'s state machine, thread grouping,
`classify_coercive`'s signature, or any other layer stay as Phase 2 left them. The
**one** exception is fail-safe, not scope creep: if an adversarial or holdout corpus
exposes a *genuine* defect (a negative trap that fires, a robustness positive that
misses), that is surfaced and analyzed, and an engine fix is legitimate — but a
corpus is **never** relabeled or edited to make a number look good.

---

## Context

`convergence/evaluation.py` today scores the discriminator `classify_coercive`
(= "the corpus contains ≥1 complete coercion-grammar envelope") over **5 labeled
dynamics corpora** (`data/dyn_*.json`): 1 positive (`dyn_coercive`) and 4 negatives
(`dyn_cooperative`, `dyn_parallel`, `dyn_conflicted`, `dyn_high_conflict` — the hard
negative). It reports `precision / recall / f1 / specificity / accuracy` and names
the hardest negative by stage-hit count. The current result is
precision = recall = F1 = 1.00.

Two honesty gaps motivate Phase 3:

1. **The eval does not stress what Phase 2 fixed.** Phase 2 made the discriminator
   *ordered* and *sender-aware* precisely so a coercive shape cannot be assembled
   from different senders' messages or out of temporal order. Nothing in the current
   5-corpus eval actively *tries* to defeat that — `dyn_high_conflict` is hostile but
   not engineered against the specific invariants. Adversarial corpora close that
   gap from both directions.
2. **The metric names overclaim.** `precision/recall/f1` over a handful of curated
   corpora are names that imply a sampled population and statistical generalization.
   They have neither. The numbers are honest as *corpus-level discrimination*; the
   framing should say so, matching the engine's documentary-primacy discipline
   (`DocumentaryPrecision` is already careful this way for real data).

## Corpus tiers

Physical separation in `data/` reinforces the reporting tiers; the eval module
loads each tier by filename convention:

- **Core** — the existing `data/dyn_*.json` (5). **Frozen baseline; must stay at
  perfect discrimination** (all 5 classified correctly). This is the
  behavior-preservation guard: a regression here means Phase 3 changed engine
  behavior, which it must not.
- **Adversarial** — new `data/adv_*.json` (5). Scored as a separate named suite.
- **Holdout** — new `data/holdout/hold_*.json` (3). Scored as a separate
  "generalization" line; never consulted during tuning.

## Adversarial corpora (5 — three negative traps, two robustness positives)

Each is a small, focused synthetic corpus (no real data). The three negatives must
classify as **not coercive** (true negatives); the two positives must classify as
**coercive** (true positives).

| File | Label | Construction | Invariant it defeats |
|---|---|---|---|
| `adv_mixed_senders.json` | **negative** | A complete stage set (action 1 → objection 2 → obstruction/question/justify 3/4/5 → fait 6) within one thread, but the war/fait stages are **split across ≥2 senders** so no single sender owns stages 2/3/4/5/6. | stage-counting without sender attribution |
| `adv_reversed_chronology.json` | **negative** | All six stage cues present from one coercer in one thread, but arranged so the **fait is at the lowest `seq`** and the action at the highest — the envelope cannot progress in increasing `seq`. | stage-counting without temporal order |
| `adv_unrelated_contamination.json` | **negative** | A benign/cooperative thread whose individual messages **happen to match stage regexes** ("it's already done — I booked the slot we agreed on", "per the agreement", a clarifying question) but carry **no coercive structure** (no refusal→legitimize→fait progression by one party). | a false envelope assembled from a bag of unrelated cues |
| `adv_interleaved_threads.json` | **positive** | One **genuine** coercive envelope in thread X by coercer C, while **C also fires stage-like cues in other threads** (so a non-thread-local matcher could stitch a false cross-thread envelope or be distracted). Record-order interleaved. Must still fire on thread X **and** must not stitch across threads. | thread-locality must not break a true envelope, and cross-thread cues must not be stitched |
| `adv_subject_mismatch.json` | **positive** | One genuine coercive envelope plus **distractor messages that match stage regexes but concern unrelated domains/subjects**, interleaved by `seq`. Must still fire on the genuine envelope. | brittleness to topical noise |

**`adv_interleaved_threads` design note (flagged during brainstorming):** the core
`dyn_coercive` already interleaves its `preschool` envelope among many other threads,
so the new corpus earns its place only by being **harder** — the coercer must emit
stage cues in *other* threads too, so the test is specifically that the machine does
not stitch a cross-thread envelope and is not distracted from the genuine one. Build
it that way, not as a simple re-interleave.

**On a failing adversarial corpus:** the expected outcome is 3 TN + 2 TP. If a
negative fires or a positive misses, that is a **real Phase-2 gap**, not an eval
artifact. Surface it with the specific message seqs and the machine's trace; an
engine fix is then legitimate and in-scope as a justified, surfaced change.
Relabeling or softening the corpus to pass is prohibited.

## Blind holdout (`data/holdout/`)

A small frozen set (**3** corpora: ≥1 coercive, ≥1 plain non-coercive, ≥1
hard-negative-style hostile-but-not-coercive), authored to detect overfitting of the
hand-built rules to `dyn_coercive`.

**Blindness mechanism (the load-bearing discipline):**
- The holdout is **authored by a fresh subagent** that works **only from the
  behavioral definition of coercion** — the prose contract: a proposer's good-faith
  action (any party), then **one** coercer running ordered refuse (2/3) → legitimize
  (4/5) cycles, then that coercer's fait (6), strictly increasing in `seq`. The
  authoring subagent is **not** given `convergence/coercion_grammar.py`, the stage
  regexes, or the existing corpora to copy from. It writes plausible
  coparenting-style conversations that a human would label, not strings reverse-
  engineered from the matcher.
- Committed **once** and **frozen**. The documented rule: holdout failures are
  surfaced and analyzed; they are **never** "fixed" by editing the holdout corpus or
  relabeling. The only legitimate response to a true holdout-exposed defect is a
  justified engine change (the same bar as the adversarial corpora).
- Scored as a **distinct "holdout / generalization" report line**, separate from
  core and adversarial. The holdout score is **reported, not asserted to a target**
  in tests — asserting a holdout pass-rate in the suite would re-introduce a tuning
  signal and defeat blindness. The test asserts only that the holdout loads and
  scores deterministically.

## Honest metric reframing

Keep the math; fix the framing. `classify_coercive` and the five computed
quantities are **unchanged** (the core tier still reads perfect).

- **Report header + module docstring** reframe to **corpus-level discrimination**,
  stating `N` explicitly and carrying the caveat:
  *"N curated corpora — corpus-level discrimination, not a sampled population; no
  statistical generalization is claimed."*
- **Each tier leads with the honest headline** `k/N corpora correctly classified`
  plus the confusion matrix. The ratio diagnostics (precision, recall, specificity)
  remain **under that banner** as separation diagnostics, not as headline
  generalization claims. (`accuracy` over a curated balanced set is the most
  misleading single number, so it is demoted out of the headline; it may stay as a
  labeled diagnostic.)
- The real-data `DocumentaryPrecision` block stays clearly separated as the **only**
  real-data precision claim — its existing caveats are unchanged.
- **Metric dict keys stay stable** (`precision/recall/f1/specificity/accuracy`) so
  `demo --eval`, `web/serialize.py`, and existing tests do not break on a gratuitous
  key churn. The rename is **human-facing report vocabulary and caveats**, plus the
  new per-tier headline — not a change to the programmatic interface. (If a future
  decision wants the keys themselves renamed, that is a separate, wider consumer
  edit, explicitly out of this phase's scope.)

## Eval-module changes (`convergence/evaluation.py`)

- `evaluate(labeled) -> EvalResult` stays the scoring primitive, **unchanged**.
- `metrics(...)`, `CorpusEval`, `EvalResult`, `DocumentaryPrecision`,
  `documentary_precision`, `format_documentary_precision` are **unchanged**.
- **Label tables** for the new tiers mirror `DYNAMICS_LABELS`: `ADVERSARIAL_LABELS`
  (`adv_*.json` → bool) and `HOLDOUT_LABELS` (`hold_*.json` → bool).
- **Tiered driver**: a function that scores all three tiers from a data dir and
  returns the three `EvalResult`s (core / adversarial / holdout). `evaluate_dynamics`
  is retained (back-compat: it scores the core tier exactly as today). The tiered
  driver is additive.
- **Reframed reporting**: a report function that renders the three tiers with the
  honest per-tier headline and the corpus-level caveat. `demo --eval` prints all
  three tiers (core first, then adversarial, then holdout/generalization).

## Testing

- **Core-tier regression (the 1.00 guard):** a test asserts the core tier still
  classifies all 5 dynamics corpora correctly (perfect discrimination). Any drift
  here means engine behavior changed — a Phase-3 failure.
- **Per-adversarial-corpus assertions:** for each `adv_*.json`, a test asserts the
  predicted label equals the ground-truth label (3 negatives stay TN, 2 positives
  are TP). These are the proof that Phase 2's ordered/sender-aware machine actually
  holds under engineered attack.
- **Holdout test:** asserts the holdout set loads and scores deterministically and
  that the tiered report includes the holdout line. It **does not** assert a holdout
  pass-rate or per-corpus correctness (asserting that would defeat blindness).
- **Report-format tests:** assert the reframed header carries the corpus-level caveat
  and the `k/N corpora correctly classified` headline per tier.
- **Determinism / drift:** if any new corpus is surfaced through the web
  serialization, `web/site/data/` is rebuilt so the demo-data-drift gate stays green.
- All Phase-0/1/2 gates stay green: `ruff`, `mypy`, coverage ≥ 80%, tests ×2,
  demo-data-drift, on Python 3.10–3.12; Pages remains test-gated.

## Build decomposition (Subagent-Driven Development)

Three workstreams. Corpus **authoring** is parallel-friendly (independent JSON
files), but edits to `evaluation.py` serialize across tasks to avoid merge
conflicts. Each task lands via branch → PR → CI → squash-merge; final whole-branch
review on the most capable model before close-out.

- **T1 — tiering + adversarial corpora.** Add the `adv_*.json` (5), the
  `ADVERSARIAL_LABELS` table, the tiered driver scaffold, and per-corpus tests + the
  core-tier regression test. The five corpus files may be authored by parallel
  sub-dispatches (one per perturbation), since they are independent inputs; the
  `evaluation.py` edit is single-threaded within the task.
- **T2 — honest metric reframing.** Reframe the report header/docstring, add the
  per-tier `k/N` headline and the corpus-level caveat, demote `accuracy` out of the
  headline; add report-format tests. Builds on T1's tiered report.
- **T3 — blind holdout.** A fresh subagent authors `data/holdout/hold_*.json` (3)
  from the behavioral contract only (not the matcher internals), then a controller
  task wires `HOLDOUT_LABELS`, the holdout report line, and the load/score test.

## Exit criteria

- 5 adversarial corpora exist and classify correctly (3 TN + 2 TP); the core tier
  still classifies all 5 dynamics corpora correctly; the eval reports three tiers.
- The metrics are reframed as corpus-level discrimination with an explicit `N`, the
  `k/N corpora correctly classified` headline, and the no-generalization caveat;
  `classify_coercive` and the metric dict keys are unchanged; `DocumentaryPrecision`
  stays the only real-data precision claim.
- A frozen, fresh-subagent-authored blind holdout (3 corpora) loads and scores on a
  separate generalization line; its score is reported, not asserted to a target.
- No change to the stage regexes, the state machine, the REFUSAL/LEGITIMACY groups,
  thread grouping, or any other layer — except a surfaced, justified engine fix if a
  corpus exposes a genuine defect (and never a relabel).
- `ruff` / `mypy` / coverage (≥80) / drift green on Python 3.10–3.12; Pages
  test-gated.

## Decisions log (brainstorming, 2026-06-30)

- **Adversarial intent = both directions.** Negative traps (mixed senders, reversed
  chronology, unrelated-pattern contamination) guard false positives; robustness
  positives (interleaved threads, subject mismatch) guard false negatives. Strongest
  proof of the Phase-2 machine.
- **Eval structure = tiered, scored separately.** Core dynamics corpora stay a
  frozen baseline that must hold at perfect discrimination (the behavior-preservation
  guard); the adversarial suite gets its own confusion matrix; the holdout gets its
  own generalization line. A regression in any tier is independently visible.
- **Metric rename = honest naming, math unchanged.** Reframe to corpus-level
  discrimination with explicit `N` and a no-generalization caveat; lead with `k/N`
  correct; keep `classify_coercive` and the dict keys stable; keep
  `DocumentaryPrecision` as the only real-data precision.
- **Holdout blindness = fresh-subagent authored + frozen + separately reported.**
  Authored from the behavioral definition of coercion, not the matcher internals;
  committed once and never edited to chase a score; failures surfaced and analyzed,
  fixed only by a justified engine change. Reported, not asserted to a target.
- **`adv_interleaved_threads` must be harder than `dyn_coercive`'s existing
  interleave** — the coercer also fires stage cues in other threads, so the corpus
  specifically tests that the machine does not stitch a cross-thread envelope.

## Non-goals (Phase 3 — YAGNI)

- No change to the six stage regexes, the state machine, the REFUSAL/LEGITIMACY
  groups, thread grouping, or any other engine layer (barring a surfaced, justified
  defect fix).
- No statistical/sampled-corpus generation, no machine learning, no new metric math
  beyond the existing five quantities.
- No rename of the programmatic metric dict keys (human-facing vocabulary only).
- No UI/demo-architecture separation and no thread-local omission/pattern change —
  those are Phase 4.
