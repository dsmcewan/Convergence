# Refusal + justify vocabulary iteration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the fresh blind holdout's false negative (a tonsillectomy-consent coercive episode) by broadening the stage-2 (objection), stage-3 (obstruction), and stage-5 (justify) regexes so the coercer's refusals AND borrowed-authority justifications are tagged; the already-merged `REFUSED→fait` relaxation then completes the envelope. Vocab-only — no machine change.

**Architecture:** (T1) broaden stages 2/3/5 in `convergence/coercion_grammar.py` + document; (T2) rotate the spent holdout into the asserted regression set and author a fresh blind holdout. Guarded by the existing 4-tier eval.

**Tech Stack:** Python 3.10–3.12, stdlib only; pytest; ruff; mypy. No new dependencies.

## Global Constraints

- **Engine scope:** change ONLY the stage-2, stage-3, and stage-5 `_Stage(...)` regex entries in `convergence/coercion_grammar.py` `STAGES`. Do NOT change stages 1/4/6, `_REFUSAL`/`_LEGITIMACY`, `_run_envelope`, `match_grammar`, `tag_stages`, or any other layer/file.
- **No machine change:** the `REFUSED/CYCLED → fait` relaxation is already merged.
- **Hard gates (must stay green after EVERY task):** the core tier classifies all 5 `dyn_*` corpora perfectly (1 TP + 4 TN); the adversarial suite stays 3 TN + 2 TP; the **existing** regression corpora (the 6 from the preschool + travel rotations) still pass; `ruff`, `mypy`, coverage ≥ 80%, demo-data-drift, on Python 3.10/3.11/3.12; Pages test-gated.
- **Stage-5 broadening is the FP risk:** the bilateral-hostile corpora (`dyn_high_conflict`, `reg_hostile`, `reg_camp_hostile`) and the cooperative corpora are the load-bearing guards. A flipped negative is a surfaced finding (set BLOCKED with corpus + seqs + trace), **never** fixed by editing a corpus.
- **`classify_coercive`, `evaluate_dynamics`, `EvalResult.metrics` dict keys, `_run_envelope` are unchanged** (no web drift).
- **Holdout discipline:** the fresh blind holdout is authored by a subagent quarantined from the matcher; reported, not asserted. The regression set IS asserted.
- **Corpus JSON shape:** each message object has EXACTLY `seq`(int), `thread`(str), `sender`(str), `timestamp`(str), `domain`(str), `body`(str). No extra keys.
- **SDD mechanics:** controller pre-creates each branch FROM `origin/main`; implementer commits locally with explicit `git add <paths>` (never `git add -A`); push → PR → CI → squash-merge per task. `.superpowers/` is gitignored. T2 depends on T1.

---

## File Structure

- `convergence/coercion_grammar.py` (modify, T1) — stage-2, stage-3, stage-5 regexes only.
- `FRAGMENTS.md` (modify, T1) — stage-2, stage-3, stage-5 table rows.
- `tests/test_coercion_grammar.py` (modify, T1) — stage-2/3/5 tagging tests + a negative guard.
- `data/regression/reg_medical_coercive.json`, `reg_swim_cooperative.json`, `reg_religion_hostile.json` (moved, T2) — `git mv` from `data/holdout/`, content unchanged.
- `data/holdout/hold_{coercive,cooperative,hostile}.json` (new content, T2) — fresh blind set (controller-managed quarantined author).
- `convergence/evaluation.py` (modify, T2) — add 3 `REGRESSION_LABELS` entries.
- `tests/test_regression_corpora.py` (modify, T2) — assert the medical coercive completes + the 2 new negatives don't; update labels + tiered-confusion.

---

## Task 1: Refusal + justify vocabulary

**Files:**
- Modify: `convergence/coercion_grammar.py` (stage 2, 3, 5 regex entries)
- Modify: `FRAGMENTS.md` (rows 2, 3, 5)
- Test: `tests/test_coercion_grammar.py`

**Interfaces:**
- Consumes (unchanged): `tag_stages`, `STAGES`, `match_grammar`, `_run_envelope`.
- Produces: broadened stage-2/3/5 matching. No new symbols.

- [ ] **Step 1: Write the failing tagging tests**

Add to `tests/test_coercion_grammar.py` (the `_msg` helper already exists):

