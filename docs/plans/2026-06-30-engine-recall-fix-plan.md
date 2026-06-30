# Engine recall-fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the coercion-detector recall gap the Phase-3 blind holdout exposed, by broadening three stage regexes and relaxing one state-machine completion transition — so a genuinely-coercive episode ending `refuse → fait` is detected.

**Architecture:** Two engine changes in `convergence/coercion_grammar.py` (vocabulary in `STAGES`; one completion transition in `_run_envelope`), then a tier rotation in `convergence/evaluation.py` + `data/` that promotes the now-known holdout to an asserted regression set and re-establishes a fresh blind holdout. Guarded by the Phase-3 tiers: core stays perfect, adversarial stays 3 TN + 2 TP.

**Tech Stack:** Python 3.10–3.12, stdlib only (`re`, `json`, `dataclasses`, `pathlib`); pytest; ruff; mypy. No new dependencies.

## Global Constraints

- **Engine scope:** change ONLY the stage-2/5/6 regexes and the one `_run_envelope` completion transition in `convergence/coercion_grammar.py`. Do NOT change stages 1/3/4, the `STAGES` structure, `_REFUSAL`/`_LEGITIMACY` (`{2,3}`/`{4,5}`), `tag_stages`, `match_grammar`'s candidate/skip logic, thread grouping, or any other layer/file.
- **Hard gates (must stay green after EVERY task):** the core tier classifies all 5 `dyn_*` corpora perfectly (1 TP + 4 TN); the adversarial suite stays 3 TN + 2 TP; `ruff`, `mypy`, coverage ≥ 80% (`--cov-fail-under=80`), demo-data-drift (`python -m web.build && git diff --exit-code web/site/data/`), on Python 3.10/3.11/3.12; Pages test-gated.
- **A flipped core/adversarial negative is a surfaced finding, never fixed by editing a corpus.** If a gate goes red because a corpus now mis-classifies, STOP, report the corpus + message seqs + `match_grammar` trace, set BLOCKED. Do not weaken the corpus or the test.
- **`classify_coercive` signature, `evaluate`, `metrics`, `EvalResult.metrics` dict keys (`precision/recall/f1/specificity/accuracy`), `evaluate_dynamics`, `documentary_precision` stay unchanged** (web-drift guard — `web/serialize.py` calls `evaluate_dynamics` and serializes the metrics dict, not report text).
- **Negation/scoping guards (verbatim intent):** stage-6 additions are **past-tense affirmative first-person only** (`I enrolled` matches; `I'm not enrolling`, `I'm going to look`, `I didn't enroll` must NOT). Stage-2 soft-doubt is **scoped** (`I'm not sure about X`, `I don't know anything about it` match; bare `I don't know` / `I'm not sure` must NOT). Stage-5 authority allows a **bounded** intervening gap (no sentence crossing).
- **Holdout discipline:** the fresh blind holdout is authored by a subagent quarantined from the matcher (no `coercion_grammar.py`, no regexes, no existing corpora); committed once; **reported, not asserted to a target**. The regression set (`reg_*`) IS asserted.
- **Corpus JSON shape:** each message object has EXACTLY `seq`(int), `thread`(str), `sender`(str), `timestamp`(str), `domain`(str), `body`(str). No extra keys.
- **SDD mechanics:** controller pre-creates each branch; implementer commits locally with explicit `git add <paths>` (never `git add -A`); push → PR → CI → squash-merge per task. `.superpowers/` is gitignored. T1→T2 sequential (same file); T3 depends on T1+T2 merged.

---

## File Structure

- `convergence/coercion_grammar.py` (modify) — T1: stage-2/5/6 regexes in `STAGES`. T2: one transition in `_run_envelope`.
- `FRAGMENTS.md` (modify) — T1: document the new cues in the stage table.
- `tests/test_coercion_grammar.py` (modify) — T1: stage-tagging tests (positive cues + negation/benign guards). T2: completion unit tests.
- `convergence/evaluation.py` (modify) — T3: `REGRESSION_LABELS`, repointed `HOLDOUT_LABELS`, `TieredEval.regression`, `evaluate_tiered`, `format_tiered_report` (4 tiers).
- `data/regression/reg_{coercive,cooperative,hostile}.json` (moved, T3) — `git mv` from `data/holdout/`, content unchanged.
- `data/holdout/hold_{coercive,cooperative,hostile}.json` (new content, T3) — fresh blind set authored by a quarantined subagent.
- `tests/test_regression_corpora.py` (new, T3) — asserts `reg_coercive` completes, `reg` negatives don't.
- `tests/test_holdout_corpora.py` (unchanged behavior, T3) — still loads/scores the (now-fresh) `hold_*` set deterministically; no target assertion.

