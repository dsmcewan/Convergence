# Engine recall-fix phase — close the holdout-exposed coercion recall gap

**Goal:** Make the coercion discriminator detect genuinely-coercive episodes the
current engine misses, as proven by the Phase-3 **blind holdout** (`hold_coercive`,
a textbook coercive conversation, classified non-coercive). This is the **first
phase that deliberately changes engine matching logic** — Phases 1–3 kept
`convergence/coercion_grammar.py` frozen on purpose. The change is two-part
(vocabulary + state machine) and is guarded harder than any prior phase.

**Status:** design approved 2026-06-30. Follows Phases 0 (tooling/web hardening),
1 (Signal provenance), 2 (sender-aware ordered state machine), 3 (evaluation
honesty), all merged. Build method: **Subagent-Driven Development**. Repo:
`dsmcewan/Convergence`.

**Why now:** Phase 3 deliberately built the guard rails (adversarial suite + blind
holdout + tiered eval) *before* touching engine logic. Those rails now exist, so an
engine change can be made safely: any regression shows up as a tier moving.

**Scope boundary:** changes only `convergence/coercion_grammar.py` (stage-2/5/6
regexes + the `_run_envelope` completion transition), `convergence/evaluation.py`
(new regression tier + report), `FRAGMENTS.md` (new cues documented), `data/`
(relocate the known holdout → regression; add a fresh blind holdout), and tests.
**No** new stages; **no** change to stages 1/3/4, the `_REFUSAL`/`_LEGITIMACY`
groupings, thread grouping, `match_grammar`'s candidate/skip logic, or any other
engine layer. **No** corpus is relabeled or edited to chase a score.

---

## Context

The Phase-3 blind holdout exposed a real recall gap, confirmed by the opus final
review: the discriminator is overfit to `dyn_coercive`'s exact phrasings.
`data/holdout/hold_coercive.json` is genuinely coercive — proposer Danielle seeks a
joint preschool decision; coercer Ryan objects, invokes attorney/parenting-plan
authority, objects again, then announces a unilateral fait (*"I enrolled Mia at
Bright Beginnings this morning"*) — yet it scored non-coercive (2 stage-hits, 0
complete envelopes). Specificity held (both holdout negatives correct).

Tracing `hold_coercive` through the live machine shows **two independent gaps**;
closing either alone does nothing:

1. **Vocabulary.** Ryan's moves go untagged: the bare first-person fait
   (`I enrolled Mia`, not `I've enrolled`), `per the parenting plan` (the regex
   wants agreement/order/policy), de-adjacent authority (`my attorney … she said`,
   the regex wants adjacency), `I don't think Montessori is right`, and the soft
   opening objection (`I'm not really sure about that place`).
2. **State machine.** Even fully tagged, Ryan's envelope ends `… refuse(seq6) →
   fait(seq8)`, but `_run_envelope` only completes a fait from the `CYCLED` state.
   Any episode ending `refuse → fait` (a fait after a final objection) is missed.

The traced completion path that this phase enables (coercer = Ryan): action(seq1,
Danielle) → OPENED; Ryan objection(seq2) → REFUSED; Ryan legitimacy(seq4) → CYCLED
(cycles=1); Ryan objection(seq6) → REFUSED; Ryan fait(seq8) → **COMPLETE** (requires
both the vocabulary fix, so seq2/4/6/8 tag, and the machine fix, so the fait
completes from REFUSED with cycles≥1).

## Vocabulary broadening (principled, with guards)

In `convergence/coercion_grammar.py` `STAGES`, broaden three stage patterns. Keep
them controlled and documented; the engine's philosophy is that a single stage is
deniable and the *envelope shape* carries the weight, but specificity is still
protected by the gates below.

- **Stage 6 (fait_accompli):** add **past-tense, affirmative, first-person** faits —
  `I (enrolled|booked|registered|scheduled|withdrew|signed up|switched|moved) …`.
  Past-tense-only makes it **negation-safe by construction**: Danielle's present-
  continuous negated "I'm **not** enrolling her without you" and Ryan's future
  "I'm **going to** look at Bright Beginnings" do **not** match. (The existing
  contracted forms `i've enrolled` / `she's enrolled` / `i went ahead and` etc.
  remain.)
- **Stage 5 (justify/legitimacy):** add `per the parenting plan` alongside the
  existing `per the (agreement|order|policy)`; and allow **de-adjacent borrowed
  authority** — `my (lawyer|attorney|accountant|doctor) … (said|told me|advised)`
  with a **bounded** intervening gap (≤ ~40 chars, no sentence-crossing) so "my
  attorney **and she** said" matches while keeping the match local.
- **Stage 2 (objection):** add clear objections — `I don't think <X> is
  (right|appropriate|a good idea|the right …)` — plus **scoped** soft-doubt directed
  at a proposal: `I'm not sure about <that|this|it|…>` and `I don't know anything
  about <…>`. **Exclude** bare standalone `I don't know` / `I'm not sure` (too
  benign — they appear constantly in cooperative talk).
- **`FRAGMENTS.md`:** document the new cues under their stages (provenance is the
  point of this engine; the catalog must not drift from the lexicon).

**False-positive guards that must stay green:** `test_neutral_message_has_no_stage`
("Thanks, see you Saturday at five." → no stage) and `test_plain_question_is_not_stage_4`
("What time is pickup on Saturday?" → not stage 4). New negative tests are added
(below).

## Machine relaxation

In `_run_envelope`, broaden exactly one completion transition. Today:

```python
elif state == "CYCLED" and h.stage == 6 and cycles >= 1:
    state = "COMPLETE"; break
