# Refusal-engine vocabulary iteration (recall gap #2)

**Goal:** Close the false negative the *fresh* blind holdout exposed after the first
recall-fix — a travel-consent coercive episode (`data/holdout/hold_coercive.json`,
coercer Derek) that scores non-coercive (8 stage-hits, 0 complete envelopes) because
Derek produces **zero refusal-stage (2/3) hits**. Broaden the refusal engine
(stage-2 objection, stage-3 obstruction) vocabulary so his objections are tagged;
the already-merged `REFUSED→fait` completion relaxation then completes the envelope.
Vocab-only — no machine change.

**Status:** design approved 2026-06-30. Follows Phases 0–4 and the first engine
recall-fix, all merged. Build method: **Subagent-Driven Development**. Repo:
`dsmcewan/Convergence`.

**Scope boundary:** changes only the stage-2 and stage-3 regexes in
`convergence/coercion_grammar.py`, `FRAGMENTS.md` (the documented cues), `data/`
(rotate the spent holdout → regression; add a fresh blind holdout), and
`convergence/evaluation.py` (`REGRESSION_LABELS`) + tests. **No** change to stages
1/4/5/6, `_REFUSAL`/`_LEGITIMACY`, `_run_envelope`, thread grouping, the 4-tier eval
structure, or any other layer. **No** corpus is relabeled to chase a score.

---

## Context

The first recall-fix closed gap #1 (a preschool-enrollment coercive episode missed on
both vocabulary and the `refuse→fait` machine ending) and rotated in a fresh blind
holdout. That holdout immediately surfaced gap #2: the fresh `hold_coercive.json` (a
spring-break travel-consent dispute) is genuinely coercive — Rachel proposes a
plan-sanctioned trip; Derek refuses consent, invokes the order/his attorney, refuses
to discuss, then announces a unilateral done-deal — yet it scores non-coercive.

Tracing Derek's messages against the current stages shows the gap is purely the
**refusal engine**:

| seq | Derek (coercer) | tags now | missing |
|---|---|---|---|
| 2 | "I don't think so. … I already told Mia" | 6 (fait, `i already`) | **stage 2** (objection) |
| 4 | "You don't get to just decide … I'm not giving consent" | 5 (`the order requires`) | **stage 2** |
| 6 | "There's nothing to talk through … not in her best interest … my attorney says" | 5 (`best interest`, `my attorney says`) | **stage 3** (obstruction) |
| 8 | "I've made my decision and it's final" | 6 (fait, `it's final`) | — |

Derek has stage-5 and stage-6 hits but **no stage-2/3 refusal**, so the ordered
machine never leaves `OPENED` (a refusal is required to reach `REFUSED`), `cycles`
stays 0, and nothing completes. The stage-2/3 vocabulary is the narrowest part of the
lexicon — the first recall-fix enriched objection-doubt, legitimacy, and fait, but
plain refusals/stonewalls remained overfit to the original corpora.

**Verified fix path:** with seq2 ("I don't think so") tagging **stage 2**, the machine
goes OPENED → REFUSED; seq4's legitimacy ("the order requires") → CYCLED (`cycles=1`);
seq8's fait ("it's final") completes via the already-merged `REFUSED/CYCLED → fait`
relaxation. Coercer = Derek, `cycles ≥ 1`, complete. **No machine change is needed.**

## Vocabulary broadening (principled but conservative)

In `convergence/coercion_grammar.py` `STAGES`, broaden stages 2 and 3 only. Add
unambiguous refusal/stonewall markers; avoid ultra-common bare fragments.

- **Stage 2 (objection):** add `i don't think so`; consent refusals `i'm not giving
  consent` / `i won't consent` / `i'm not consenting` / `i'm not signing off`;
  authority/standing refusals `you don't get to` / `you can't just`.
- **Stage 3 (obstruction):** add refusal-to-engage `nothing to talk through` /
  `there's nothing to talk about`; `i'm not discussing this` / `i won't discuss`.
- **`FRAGMENTS.md`:** document the new cues in the stage-2 and stage-3 rows
  (provenance discipline — the catalog must not drift from the lexicon).

**Specificity guards (must stay green):** the existing negative-tagging guards stay
(`test_neutral_message_has_no_stage`, `test_plain_question_is_not_stage_4`,
the bare-`I don't know`/`I'm not sure` exclusions from the first recall-fix). New
negative tests assert the broadened cues do not fire on benign fragments.

## Holdout rotation

The current fresh blind holdout drove this fix (its misses are now known), so it is
spent as a blind instrument. Rotate all three:

- **Relocate** `data/holdout/hold_{coercive,cooperative,hostile}.json` →
  `data/regression/reg_travel_coercive.json`, `data/regression/reg_dental_cooperative.json`,
  `data/regression/reg_camp_hostile.json` (`git mv`, **content unchanged**). The
  existing first-rotation regression corpora (`reg_coercive`/`reg_cooperative`/`reg_hostile`,
  the preschool set) are left as-is — no rename, no churn.