---

## Task 1: Vocabulary broadening

**Files:**
- Modify: `convergence/coercion_grammar.py` (the `STAGES` tuple — stage 2, 5, 6 patterns only)
- Modify: `FRAGMENTS.md` (stage table rows 2, 5, 6)
- Test: `tests/test_coercion_grammar.py` (add tagging tests)

**Interfaces:**
- Consumes (unchanged): `tag_stages(messages) -> list[StageHit]` (StageHit has `.stage`, `.name`, `.sender`), `STAGES`.
- Produces: broadened stage-2/5/6 matching. No new symbols.

- [ ] **Step 1: Write the failing tagging tests**

Add to `tests/test_coercion_grammar.py` (the `_msg` helper already exists there):

```python
# --- vocabulary broadening (recall fix) ------------------------------------

def test_bare_first_person_fait_tags_stage6():
    assert any(h.stage == 6 for h in tag_stages([_msg(1, "I enrolled Mia at Bright Beginnings this morning. She starts September 4th.")]))  # noqa: E501


def test_negated_enrolling_does_not_tag_stage6():
    # "I'm not enrolling" (present-continuous, negated) is NOT a fait accompli
    assert all(h.stage != 6 for h in tag_stages([_msg(1, "I'm not enrolling her without you. I'm trying to include you.")]))  # noqa: E501


def test_future_intent_does_not_tag_stage6():
    assert all(h.stage != 6 for h in tag_stages([_msg(1, "I'm going to look at Bright Beginnings this week.")]))  # noqa: E501


def test_per_the_parenting_plan_tags_stage5():
    assert any(h.stage == 5 for h in tag_stages([_msg(1, "Per the parenting plan, major decisions require my agreement.")]))  # noqa: E501


def test_de_adjacent_authority_tags_stage5():
    assert any(h.stage == 5 for h in tag_stages([_msg(1, "I talked to my attorney and she said this is my call.")]))  # noqa: E501


def test_i_dont_think_x_is_right_tags_stage2():
    assert any(h.stage == 2 for h in tag_stages([_msg(1, "I don't think Montessori is the right approach for Mia.")]))  # noqa: E501


def test_scoped_soft_doubt_tags_stage2():
    assert any(h.stage == 2 for h in tag_stages([_msg(1, "I'm not really sure about that place. I don't know anything about it.")]))  # noqa: E501


def test_bare_dont_know_does_not_tag_stage2():
    # bare uncertainty is benign and must NOT be an objection
    assert all(h.stage != 2 for h in tag_stages([_msg(1, "I don't know. Let me check and get back to you.")]))  # noqa: E501


def test_bare_not_sure_does_not_tag_stage2():
    assert all(h.stage != 2 for h in tag_stages([_msg(1, "I'm not sure. Either day works for me though.")]))  # noqa: E501
```

- [ ] **Step 2: Run to verify they fail**

Run: `python -m pytest tests/test_coercion_grammar.py -k "fait or stage5 or stage2 or doubt or authority or parenting" -v`
Expected: the positive tests FAIL (new cues not yet matched); the negation/benign tests may already pass (they assert absence) — that is fine, they are guards.

- [ ] **Step 3: Broaden the stage-2, stage-5, stage-6 regexes**

In `convergence/coercion_grammar.py`, replace the stage 2, 5, and 6 `_Stage(...)` entries in `STAGES` with these (stages 1, 3, 4 and `_REFUSAL`/`_LEGITIMACY` unchanged):

```python
    _Stage(2, "objection", re.compile(
        r"\b(i object\b|don't agree|do not agree|i disagree|that won't work|"
        r"that's not acceptable|that is not acceptable|i'm not comfortable|"
        r"i am not comfortable|i won't agree|i refuse|that's not happening|"
        r"i don't think[^.!?]{0,40}\b(right|appropriate|a good idea)\b|"
        r"i'm not[^.!?]{0,12}sure about\b|i don't know anything about\b)\b")),
```