```

Becomes:

```python
elif state in ("REFUSED", "CYCLED") and h.stage == 6 and cycles >= 1:
    state = "COMPLETE"; break
```

**Principle:** once at least one ordered refuse→legitimize round has occurred
(`cycles ≥ 1`), the documentation war is established; a fait terminates it whether or
not a final objection immediately precedes it. The war-round bar is preserved: a
fait with `cycles == 0` (e.g. action→refuse→fait, no completed round) still does
**not** complete, and a fait in the `OPENED` state (no war at all) still does not
complete. `cycles` counting is unchanged; only the completion *condition* widens.

**Verified safe against the known negatives** (none reaches `cycles ≥ 1` with its own
fait, so none flips): `adv_mixed_senders` (Victor cycles=1 but no Victor fait; Pat
has fait but cycles=0), `adv_reversed_chronology` (action last → never past OPENED),
`adv_unrelated_contamination` (cycles=0), and the `test_bilateral_hostility…` unit
test (neither party has a round-plus-own-fait). **Residual risk — the core hard
negative `dyn_high_conflict`:** it is hostile and bilateral with many stage hits; if
any sender there has a completed round plus a later own fait, the relaxation could
flip it to a false positive. The **core-tier gate (must stay perfect) is the hard
proof.** If it flips, the relaxation is too loose — surface it (sender + seqs +
trace) and stop; do not weaken the corpus.

## Tier restructure (holdout rotation)

The current holdout's misses are now known (read during this design and the Phase-3
review), so it is "spent" as a blind instrument. Rotate:

- **Relocate** `data/holdout/hold_{coercive,cooperative,hostile}.json` →
  `data/regression/reg_{coercive,cooperative,hostile}.json` (`git mv`, **content
  unchanged**). These become the **known regression set**. Add `REGRESSION_LABELS`
  in `convergence/evaluation.py` (`reg_coercive.json: True`,
  `reg_cooperative.json: False`, `reg_hostile.json: False`).
- **Author a fresh blind holdout** at `data/holdout/hold_*.json` (3 corpora:
  coercive / cooperative / hostile) by a subagent **quarantined from the matcher
  internals** (same discipline as Phase 3 — no `coercion_grammar.py`, no regexes, no
  existing corpora). Wire `HOLDOUT_LABELS` to the fresh set.
- The tiered eval/report grows to **core / adversarial / regression / holdout**.
  `evaluate_tiered` returns the four tiers; `format_tiered_report` renders four
  sections. `evaluate_dynamics` and `EvalResult.metrics` keys stay unchanged (web
  drift guard).

**Assertion discipline by tier:**
- **regression** — ASSERTED: `reg_coercive` must now *complete* (the recall-fix
  target; passes only after both the vocabulary and machine fixes); `reg_cooperative`
  and `reg_hostile` must stay non-coercive (specificity regression guards).
- **holdout** — REPORTED, NOT asserted to a target (asserting it would re-introduce a
  tuning signal and defeat blindness — same rule as Phase 3). The test asserts only
  deterministic load/score and that the report includes the holdout section.

## Eval-module changes (`convergence/evaluation.py`)

- Add `REGRESSION_LABELS: dict[str, bool]`; repoint `HOLDOUT_LABELS` to the fresh
  set (filenames unchanged: `hold_coercive/cooperative/hostile.json`, new content).
- Extend `TieredEval` with a `regression: EvalResult` field (alongside
  `core/adversarial/holdout`); `evaluate_tiered` scores it via the existing
  `evaluate_labelset(data_dir / "regression", REGRESSION_LABELS)`.
- `format_tiered_report` renders the regression tier (asserted) and the holdout tier
  (reported) as distinct sections, each with the existing honest `k/N` headline +
  caveat.
- `evaluate`, `metrics`, `EvalResult.metrics` keys, `evaluate_dynamics`,
  `classify_coercive`, `documentary_precision` unchanged.

## Testing

- **Hard gates (must hold):** core tier classifies all 5 dynamics corpora perfectly
  (the behavior-preservation tripwire — now also proving the engine change did not
  regress the dynamics discrimination); adversarial 3 TN + 2 TP; `ruff`, `mypy`,
  coverage ≥ 80%, demo-data-drift, on Python 3.10–3.12; Pages test-gated.
- **Vocabulary tests (T1):** for each new cue, a positive stage-tagging assertion
  (`I enrolled Mia` → stage 6; `per the parenting plan` → stage 5; `my attorney and
  she said` → stage 5; `I don't think X is right` → stage 2; `I'm not sure about
  that place` → stage 2). Negative guards: `I'm not enrolling her` must **not** tag
  stage 6; bare `I don't know` / `I'm not sure` must **not** tag stage 2; the
  existing neutral-message and plain-question guards stay green.