```python
# --- refusal + justify broadening (recall gap #3) --------------------------

def test_im_not_agreeing_tags_stage2():
    assert any(h.stage == 2 for h in tag_stages([_msg(1, "Surgery seems extreme. I'm not agreeing to this.")]))  # noqa: E501


def test_you_dont_have_the_right_tags_stage2():
    assert any(h.stage == 2 for h in tag_stages([_msg(1, "You don't have the right to schedule any procedure without my consent.")]))  # noqa: E501


def test_im_not_attending_tags_stage3():
    assert any(h.stage == 3 for h in tag_stages([_msg(1, "I'm not attending any appointment you set up without me.")]))  # noqa: E501


def test_coordinator_redirect_tags_stage3():
    assert any(h.stage == 3 for h in tag_stages([_msg(1, "You go through the co-parenting coordinator, not text me directly.")]))  # noqa: E501


def test_the_parenting_plan_is_clear_tags_stage5():
    assert any(h.stage == 5 for h in tag_stages([_msg(1, "The parenting plan is very clear that major medical decisions require both parents.")]))  # noqa: E501


def test_authority_agrees_tags_stage5():
    assert any(h.stage == 5 for h in tag_stages([_msg(1, "I reviewed it with my attorney and she agrees you're out of line.")]))  # noqa: E501


def test_the_court_requires_tags_stage5():
    assert any(h.stage == 5 for h in tag_stages([_msg(1, "Go through the coordinator. That's what the court requires.")]))


def test_benign_clear_schedule_does_not_tag_stage5():
    # a plain logistics confirmation must not trip the broadened justify cue
    assert all(h.stage != 5 for h in tag_stages([_msg(1, "The plan is for pickup at five, see you then.")]))
```

- [ ] **Step 2: Run to verify they fail**

Run: `python -m pytest tests/test_coercion_grammar.py -k "agreeing or have_the_right or attending or coordinator or parenting_plan_is_clear or authority_agrees or court_requires" -v`
Expected: the seven positive tests FAIL (cues not matched yet); the benign guard already passes.

- [ ] **Step 3: Broaden the stage-2, stage-3, and stage-5 regexes**

In `convergence/coercion_grammar.py`, replace the stage-2, stage-3, and stage-5 `_Stage(...)` entries (stages 1/4/6 unchanged):

```python
    _Stage(2, "objection", re.compile(
        r"\b(i object\b|don't agree|do not agree|i disagree|that won't work|"
        r"that's not acceptable|that is not acceptable|i'm not comfortable|"
        r"i am not comfortable|i won't agree|i refuse|that's not happening|"
        r"i don't think[^.!?]{0,40}\b(right|appropriate|a good idea)\b|"
        r"i'm not[^.!?]{0,12}sure about\b|i don't know anything about\b|"
        r"i don't think so\b|i'm not giving consent\b|i won't consent\b|"
        r"i'm not consenting\b|i'm not signing off\b|you don't get to\b|"
        r"you can't just\b|i'm not agreeing\b|you don't have the right\b)\b")),
    _Stage(3, "obstruction", re.compile(
        r"\b(let's just talk about this later|let's talk about this later|let's talk later|"
        r"i'll get back to you|we'll discuss|i need more time|i need time|"
        r"i'm not going to respond|we can talk about this later|we'll talk in person|"
        r"i'll have my (lawyer|attorney|accountant)|i'm done discussing|"
        r"nothing to talk through|there's nothing to talk about|"
        r"i'm not discussing this|i won't discuss|i'm not attending\b|"
        r"go through the (co-parenting )?coordinator)\b")),
    _Stage(5, "justify", re.compile(
        r"\b(i'm only trying to|i'm just trying to|i am only trying to|"
        r"for (her|his|their) safety|in (her|his) best interest|because the|because my|"
        r"the (policy|agreement|order|schedule) (says|states|requires|stands)|"
        r"the (parenting plan|order|court)\b[^.!?]{0,20}\b(requires|clear|states|mandates)\b|"
        r"my (lawyer|attorney|accountant|doctor)\b[^.!?]{0,40}\b(says|said|told me|advised|agrees|confirms)\b|"
        r"physician of record|doctor of record|"
        r"pursuant to|per the (agreement|order|policy|parenting plan|plan))\b")),
```

- [ ] **Step 4: Run the tagging tests to verify they pass**