```python
    _Stage(5, "justify", re.compile(
        r"\b(i'm only trying to|i'm just trying to|i am only trying to|"
        r"for (her|his|their) safety|in (her|his) best interest|because the|because my|"
        r"the (policy|agreement|order|schedule) (says|states|requires|stands)|"
        r"my (lawyer|attorney|accountant|doctor)\b[^.!?]{0,40}\b(says|said|told me|advised)\b|"
        r"pursuant to|per the (agreement|order|policy|parenting plan|plan))\b")),
```

```python
    _Stage(6, "fait_accompli", re.compile(
        r"\b(i've already|i already|i went ahead and|it's already done|it's done|"
        r"it's final|it's settled|she's now (enrolled|registered|signed up)|"
        r"she's enrolled|we've moved|we've relocated|"
        r"i've (enrolled|booked|switched|withdrawn|moved|scheduled)|"
        r"i (enrolled|booked|registered|scheduled|withdrew|switched|moved|signed (her|him|them) up)\b|"
        r"too late now|too late to|there's nothing to discuss|nothing to discuss|"
        r"the decision is made|the decision has been made)\b")),
```

- [ ] **Step 4: Run the tagging tests to verify they pass**

Run: `python -m pytest tests/test_coercion_grammar.py -v`
Expected: PASS — all new tagging tests green, AND the pre-existing stage tests (`test_objection_stage`, `test_justify_stage`, `test_fait_accompli_stage`, `test_neutral_message_has_no_stage`, `test_plain_question_is_not_stage_4`) still green.

- [ ] **Step 5: Document the new cues in `FRAGMENTS.md`**

Replace these three rows of the stage table (the row text only):

Row 2 — from:
`| 2 | **objection** | don't agree / do not agree / i disagree / that won't work / i'm not comfortable / i refuse |`
to:
`| 2 | **objection** | don't agree / do not agree / i disagree / that won't work / i'm not comfortable / i refuse / i don't think X is right / i'm not sure about X / i don't know anything about X |`

Row 5 — from:
`| 5 | **justify** | i'm only trying to / for her safety / the (policy\|agreement\|order) says / my (lawyer\|doctor) says / pursuant to |`
to:
`| 5 | **justify** | i'm only trying to / for her safety / the (policy\|agreement\|order) says / my (lawyer\|doctor) … says/said/told me / pursuant to / per the (agreement\|order\|policy\|parenting plan) |`

Row 6 — from:
`| 6 | **fait_accompli** | i've already / i went ahead and / it's already done / it's final / we've moved / there's nothing to discuss |`
to:
`| 6 | **fait_accompli** | i've already / i went ahead and / it's already done / it's final / we've moved / i (enrolled\|booked\|registered\|scheduled\|withdrew\|switched\|moved) / there's nothing to discuss |`

- [ ] **Step 6: Run the full gate suite (the behavior-preservation tripwire)**

Run: `python -m pytest -q && python -m ruff check . && python -m mypy convergence web && python -m web.build && git diff --exit-code web/site/data/`
Expected: all pass; `web/site/data/` clean (no drift). **In particular, `tests/test_dynamics_corpora.py` and `tests/test_adversarial_corpora.py` must stay green** — that proves the broadened vocabulary did not create a false envelope in any core or adversarial corpus. If a core/adversarial corpus flips, STOP and surface it (do not edit the corpus). Note: this task does NOT make `hold_coercive` complete yet — that also needs the T2 machine change.

- [ ] **Step 7: Commit**

```bash
git add convergence/coercion_grammar.py FRAGMENTS.md tests/test_coercion_grammar.py
git commit -m "feat: broaden coercion stage vocabulary to close holdout recall gap (recall-fix T1)"
```

---

## Task 2: Machine relaxation

**Files:**
- Modify: `convergence/coercion_grammar.py` (`_run_envelope` — one transition)
- Test: `tests/test_coercion_grammar.py` (add completion unit tests)

**Interfaces:**
- Consumes (from T1, on the branch base): the broadened `STAGES`. Consumes (unchanged): `match_grammar`, `_run_envelope`, `_REFUSAL`/`_LEGITIMACY`.
- Produces: a fait completes from `REFUSED` or `CYCLED` once `cycles >= 1`. No new symbols; the `cycles` counter and all other transitions are unchanged.

- [ ] **Step 1: Write the failing completion tests**

Add to `tests/test_coercion_grammar.py`:

