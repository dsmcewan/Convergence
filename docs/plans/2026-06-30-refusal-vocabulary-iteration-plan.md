# Refusal-vocabulary iteration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the fresh blind holdout's false negative (the travel-consent coercive episode) by broadening the stage-2 (objection) and stage-3 (obstruction) regexes so the coercer's refusals are tagged; the already-merged `REFUSED→fait` relaxation then completes the envelope. Vocab-only — no machine change.

**Architecture:** Two engine-adjacent changes: (T1) broaden the stage-2/3 patterns in `convergence/coercion_grammar.py` + document them; (T2) rotate the spent holdout into the asserted regression set and author a fresh blind holdout. Guarded by the existing 4-tier eval (core/adversarial/regression/holdout).

**Tech Stack:** Python 3.10–3.12, stdlib only (`re`, `json`, `dataclasses`, `pathlib`); pytest; ruff; mypy. No new dependencies.

## Global Constraints

- **Engine scope:** change ONLY the stage-2 and stage-3 `_Stage(...)` regex entries in `convergence/coercion_grammar.py` `STAGES`. Do NOT change stages 1/4/5/6, `_REFUSAL`/`_LEGITIMACY`, `_run_envelope`, `match_grammar`, `tag_stages`, or any other layer/file.
- **No machine change:** the `REFUSED/CYCLED → fait` completion relaxation is already merged. This iteration only adds refusal vocabulary.
- **Hard gates (must stay green after EVERY task):** the core tier classifies all 5 `dyn_*` corpora perfectly (1 TP + 4 TN); the adversarial suite stays 3 TN + 2 TP; the **existing** regression corpora (`reg_coercive`/`reg_cooperative`/`reg_hostile`, the preschool set) still pass; `ruff`, `mypy`, coverage ≥ 80%, demo-data-drift, on Python 3.10/3.11/3.12; Pages test-gated.
- **A flipped core/adversarial/existing-regression negative is a surfaced finding, never fixed by editing a corpus.** If a gate goes red because a corpus mis-classifies, STOP, report it (corpus + seqs + `match_grammar` trace), set BLOCKED. The broadening is too greedy — the human decides.
- **`classify_coercive`, `evaluate_dynamics`, `EvalResult.metrics` dict keys, `_run_envelope` are unchanged** (no web drift).
- **Holdout discipline:** the fresh blind holdout is authored by a subagent quarantined from the matcher (no `coercion_grammar.py`, no regexes, no existing corpora); reported, not asserted. The regression set IS asserted.
- **Corpus JSON shape:** each message object has EXACTLY `seq`(int), `thread`(str), `sender`(str), `timestamp`(str), `domain`(str), `body`(str). No extra keys.
- **SDD mechanics:** controller pre-creates each branch; implementer commits locally with explicit `git add <paths>` (never `git add -A`); push → PR → CI → squash-merge per task. `.superpowers/` is gitignored. T2 depends on T1 (the `reg_travel_coercive` completion assertion passes only after T1's vocabulary).

---

## File Structure

- `convergence/coercion_grammar.py` (modify, T1) — stage-2 and stage-3 regexes only.
- `FRAGMENTS.md` (modify, T1) — stage-2 and stage-3 table rows.
- `tests/test_coercion_grammar.py` (modify, T1) — stage-2/3 tagging tests (positive + a negative guard).
- `data/regression/reg_travel_coercive.json`, `reg_dental_cooperative.json`, `reg_camp_hostile.json` (moved, T2) — `git mv` from `data/holdout/`, content unchanged.
- `data/holdout/hold_{coercive,cooperative,hostile}.json` (new content, T2) — fresh blind set (controller-managed quarantined author).
- `convergence/evaluation.py` (modify, T2) — add the 3 new `REGRESSION_LABELS` entries.
- `tests/test_regression_corpora.py` (modify, T2) — assert the travel coercive completes + the 2 new negatives don't; update the labels + tiered-confusion assertions.

---

## Task 1: Refusal vocabulary

**Files:**
- Modify: `convergence/coercion_grammar.py` (stage 2 and stage 3 regex entries)
- Modify: `FRAGMENTS.md` (rows 2 and 3)
- Test: `tests/test_coercion_grammar.py`

**Interfaces:**
- Consumes (unchanged): `tag_stages`, `STAGES`, `match_grammar`, `_run_envelope`.
- Produces: broadened stage-2/3 matching. No new symbols.

- [ ] **Step 1: Write the failing tagging tests**

Add to `tests/test_coercion_grammar.py` (the `_msg` helper already exists):

```python
# --- refusal-engine broadening (recall gap #2) -----------------------------

def test_i_dont_think_so_tags_stage2():
    assert any(h.stage == 2 for h in tag_stages([_msg(1, "I don't think so. That's my week per the schedule.")]))  # noqa: E501


def test_consent_refusal_tags_stage2():
    assert any(h.stage == 2 for h in tag_stages([_msg(1, "I'm not giving consent for the flight to Florida.")]))  # noqa: E501


def test_you_dont_get_to_tags_stage2():
    assert any(h.stage == 2 for h in tag_stages([_msg(1, "You don't get to just decide to take her out of state.")]))  # noqa: E501


def test_nothing_to_talk_through_tags_stage3():
    assert any(h.stage == 3 for h in tag_stages([_msg(1, "There's nothing to talk through.")]))


def test_affirmative_think_so_does_not_tag_stage2():
    # the broadened cue is the NEGATIVE "i don't think so" - a plain "i think so" must not tag
    assert all(h.stage != 2 for h in tag_stages([_msg(1, "I think so, that works for me.")]))
```

- [ ] **Step 2: Run to verify they fail**

Run: `python -m pytest tests/test_coercion_grammar.py -k "think_so or consent or you_dont_get or talk_through" -v`
Expected: the four positive tests FAIL (cues not matched yet); `test_affirmative_think_so_does_not_tag_stage2` already passes (a guard).

- [ ] **Step 3: Broaden the stage-2 and stage-3 regexes**

In `convergence/coercion_grammar.py`, replace the stage-2 and stage-3 `_Stage(...)` entries (stages 1/4/5/6 unchanged):

```python
    _Stage(2, "objection", re.compile(
        r"\b(i object\b|don't agree|do not agree|i disagree|that won't work|"
        r"that's not acceptable|that is not acceptable|i'm not comfortable|"
        r"i am not comfortable|i won't agree|i refuse|that's not happening|"
        r"i don't think[^.!?]{0,40}\b(right|appropriate|a good idea)\b|"
        r"i'm not[^.!?]{0,12}sure about\b|i don't know anything about\b|"
        r"i don't think so\b|i'm not giving consent\b|i won't consent\b|"
        r"i'm not consenting\b|i'm not signing off\b|you don't get to\b|"
        r"you can't just\b)\b")),
    _Stage(3, "obstruction", re.compile(
        r"\b(let's just talk about this later|let's talk about this later|let's talk later|"
        r"i'll get back to you|we'll discuss|i need more time|i need time|"
        r"i'm not going to respond|we can talk about this later|we'll talk in person|"
        r"i'll have my (lawyer|attorney|accountant)|i'm done discussing|"
        r"nothing to talk through|there's nothing to talk about|"
        r"i'm not discussing this|i won't discuss)\b")),
```

- [ ] **Step 4: Run the tagging tests to verify they pass**

Run: `python -m pytest tests/test_coercion_grammar.py -v`
Expected: PASS — the new tagging tests green, AND the pre-existing stage tests still green (`test_objection_stage`, `test_obstruction_stage`, `test_neutral_message_has_no_stage`, `test_plain_question_is_not_stage_4`, and the first recall-fix's negation/scoping guards).

- [ ] **Step 5: Document the new cues in `FRAGMENTS.md`**

Replace row 2 — from:
`| 2 | **objection** | don't agree / do not agree / i disagree / that won't work / i'm not comfortable / i refuse / i don't think X is right / i'm not sure about X / i don't know anything about X |`
to:
`| 2 | **objection** | don't agree / do not agree / i disagree / that won't work / i'm not comfortable / i refuse / i don't think X is right / i'm not sure about X / i don't know anything about X / i don't think so / i'm not giving consent / i won't consent / you don't get to / you can't just |`

Replace row 3 — from:
`| 3 | **obstruction** | let's talk about this later / i'll get back to you / we'll discuss / i need more time / i'm done discussing |`
to:
`| 3 | **obstruction** | let's talk about this later / i'll get back to you / we'll discuss / i need more time / i'm done discussing / nothing to talk through / i'm not discussing this / i won't discuss |`

- [ ] **Step 6: Run the full gate suite (the tripwire)**

Run: `python -m pytest -q && python -m ruff check . && python -m mypy convergence web && python -m web.build && git diff --exit-code web/site/data/`
Expected: all pass; no web drift. **In particular `tests/test_dynamics_corpora.py` (core 5), `tests/test_adversarial_corpora.py` (3 TN + 2 TP), and `tests/test_regression_corpora.py` (the existing preschool set) must stay green** — that proves the refusal broadening created no false envelope in any core/adversarial/existing-regression corpus (especially the bilateral-hostile ones). If a negative flips, STOP and surface it (do not edit the corpus). Note: this task does not assert the travel holdout completes (that is wired in T2); after this task the engine does complete it, which is fine (the holdout is reported, not asserted).

- [ ] **Step 7: Commit**

```bash
git add convergence/coercion_grammar.py FRAGMENTS.md tests/test_coercion_grammar.py
git commit -m "feat: broaden refusal-engine vocabulary (stages 2/3) to close holdout gap #2 (refusal-vocab T1)"
```

---

## Task 2: Holdout rotation

**Files:**
- Move: `data/holdout/hold_{coercive,cooperative,hostile}.json` → `data/regression/reg_travel_coercive.json`, `reg_dental_cooperative.json`, `reg_camp_hostile.json` (`git mv`, content unchanged)
- Create: `data/holdout/hold_{coercive,cooperative,hostile}.json` (fresh blind content — authored by a separate quarantined subagent, provided by the controller; do NOT author these yourself)
- Modify: `convergence/evaluation.py` (`REGRESSION_LABELS` — add 3 entries)
- Test: `tests/test_regression_corpora.py`

**Interfaces:**
- Consumes (from T1, merged): the broadened stage-2/3 vocabulary that makes the travel coercive episode complete. Consumes (existing): `REGRESSION_LABELS`, `HOLDOUT_LABELS`, `evaluate_tiered`, `evaluate_labelset`, `classify_coercive`, `load_corpus`.
- Produces: `REGRESSION_LABELS` with 6 entries.

- [ ] **Step 1: Relocate the spent holdout to the regression set**

```bash
git mv data/holdout/hold_coercive.json    data/regression/reg_travel_coercive.json
git mv data/holdout/hold_cooperative.json data/regression/reg_dental_cooperative.json
git mv data/holdout/hold_hostile.json     data/regression/reg_camp_hostile.json
```

(Content unchanged — these are the now-known corpora. The fresh blind `data/holdout/hold_*.json` are provided separately by the controller in Step 2.)

- [ ] **Step 2: Confirm the fresh blind holdout files exist**

The controller dispatches a quarantined subagent (no access to `coercion_grammar.py`, regexes, or existing corpora) to author fresh `data/holdout/hold_{coercive,cooperative,hostile}.json` from the behavioral definition of coercion only. Do NOT author or inspect these for regex-fit yourself. Confirm only that the three files exist and are valid JSON with exactly the six keys:

Run: `python -c "import json,glob; [print(f, len(json.load(open(f,encoding='utf-8')))) for f in sorted(glob.glob('data/holdout/hold_*.json'))]"`
Expected: three files listed with message counts.

- [ ] **Step 3: Update the failing regression tests**

Edit `tests/test_regression_corpora.py`. Update `test_regression_labels` to the 6-entry dict and add the new assertions (keep the existing preschool assertions):

```python
def test_regression_labels():
    assert REGRESSION_LABELS == {
        "reg_coercive.json": True,
        "reg_cooperative.json": False,
        "reg_hostile.json": False,
        "reg_travel_coercive.json": True,
        "reg_dental_cooperative.json": False,
        "reg_camp_hostile.json": False,
    }


def test_reg_travel_coercive_now_completes():
    # the gap-#2 fix target: a travel-consent coercive episode missed pre-fix
    assert classify_coercive(load_corpus(REG / "reg_travel_coercive.json")) is True


def test_new_reg_negatives_stay_non_coercive():
    assert classify_coercive(load_corpus(REG / "reg_dental_cooperative.json")) is False
    # the bilateral-hostile corpus is the key specificity guard for refusal-vocab broadening
    assert classify_coercive(load_corpus(REG / "reg_camp_hostile.json")) is False
```

And update `test_tiered_eval_has_four_tiers` so the regression confusion reflects 6 corpora (2 TP + 4 TN):

```python
    assert (t.regression.tp, t.regression.fp, t.regression.fn, t.regression.tn) == (2, 0, 0, 4)
```

(Keep `test_reg_coercive_now_completes` and `test_reg_negatives_stay_non_coercive` for the existing preschool trio.)

- [ ] **Step 4: Run to verify it fails**

Run: `python -m pytest tests/test_regression_corpora.py -v`
Expected: FAIL — `REGRESSION_LABELS` has only the 3 old entries and the regression tier is `(1,0,0,2)`.

- [ ] **Step 5: Add the new `REGRESSION_LABELS` entries**

In `convergence/evaluation.py`, extend the `REGRESSION_LABELS` dict:

```python
REGRESSION_LABELS: dict[str, bool] = {
    "reg_coercive.json": True,
    "reg_cooperative.json": False,
    "reg_hostile.json": False,
    "reg_travel_coercive.json": True,
    "reg_dental_cooperative.json": False,
    "reg_camp_hostile.json": False,
}
```

(`HOLDOUT_LABELS` is unchanged — the fresh blind set reuses the `hold_*` names.)

- [ ] **Step 6: Run the regression + holdout tests**

Run: `python -m pytest tests/test_regression_corpora.py tests/test_holdout_corpora.py -v`
Expected: PASS — `reg_travel_coercive` completes (proving T1 closed the gap), the new negatives stay non-coercive, the existing preschool trio still holds, and the (now-fresh) holdout still loads/scores deterministically with no target assertion. If `reg_travel_coercive` does NOT complete, STOP — T1 is missing on this branch; do not edit the corpus.

- [ ] **Step 7: Run the full gate suite + demo**

Run: `python -m pytest -q && python -m ruff check . && python -m mypy convergence web && python -m web.build && git diff --exit-code web/site/data/ && python demo.py --eval | tail -30`
Expected: all pass; no web drift; `demo --eval` prints CORE, ADVERSARIAL, REGRESSION (6 corpora), and HOLDOUT sections. Report the observed fresh-holdout classifications in the report file as an informational generalization data point (not a gate).

- [ ] **Step 8: Commit**

```bash
git add data/regression/reg_travel_coercive.json data/regression/reg_dental_cooperative.json data/regression/reg_camp_hostile.json data/holdout/hold_coercive.json data/holdout/hold_cooperative.json data/holdout/hold_hostile.json convergence/evaluation.py tests/test_regression_corpora.py
git commit -m "feat: rotate spent holdout -> regression (6) + fresh blind holdout (refusal-vocab T2)"
```

---

## Notes for the controller

- **T1 precedes T2** — T2's `reg_travel_coercive` completion assertion passes only once T1's vocabulary is merged.
- **The behavior-preservation tripwire is core-perfect + adversarial-3TN+2TP + the existing preschool regression trio after T1.** The single highest risk is a bilateral-hostile corpus (`dyn_high_conflict`, `reg_camp_hostile`) flipping under the broadened refusal vocabulary — watch those specifically.
- **The fresh blind holdout authoring is controller-managed** (like the prior rotations): dispatch the quarantined author after the `git mv`, validate structure only, then the T2 implementer wires labels/tests.
- After T2 merges, run the **final whole-branch review on the most capable model** over the iteration span, with attention to: the refusal broadening introducing no false positive (trace the new cues against the bilateral corpora), `reg_travel_coercive` completing via the merged relaxation (no machine change crept in), `_run_envelope`/stages 1/4/5/6 unchanged, the fresh holdout's blindness, and a character-corruption scan of the new regex/JSON literals.
```
