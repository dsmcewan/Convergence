# Refusal + justify vocabulary iteration (recall gap #3)

**Goal:** Close the false negative the fresh blind holdout exposed after the
refusal-vocabulary iteration — a tonsillectomy-consent coercive episode
(`data/holdout/hold_coercive.json`, coercer Derek) that scores non-coercive (3
stage-hits, 0 complete envelopes) because Derek's **entire documentation war is
near-misses across stages 2, 3, AND 5**. Broaden the objection (2), obstruction (3),
and **justify (5)** regexes so both his refusals *and* his borrowed-authority
justifications are tagged; the already-merged `REFUSED→fait` relaxation then completes
the envelope. Vocab-only — no machine change.

**Status:** design approved 2026-06-30 (user: "go with recommendations" on the opus
gap-#3 diagnosis). Follows Phases 0–4, the engine recall-fix, and the refusal-
vocabulary iteration, all merged. Build method: **Subagent-Driven Development**. Repo:
`dsmcewan/Convergence`.

**Scope boundary:** changes only the stage-2, stage-3, and stage-5 regexes in
`convergence/coercion_grammar.py`, `FRAGMENTS.md`, `data/` (rotate the spent holdout →
regression; add a fresh blind holdout), and `convergence/evaluation.py`
(`REGRESSION_LABELS`) + tests. **No** change to stages 1/4/6, `_REFUSAL`/`_LEGITIMACY`,
`_run_envelope`, thread grouping, the 4-tier eval structure, or any other layer. **No**
corpus is relabeled to chase a score.

---

## Context

The refusal-vocabulary iteration (gap #2) closed a travel-consent FN and rotated in a
fresh blind holdout, which immediately surfaced gap #3. Unlike gap #2 (refusal-only),
the opus diagnosis shows gap #3 spans **two** engines: to complete, the coercer needs
both a **refusal** (2/3 → `REFUSED`) and a **legitimacy** (4/5 → `cycles ≥ 1`) before
the fait — and *both* are untagged near-misses of the controlled vocabulary.

Tracing Derek (coercer) against the current stages, his war is invisible:

| seq | Derek | current | missing |
|---|---|---|---|
| 2 | "I don't think that's necessary … **I'm not agreeing** to this." | — | **stage 2** (objection) |
| 4 | "**You don't have the right** to schedule … **the parenting plan is very clear** … my attorney … **she agrees**" | — | **stage 2** + **stage 5** |
| 6 | "**I'm not attending** any appointment … **go through the** co-parenting **coordinator** … that's what **the court requires**" | — | **stage 3** + **stage 5** |
| 8 | "I've already spoken with Dr. Nguyen … backed by a **physician of record**. Consider this matter closed." | 6 (fait, `i've already`) | — |

The near-misses: `i'm not agreeing` (vs `i won't agree`); `you don't have the right`
(sibling of gap-#2's `you don't get to`); `the parenting plan is very clear` (stage-5
keys on `the {policy|agreement|order|schedule} {says|states|requires|stands}`, not
`parenting plan`/`is clear`); `my attorney … agrees` (authority verbs are
`says|said|told me|advised`, not `agrees`); `the court requires` (`court` is not in the
noun group); `i'm not attending` / coordinator-redirect (stage-3 stonewall not in the
lexicon); `physician of record`.

**Verified fix path (ran the patched engine):** with the broadenings, Derek tags
seq2 (stage 2), seq4 (stage 2 + stage 5), seq6 (stage 3 + stage 5), seq8 (stage 6).
The machine: action(Maya, seq1)→OPENED; seq2→REFUSED; seq4 legitimacy→CYCLED
(`cycles=1`); seq6 obstruction→REFUSED then legitimacy→CYCLED (`cycles=2`); seq8 fait
completes via the merged `REFUSED/CYCLED→fait` relaxation. **`coercer=Derek, cycles=2,
complete=True`. No machine change.** And **zero flips** across core (5) + adversarial
(5) + regression (6) — including the bilateral-hostile guards.

## Vocabulary broadening (principled but conservative)

In `convergence/coercion_grammar.py` `STAGES`, broaden stages 2, 3, and 5 only.

- **Stage 2 (objection):** add `i'm not agreeing`, `you don't have the right`.
- **Stage 3 (obstruction):** add `i'm not attending`, `go through the (co-parenting )?coordinator` (coordinator-redirect stonewall).
- **Stage 5 (justify):** add
  - `the (parenting plan|order|court)\b[^.!?]{0,20}\b(requires|clear|states|mandates)\b` — catches `the parenting plan is very clear`, `the court requires`, without the `per the` prefix and beyond the `{policy|agreement|order|schedule}` noun set;
  - the authority verbs `agrees`/`confirms` appended to the existing `my (lawyer|attorney|accountant|doctor)…(says|said|told me|advised)` alternative;
  - `physician of record` / `doctor of record`.
- **`FRAGMENTS.md`:** document the new cues in the stage-2, stage-3, and stage-5 rows.

**Specificity is the watch-point:** stage-5 broadening carries more false-positive
risk than the pure-refusal pass. The bilateral-hostile guards (`dyn_high_conflict`,
`reg_camp_hostile`, `reg_hostile`) and the cooperative corpora are the load-bearing
gates. (Pre-verified: 0 flips, but the implementer must re-confirm under the full
suite.) The existing negative-tagging guards stay
(`test_neutral_message_has_no_stage`, `test_plain_question_is_not_stage_4`, the
prior bare-doubt/affirmative guards).

## Holdout rotation

The current fresh holdout drove this fix, so it is spent as a blind instrument.
Rotate all three:

- **Relocate** `data/holdout/hold_{coercive,cooperative,hostile}.json` →
  `data/regression/reg_medical_coercive.json`, `reg_swim_cooperative.json`,
  `reg_religion_hostile.json` (`git mv`, content unchanged). The two existing
  regression rotations (preschool `reg_coercive` + travel `reg_travel_coercive` and
  their negatives) are left as-is.
- Add the three to `REGRESSION_LABELS` (now 9 entries): `reg_medical_coercive.json: True`,
  `reg_swim_cooperative.json: False`, `reg_religion_hostile.json: False`.
- **Assert:** `reg_medical_coercive` now *completes* (the fix target — passes only
  after the vocabulary broadening); `reg_swim_cooperative` and `reg_religion_hostile`
  stay non-coercive. `reg_religion_hostile` (a bilateral First-Communion dispute) is a
  key specificity guard for the stage-5 broadening.
- **Author a fresh 3-corpus blind holdout** at `data/holdout/hold_*.json` via a
  subagent quarantined from the matcher. `HOLDOUT_LABELS` keeps the `hold_*` names;
  reported, not asserted.

## Hard gates (every task)

- Core tier: the 5 `dyn_*` corpora classify perfectly (1 TP + 4 TN).
- Adversarial tier: 3 TN + 2 TP.
- The **existing** regression corpora (the preschool + travel sets, 6 corpora) still
  pass.
- `ruff`, `mypy`, coverage ≥ 80%, demo-data-drift, on Python 3.10–3.12; Pages
  test-gated.
- A flipped core/adversarial/existing-regression negative is a surfaced finding (the
  stage-5 broadening is too greedy), **never** fixed by editing a corpus.

## Testing

- **Stage-2/3/5 tagging tests:** positive — `i'm not agreeing` → stage 2,
  `you don't have the right` → stage 2, `i'm not attending` → stage 3,
  `the parenting plan is very clear` → stage 5, `my attorney … agrees` → stage 5,
  `the court requires` → stage 5; negative guards — the new cues do not fire on benign
  fragments, and the pre-existing neutral/plain-question/bare-doubt guards stay green.
- **Regression-tier tests:** `reg_medical_coercive` completes; `reg_swim_cooperative`
  and `reg_religion_hostile` stay non-coercive; the existing preschool + travel sets
  still hold; the regression confusion is `(tp=3, fp=0, fn=0, tn=6)` over the 9.
- **Fresh holdout:** loads and scores deterministically; report includes the holdout
  section; **no** assertion of holdout correctness/score.

## Build decomposition (Subagent-Driven Development)

Two tasks; each branch (from `origin/main`) → PR → CI → squash-merge; final whole-
branch review on the most capable model before close-out.

- **T1 — refusal + justify vocabulary.** Broaden the stage-2/3/5 regexes (with the
  negative guards) + update `FRAGMENTS.md` + tagging tests. Core + adversarial +
  existing-regression gates must hold (watch the bilateral-hostile and cooperative
  corpora under the stage-5 broadening).
- **T2 — holdout rotation.** `git mv` the 3 spent holdout corpora → `data/regression/`
  (descriptive names, content unchanged); add the 3 `REGRESSION_LABELS`; assert
  `reg_medical_coercive` completes + the 2 new negatives don't; author the fresh blind
  holdout (quarantined subagent); keep `HOLDOUT_LABELS` reported-not-asserted.

## Exit criteria

- `reg_medical_coercive` (the former blind FN, content unchanged) now **completes**
  (coercer Derek, `cycles ≥ 1`); the two new regression negatives stay non-coercive;
  the existing preschool + travel regression sets still hold.
- Core tier perfect; adversarial 3 TN + 2 TP (the stage-2/3/5 broadening introduced no
  false positive — especially on the bilateral-hostile and cooperative corpora).
- A fresh quarantined-subagent-authored blind holdout (3 corpora) loads and scores on
  the generalization line, reported not asserted.
- New cues documented in `FRAGMENTS.md`; `_run_envelope` and stages 1/4/6 unchanged.
- `ruff` / `mypy` / coverage (≥80) / drift green on 3.10–3.12; `evaluate_dynamics` and
  metric dict keys unchanged (no web drift).

## Decisions log (2026-06-30)

- **Vocab-only; no machine change** — the merged `REFUSED→fait` relaxation completes
  the envelope once both a refusal and a legitimacy are tagged.
- **Cross-stage (2/3/5) broadening** — gap #3 is NOT refusal-only; the coercer needs a
  legitimacy (4/5) for `cycles ≥ 1`, so stage 5 must broaden too. (Verified: a
  refusal-only pass would leave `cycles=0` and still FN.)
- **Principled but conservative**, with stage-5's higher FP risk gated by the
  bilateral-hostile corpora. Pre-verified 0 flips on the full corpus set.
- **Full rotation** — all three spent-holdout corpora become asserted regression
  corpora; a fresh blind holdout re-establishes the generalization measure.
- **Scenario-based regression names** alongside the existing sets; no rename.

## Non-goals (YAGNI)

- No machine change; no change to stages 1/4/6, the REFUSAL/LEGITIMACY groups, thread
  grouping, or any other layer.
- No metric/eval-structure change; no statistical/ML scoring.
- No relabeling or editing of any existing corpus to change a classification.