```python
def test_envelope_ending_refuse_then_fait_completes():
    # action -> refuse -> legitimize (round 1) -> refuse -> fait
    # The fait follows a final OBJECTION (not a legitimacy). Real coercers often
    # fait right after a last objection; once a round has occurred, the fait
    # terminates the war and should complete.
    msgs = [
        _msg(1, "Can we decide on preschool together like we agreed?", sender="Rosa"),
        _msg(2, "I don't agree to the ones you picked.", sender="Victor"),
        _msg(3, "Per the agreement, I have decision-making too.", sender="Victor"),
        _msg(4, "I still don't agree to your list.", sender="Victor"),
        _msg(5, "It's already done - I enrolled her at Oakwood.", sender="Victor"),
    ]
    m = [x for x in match_grammar(msgs) if x.complete]
    assert len(m) == 1 and m[0].coercer == "Victor"
    assert m[0].cycles >= 1


def test_action_refuse_fait_without_a_round_does_not_complete():
    # No completed refuse->legitimize round (cycles == 0): a fait alone after a
    # lone objection must NOT complete.
    msgs = [
        _msg(1, "Can we decide on preschool together like we agreed?", sender="Rosa"),
        _msg(2, "I don't agree to the ones you picked.", sender="Victor"),
        _msg(3, "It's already done - I enrolled her at Oakwood.", sender="Victor"),
    ]
    assert [x for x in match_grammar(msgs) if x.complete] == []
```

- [ ] **Step 2: Run to verify the first fails**

Run: `python -m pytest tests/test_coercion_grammar.py -k "refuse_then_fait or without_a_round" -v`
Expected: `test_envelope_ending_refuse_then_fait_completes` FAILS (today the fait at seq 5 sees state `REFUSED`, not `CYCLED`, so the envelope does not complete). `test_action_refuse_fait_without_a_round_does_not_complete` already passes (cycles 0) — it is a guard.

- [ ] **Step 3: Relax the completion transition in `_run_envelope`**

In `convergence/coercion_grammar.py`, inside `_run_envelope`, change the single fait-completion branch. From:

```python
        elif state == "CYCLED" and h.stage == 6 and cycles >= 1:
            state = "COMPLETE"
            break
```

to:

```python
        elif state in ("REFUSED", "CYCLED") and h.stage == 6 and cycles >= 1:
            state = "COMPLETE"
            break
```

Leave every other line of `_run_envelope` unchanged (the `S0`/`OPENED`/`REFUSED`/`CYCLED` transitions and the `cycles` increment are untouched).

- [ ] **Step 4: Run the completion tests to verify they pass**

Run: `python -m pytest tests/test_coercion_grammar.py -v`
Expected: PASS — both new tests green, AND the pre-existing envelope tests still green and unchanged: `test_complete_envelope_detected`, `test_cycles_counted` (== 2), `test_fait_accompli_sets_the_status_quo` (== 8), `test_cycles_counted_only_before_the_fait_accompli` (== 2), `test_incomplete_without_fait_accompli`, `test_fait_accompli_alone_is_not_complete`, `test_single_coercer_envelope_completes`, `test_envelope_split_across_two_senders_does_not_complete`, `test_reverse_seq_order_does_not_complete`, `test_bilateral_hostility_is_not_a_single_coercer_envelope`.

- [ ] **Step 5: Run the full gate suite (the tripwire — esp. the hard negative)**

Run: `python -m pytest -q && python -m ruff check . && python -m mypy convergence web && python -m web.build && git diff --exit-code web/site/data/`
Expected: all pass; no web drift. **The key risk is `dyn_high_conflict`** (bilateral, many stage hits) flipping to a false positive under the relaxation, and the cooperative/parallel/conflicted corpora staying negative — `tests/test_dynamics_corpora.py` must stay green. The adversarial suite (`tests/test_adversarial_corpora.py`) must stay 3 TN + 2 TP. If any negative flips, STOP and surface it (sender + seqs + trace); the relaxation is too loose — do NOT edit the corpus.

- [ ] **Step 6: Commit**

```bash
git add convergence/coercion_grammar.py tests/test_coercion_grammar.py
git commit -m "feat: a fait completes the envelope from REFUSED once a round has occurred (recall-fix T2)"
```

---

## Task 3: Tier rotation — regression set + fresh blind holdout