Run: `python -m pytest tests/test_coercion_grammar.py -v`
Expected: PASS — the new tagging tests green, AND the pre-existing stage tests still green (`test_objection_stage`, `test_obstruction_stage`, `test_justify_stage`, `test_neutral_message_has_no_stage`, `test_plain_question_is_not_stage_4`, and the prior iterations' guards).

- [ ] **Step 5: Document the new cues in `FRAGMENTS.md`**

Append to the stage rows (keep the existing text; add the new cues after it):

Row 2 — append ` / i'm not agreeing / you don't have the right` to the end of the objection row's cue list.

Row 3 — append ` / i'm not attending / go through the coordinator` to the end of the obstruction row's cue list.

Row 5 — append ` / the (parenting plan\|order\|court) requires/is clear / my (lawyer\|attorney\|doctor) ... agrees/confirms / physician of record` to the end of the justify row's cue list. (Escape the table-cell pipes as `\|`.)

- [ ] **Step 6: Run the full gate suite (the tripwire)**

Run: `python -m pytest -q && python -m ruff check . && python -m mypy convergence web && python -m web.build && git diff --exit-code web/site/data/`
Expected: all pass; no web drift. **In particular `tests/test_dynamics_corpora.py` (core 5), `tests/test_adversarial_corpora.py` (3 TN + 2 TP), and `tests/test_regression_corpora.py` (the existing 6 corpora) must stay green** — especially the bilateral-hostile (`dyn_high_conflict`, `reg_hostile`, `reg_camp_hostile`) and cooperative corpora, since the stage-5 broadening is the FP risk. If a negative flips, STOP and surface it (corpus + seqs + `match_grammar` trace); do not edit the corpus. (This task does not assert the medical holdout completes — that is wired in T2; after this task the engine does complete it, which is fine — the holdout is reported, not asserted.)

- [ ] **Step 7: Commit**

```bash
git add convergence/coercion_grammar.py FRAGMENTS.md tests/test_coercion_grammar.py
git commit -m "feat: broaden objection/obstruction/justify vocabulary (stages 2/3/5) to close holdout gap #3 (refusal-justify T1)"
```

---

## Task 2: Holdout rotation

**Files:**
- Move: `data/holdout/hold_{coercive,cooperative,hostile}.json` → `data/regression/reg_medical_coercive.json`, `reg_swim_cooperative.json`, `reg_religion_hostile.json` (`git mv`, content unchanged)
- Create: `data/holdout/hold_{coercive,cooperative,hostile}.json` (fresh blind content — authored by a separate quarantined subagent, provided by the controller; do NOT author these yourself)
- Modify: `convergence/evaluation.py` (`REGRESSION_LABELS` — add 3 entries)
- Test: `tests/test_regression_corpora.py`

**Interfaces:**
- Consumes (from T1, merged): the broadened stage-2/3/5 vocabulary that makes the medical coercive episode complete. Consumes (existing): `REGRESSION_LABELS`, `HOLDOUT_LABELS`, `evaluate_tiered`, `evaluate_labelset`, `classify_coercive`, `load_corpus`. `tests/test_regression_corpora.py` exists with `REG = DATA / "regression"`.
- Produces: `REGRESSION_LABELS` with 9 entries.

- [ ] **Step 1: Relocate the spent holdout to the regression set**

```bash
git mv data/holdout/hold_coercive.json    data/regression/reg_medical_coercive.json
git mv data/holdout/hold_cooperative.json data/regression/reg_swim_cooperative.json
git mv data/holdout/hold_hostile.json     data/regression/reg_religion_hostile.json
```

(Content unchanged. The fresh blind `data/holdout/hold_*.json` are provided separately by the controller in Step 2.)

- [ ] **Step 2: Confirm the fresh blind holdout files exist**

The controller dispatches a quarantined subagent (no access to `coercion_grammar.py`, regexes, or existing corpora) to author fresh `data/holdout/hold_{coercive,cooperative,hostile}.json`. Do NOT author or inspect these for regex-fit. Confirm only that the three files exist and are valid JSON with exactly the six keys:

Run: `python -c "import json,glob; [print(f, len(json.load(open(f,encoding='utf-8')))) for f in sorted(glob.glob('data/holdout/hold_*.json'))]"`
Expected: three files listed with message counts.

- [ ] **Step 3: Update the failing regression tests**

Edit `tests/test_regression_corpora.py`. Update `test_regression_labels` to the 9-entry dict and add the new assertions (keep the existing preschool + travel assertions):

```python
def test_regression_labels():
    assert REGRESSION_LABELS == {
        "reg_coercive.json": True,
        "reg_cooperative.json": False,
        "reg_hostile.json": False,
        "reg_travel_coercive.json": True,
        "reg_dental_cooperative.json": False,
        "reg_camp_hostile.json": False,
        "reg_medical_coercive.json": True,
        "reg_swim_cooperative.json": False,
        "reg_religion_hostile.json": False,
    }


def test_reg_medical_coercive_now_completes():
    # the gap-#3 fix target: a tonsillectomy-consent coercive episode missed pre-fix
    assert classify_coercive(load_corpus(REG / "reg_medical_coercive.json")) is True


def test_reg_gap3_negatives_stay_non_coercive():
    assert classify_coercive(load_corpus(REG / "reg_swim_cooperative.json")) is False
    # bilateral-hostile religion dispute: key specificity guard for stage-5 broadening
    assert classify_coercive(load_corpus(REG / "reg_religion_hostile.json")) is False
```

And update `test_tiered_eval_has_four_tiers` so the regression confusion reflects 9 corpora (3 TP + 6 TN):

```python
    assert (t.regression.tp, t.regression.fp, t.regression.fn, t.regression.tn) == (3, 0, 0, 6)
```

(Keep the prior `test_reg_*` assertions for the preschool + travel sets.)

- [ ] **Step 4: Run to verify it fails**

Run: `python -m pytest tests/test_regression_corpora.py -v`
Expected: FAIL — `REGRESSION_LABELS` has only the 6 prior entries and the regression tier is `(2,0,0,4)`.

- [ ] **Step 5: Add the new `REGRESSION_LABELS` entries**

In `convergence/evaluation.py`, extend the `REGRESSION_LABELS` dict by appending the three new entries (keep the existing six):

```python
    "reg_medical_coercive.json": True,
    "reg_swim_cooperative.json": False,
    "reg_religion_hostile.json": False,
```

(`HOLDOUT_LABELS` is unchanged — the fresh blind set reuses the `hold_*` names.)

- [ ] **Step 6: Run the regression + holdout tests**

Run: `python -m pytest tests/test_regression_corpora.py tests/test_holdout_corpora.py -v`
Expected: PASS — `reg_medical_coercive` completes (proving T1 closed the gap), the new negatives stay non-coercive, the existing preschool + travel sets still hold, and the (now-fresh) holdout still loads/scores deterministically with no target assertion. If `reg_medical_coercive` does NOT complete, STOP — T1 is missing on this branch; do not edit the corpus.

- [ ] **Step 7: Run the full gate suite + demo**

Run: `python -m pytest -q && python -m ruff check . && python -m mypy convergence web && python -m web.build && git diff --exit-code web/site/data/ && python demo.py --eval | tail -30`
Expected: all pass; no web drift; `demo --eval` prints CORE, ADVERSARIAL, REGRESSION (9 corpora), and HOLDOUT sections. Report the observed fresh-holdout classifications in the report file as an informational generalization data point (not a gate).

- [ ] **Step 8: Commit**

```bash
git add data/regression/reg_medical_coercive.json data/regression/reg_swim_cooperative.json data/regression/reg_religion_hostile.json data/holdout/hold_coercive.json data/holdout/hold_cooperative.json data/holdout/hold_hostile.json convergence/evaluation.py tests/test_regression_corpora.py
git commit -m "feat: rotate spent holdout -> regression (9) + fresh blind holdout (refusal-justify T2)"
```

---

## Notes for the controller

- **Branch each task FROM `origin/main`** (local `main` was reconciled to `origin/main`; keep it that way — do not branch from a divergent local main). T1 precedes T2.
- **The behavior-preservation tripwire is core-perfect + adversarial-3TN+2TP + the existing 6 regression corpora after T1.** The single highest risk is the **stage-5 broadening** flipping a bilateral-hostile or cooperative corpus — watch `dyn_high_conflict`, `reg_hostile`, `reg_camp_hostile`, and the cooperative corpora specifically. (Pre-verified 0 flips, but the implementer must confirm under the full suite.)
- **The fresh blind holdout authoring is controller-managed:** dispatch the quarantined author after the `git mv`, validate structure only, then the T2 implementer wires labels/tests.
- After T2 merges, run the **final whole-branch review on the most capable model** over the iteration span, with attention to: the stage-5 broadening introducing no false positive (trace the new cues against the bilateral corpora), `reg_medical_coercive` completing via the merged relaxation (no machine change crept in), `_run_envelope`/stages 1/4/6 unchanged, the fresh holdout's blindness, the new gap-#4 FN if any (surfaced not chased), and a character-corruption scan of the new regex/JSON literals.
```