- **Machine tests (T2):** an envelope ending `action → refuse → legitimize → refuse
  → fait` **completes** (cycles ≥ 1, fait from REFUSED); `action → refuse → fait`
  with no completed round does **not** complete; the existing
  `test_complete_envelope_detected`, `test_cycles_counted` (==2),
  `test_fait_accompli_alone_is_not_complete`, `test_incomplete_without_fait_accompli`
  stay green unchanged.
- **Regression tier (T3):** `reg_coercive` completes (asserted — green only after
  T1+T2); `reg_cooperative` and `reg_hostile` stay non-coercive.
- **Fresh holdout (T3):** loads + classifies deterministically; report includes the
  holdout section; **no** assertion of holdout correctness/score.

## Build decomposition (Subagent-Driven Development)

Three tasks; each branch → PR → CI → squash-merge; final whole-branch review on the
most capable model before close-out. T1→T2 are sequential (same file
`coercion_grammar.py`); T3 depends on T1+T2 (its `reg_coercive` assertion passes only
once both engine fixes are in).

- **T1 — vocabulary broadening.** Broaden stage-2/5/6 regexes (with the negation and
  scoping guards) + update `FRAGMENTS.md` + stage-tagging tests (positive + negative
  guards). Core + adversarial gates must hold. (T1 does **not** assert `reg_coercive`
  completes — that needs T2.)
- **T2 — machine relaxation.** Widen the `_run_envelope` completion transition +
  completion unit tests. Core + adversarial gates must hold.
- **T3 — tier rotation.** `git mv` holdout → `data/regression/` (content unchanged);
  add `REGRESSION_LABELS`; author the fresh blind holdout via a quarantined subagent;
  repoint `HOLDOUT_LABELS`; extend `TieredEval`/`evaluate_tiered`/
  `format_tiered_report` to four tiers; assert the regression tier; report the
  holdout tier.

## Exit criteria

- `reg_coercive` (the former blind FN, content unchanged) now **completes**; the two
  regression negatives stay non-coercive.
- The core tier still classifies all 5 dynamics corpora perfectly; the adversarial
  suite stays 3 TN + 2 TP (engine change introduced no false positives on the
  guards).
- A fresh, quarantined-subagent-authored blind holdout (3 corpora) loads and scores
  on a separate generalization line, reported not asserted.
- New cues documented in `FRAGMENTS.md`; the negation/benign guards pass;
  `_run_envelope` completes `refuse → fait` only when `cycles ≥ 1`.
- `ruff` / `mypy` / coverage (≥80) / drift green on 3.10–3.12; `evaluate_dynamics`
  and metric dict keys unchanged (no web drift).

## Decisions log (brainstorming, 2026-06-30)

- **Holdout rotation:** the spent holdout becomes an asserted **regression** set
  (`reg_coercive` must complete); a **fresh blind holdout** re-establishes an honest
  generalization measure (reported, not asserted).
- **Broadening = principled but conservative:** cover the general phenomenon, not
  `hold_coercive`'s exact strings; exclude bare `I don't know`/`I'm not sure`; the
  scoped soft-doubt (`I'm not sure about X`) is included because promoting
  `hold_coercive` requires tagging its soft opening objection (seq2) so an ordered
  refuse→legitimize round exists.
- **Machine relaxation included:** the gap is both vocabulary and machine; a fait
  completes from REFUSED or CYCLED once `cycles ≥ 1`. Vocabulary alone cannot close
  it (the envelope ends `refuse → fait`).
- **Tier naming:** `data/regression/` = known/asserted; `data/holdout/` = currently
  blind/reported. "Holdout" always means the current blind set.
- **Discipline:** a flipped core/adversarial negative is a surfaced finding (the
  relaxation or a cue is too loose), never fixed by editing a corpus.

## Non-goals (YAGNI)

- No new stages; no change to stages 1/3/4, the REFUSAL/LEGITIMACY groups, thread
  grouping, `match_grammar`'s candidate/skip logic, or any other layer.
- No metric-math changes; no statistical/ML scoring.
- No UI/demo-architecture work or thread-local omission/pattern (Phase 4).
- No relabeling or editing of any existing corpus to change a classification.