**Files:**
- Move: `data/holdout/hold_{coercive,cooperative,hostile}.json` → `data/regression/reg_{coercive,cooperative,hostile}.json` (`git mv`, content unchanged)
- Create: `data/holdout/hold_{coercive,cooperative,hostile}.json` (fresh blind content — authored by a separate quarantined subagent, provided by the controller; do NOT author these yourself)
- Modify: `convergence/evaluation.py` (`REGRESSION_LABELS`, repoint `HOLDOUT_LABELS`, `TieredEval.regression`, `evaluate_tiered`, `format_tiered_report`)
- Create: `tests/test_regression_corpora.py`

**Interfaces:**
- Consumes (from T1+T2, merged): the engine fixes that make a `refuse → fait` coercive episode complete. Consumes (existing): `evaluate_labelset(base_dir, labels: dict[str, bool]) -> EvalResult`, `evaluate(...)`, `classify_coercive`, `EvalResult`, `TieredEval`, `evaluate_tiered`, `format_tiered_report`, `HOLDOUT_LABELS`, `load_corpus`.
- Produces: `REGRESSION_LABELS: dict[str, bool]`; `TieredEval.regression: EvalResult | None`; a 4-tier report.

- [ ] **Step 1: Relocate the known holdout to the regression set**

```bash
mkdir -p data/regression
git mv data/holdout/hold_coercive.json    data/regression/reg_coercive.json
git mv data/holdout/hold_cooperative.json data/regression/reg_cooperative.json
git mv data/holdout/hold_hostile.json     data/regression/reg_hostile.json
```

(Content is unchanged — these are the now-known corpora. The fresh blind `data/holdout/hold_*.json` are provided separately by the controller in Step 2.)

- [ ] **Step 2: Confirm the fresh blind holdout files exist**

The controller dispatches a quarantined subagent (no access to `coercion_grammar.py`, regexes, or existing corpora) to author fresh `data/holdout/hold_{coercive,cooperative,hostile}.json` from the behavioral definition of coercion only. Do NOT author or inspect these for regex-fit yourself. Confirm only that the three files exist and are valid JSON with exactly the six keys:

Run: `python -c "import json,glob; [print(f, len(json.load(open(f,encoding='utf-8')))) for f in sorted(glob.glob('data/holdout/hold_*.json'))]"`
Expected: three files listed with message counts.

- [ ] **Step 3: Write the failing regression + tier tests**

Create `tests/test_regression_corpora.py`:

```python
"""Regression corpora: the former blind holdout, now KNOWN (its misses drove the
recall fix). reg_coercive is a textbook coercive episode that the pre-fix engine
missed; it must now COMPLETE. The two negatives must stay non-coercive (specificity
regression guard). These are ASSERTED (unlike the blind holdout, which is reported).
"""
from pathlib import Path

from convergence.corpus import load_corpus
from convergence.evaluation import REGRESSION_LABELS, classify_coercive, evaluate_tiered

DATA = Path(__file__).parent.parent / "data"
REG = DATA / "regression"


def test_regression_labels():
    assert REGRESSION_LABELS == {
        "reg_coercive.json": True,
        "reg_cooperative.json": False,
        "reg_hostile.json": False,
    }


def test_reg_coercive_now_completes():
    # the recall-fix target: behaviorally coercive, missed pre-fix, must fire now
    assert classify_coercive(load_corpus(REG / "reg_coercive.json")) is True


def test_reg_negatives_stay_non_coercive():
    assert classify_coercive(load_corpus(REG / "reg_cooperative.json")) is False
    assert classify_coercive(load_corpus(REG / "reg_hostile.json")) is False


def test_tiered_eval_has_four_tiers():
    t = evaluate_tiered(DATA)
    assert t.core is not None and t.adversarial is not None
    assert t.regression is not None and t.holdout is not None
    # regression tier scores perfectly (1 TP + 2 TN) once T1+T2 are in
    assert (t.regression.tp, t.regression.fp, t.regression.fn, t.regression.tn) == (1, 0, 0, 2)
```

- [ ] **Step 4: Run to verify it fails**

Run: `python -m pytest tests/test_regression_corpora.py -v`
Expected: FAIL — `REGRESSION_LABELS` not importable / `TieredEval` has no `regression` field.

- [ ] **Step 5: Wire the regression tier into `convergence/evaluation.py`**

Add `REGRESSION_LABELS` next to `ADVERSARIAL_LABELS`, and repoint `HOLDOUT_LABELS` (filenames unchanged — the fresh blind set reuses the `hold_*` names):

```python
# Regression tier (recall-fix): the former blind holdout, now KNOWN; ASSERTED.
REGRESSION_LABELS = {
    "reg_coercive.json": True,
    "reg_cooperative.json": False,
    "reg_hostile.json": False,
}
```