- Add the three to `REGRESSION_LABELS` (now 6 entries): `reg_travel_coercive.json: True`,
  `reg_dental_cooperative.json: False`, `reg_camp_hostile.json: False`.
- **Assert:** `reg_travel_coercive` now *completes* (the fix target — passes only
  after the vocabulary broadening); `reg_dental_cooperative` and `reg_camp_hostile`
  stay non-coercive. **`reg_camp_hostile` is the load-bearing specificity guard** —
  broadening refusal vocabulary most risks a bilateral-hostile corpus (both parties
  refuse) flipping to a false positive; this assertion catches it.
- **Author a fresh 3-corpus blind holdout** at `data/holdout/hold_*.json` (coercive /
  cooperative / hostile) via a subagent quarantined from the matcher internals (same
  discipline as before — no `coercion_grammar.py`, no regexes, no existing corpora).
  `HOLDOUT_LABELS` keeps the `hold_*` names; the holdout is **reported, not asserted**.

## Hard gates (every task)

- Core tier: the 5 `dyn_*` corpora classify perfectly (1 TP + 4 TN).
- Adversarial tier: 3 TN + 2 TP.
- The **existing** regression corpora (the preschool `reg_coercive` and its two
  negatives) still pass.
- `ruff`, `mypy`, coverage ≥ 80%, demo-data-drift, on Python 3.10–3.12; Pages
  test-gated.
- A flipped core/adversarial/existing-regression negative is a surfaced finding
  (the broadening is too greedy), **never** fixed by editing a corpus.

## Testing

- **Stage-2/3 tagging tests:** positive — `i don't think so` → stage 2,
  `i'm not giving consent` → stage 2, `you don't get to` → stage 2,
  `nothing to talk through` → stage 3; negative guards — the new cues do not fire on
  benign fragments, and the pre-existing neutral/plain-question/bare-doubt guards stay
  green.
- **Regression-tier tests:** `reg_travel_coercive` completes; `reg_dental_cooperative`
  and `reg_camp_hostile` stay non-coercive; the existing preschool regression trio
  still holds; the regression confusion is `(tp=2, fp=0, fn=0, tn=4)` over the 6.
- **Fresh holdout:** loads and scores deterministically; report includes the holdout
  section; **no** assertion of holdout correctness/score.

## Build decomposition (Subagent-Driven Development)

Two tasks; each branch → PR → CI → squash-merge; final whole-branch review on the most
capable model before close-out.

- **T1 — refusal vocabulary.** Broaden the stage-2/3 regexes (with the negative
  guards) + update `FRAGMENTS.md` + tagging tests. Core + adversarial + existing-
  regression gates must hold. (T1 does not assert the travel corpus completes — that
  is wired in T2; but after T1 the engine *does* complete it, which the T2 regression
  assertion then locks.)
- **T2 — holdout rotation.** `git mv` the 3 spent holdout corpora → `data/regression/`
  (descriptive names, content unchanged); add the 3 `REGRESSION_LABELS`; assert
  `reg_travel_coercive` completes and the 2 new negatives don't; author the fresh blind
  holdout (quarantined subagent); keep `HOLDOUT_LABELS` reported-not-asserted.

## Exit criteria

- `reg_travel_coercive` (the former blind FN, content unchanged) now **completes**
  (coercer Derek, `cycles ≥ 1`); the two new regression negatives stay non-coercive;
  the existing preschool regression trio still holds.
- Core tier perfect; adversarial 3 TN + 2 TP (the refusal broadening introduced no
  false positive on the guards — especially the bilateral-hostile corpora).
- A fresh quarantined-subagent-authored blind holdout (3 corpora) loads and scores on
  the generalization line, reported not asserted.
- New cues documented in `FRAGMENTS.md`; `_run_envelope` and stages 1/4/5/6 unchanged.
- `ruff` / `mypy` / coverage (≥80) / drift green on 3.10–3.12; `evaluate_dynamics` and
  metric dict keys unchanged (no web drift).

## Decisions log (brainstorming, 2026-06-30)

- **Vocab-only; no machine change.** The merged `REFUSED→fait` relaxation already
  completes a `refuse→fait` ending; this gap is purely missing refusal vocabulary.
- **Principled but conservative broadening.** Add unambiguous refusal/stonewall
  markers; avoid bare ultra-common fragments. Gated by core + adversarial + the
  bilateral-hostile regression corpus.
- **Full rotation.** All three spent-holdout corpora become asserted regression
  corpora (the hostile negative is the key specificity guard); a fresh blind holdout
  re-establishes the generalization measure.
- **Scenario-based regression names** alongside the existing `reg_coercive`/etc.; no
  rename of the first-rotation set.

## Non-goals (YAGNI)

- No machine change; no change to stages 1/4/5/6, the REFUSAL/LEGITIMACY groups,
  thread grouping, or any other layer.
- No metric/eval-structure change (the 4-tier eval already exists); no statistical/ML
  scoring.
- No relabeling or editing of any existing corpus to change a classification.