(`HOLDOUT_LABELS` keeps its three `hold_*` keys — the content under `data/holdout/` is now the fresh blind set.)

Extend `TieredEval` with a `regression` field (keyword construction keeps it safe):

```python
@dataclass(frozen=True)
class TieredEval:
    core: EvalResult
    adversarial: EvalResult
    regression: EvalResult | None
    holdout: EvalResult | None
```

Update `evaluate_tiered` to score the regression tier from `data_dir / "regression"`:

```python
def evaluate_tiered(data_dir) -> TieredEval:
    data_dir = Path(data_dir)
    core = evaluate_dynamics(data_dir)
    adversarial = evaluate_labelset(data_dir, ADVERSARIAL_LABELS)
    regression = (
        evaluate_labelset(data_dir / "regression", REGRESSION_LABELS)
        if REGRESSION_LABELS else None
    )
    holdout = (
        evaluate_labelset(data_dir / "holdout", HOLDOUT_LABELS)
        if HOLDOUT_LABELS else None
    )
    return TieredEval(core=core, adversarial=adversarial, regression=regression, holdout=holdout)
```

Extend `format_tiered_report` to render the regression tier (asserted) before the holdout tier (reported). Insert the regression block between the adversarial and holdout sections:

```python
    if t.regression is not None:
        out += [
            "",
            _format_tier("REGRESSION (known; asserted - the recall-fix target)", t.regression),
        ]
```

(Keep the existing core / adversarial / holdout blocks; the holdout block stays guarded by `if t.holdout is not None:`.)

- [ ] **Step 6: Run the regression + tier tests to verify they pass**

Run: `python -m pytest tests/test_regression_corpora.py tests/test_holdout_corpora.py -v`
Expected: PASS — `reg_coercive` completes (proving T1+T2 closed the gap), the regression negatives stay non-coercive, the four-tier eval is wired, and the (now-fresh) holdout still loads/scores deterministically with no target assertion. If `reg_coercive` does NOT complete, STOP — T1 or T2 is incomplete on this branch; do not edit the corpus.

- [ ] **Step 7: Run the full gate suite + demo**

Run: `python -m pytest -q && python -m ruff check . && python -m mypy convergence web && python -m web.build && git diff --exit-code web/site/data/ && python demo.py --eval | tail -30`
Expected: all pass; no web drift; `demo --eval` prints CORE, ADVERSARIAL, REGRESSION, and HOLDOUT sections. Report the observed fresh-holdout classifications in the report file as an informational generalization data point (not a gate).

- [ ] **Step 8: Commit**

```bash
git add data/regression/reg_coercive.json data/regression/reg_cooperative.json data/regression/reg_hostile.json data/holdout/hold_coercive.json data/holdout/hold_cooperative.json data/holdout/hold_hostile.json convergence/evaluation.py tests/test_regression_corpora.py
git commit -m "feat: rotate holdout -> regression + fresh blind holdout; 4-tier eval (recall-fix T3)"
```

---

## Notes for the controller

- **T1→T2 are sequential** (same file `coercion_grammar.py`); branch each from the prior merged state. **T3 depends on T1+T2 being merged** — its `reg_coercive` assertion passes only once both engine fixes are live.
- **The behavior-preservation tripwire is `t.core` staying perfect (FP=0/FN=0) and the adversarial suite staying 3 TN + 2 TP after every task.** The single highest risk is `dyn_high_conflict` flipping under the T2 relaxation — watch `tests/test_dynamics_corpora.py` there specifically.
- **Honesty discipline:** a misclassifying core/adversarial corpus is surfaced and analyzed, never relabeled/edited. The fresh holdout is authored blind (controller-managed sub-dispatch in T3 Step 1–2), reported not asserted.
- **The fresh blind holdout authoring is controller-managed** (like Phase 3 T3): dispatch the quarantined author after the `git mv`, validate structure only, then the T3 implementer wires labels/tiers/tests.
- After T3 merges, run the **final whole-branch review on the most capable model** over the recall-fix span, with attention to: the regex broadening introducing no false positives (trace the negation guards), the `_run_envelope` relaxation being exactly the one-transition change, `dyn_high_conflict` still negative, `evaluate_dynamics`/metric keys unchanged (no web drift), the blindness of the fresh holdout, and a character-corruption scan of the new regex/JSON literals.
```
