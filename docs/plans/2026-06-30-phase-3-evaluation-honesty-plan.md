# Phase 3 — Evaluation honesty Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove the Phase-2 ordered, sender-aware coercion discriminator honestly — add adversarial corpora (both directions), reframe the metrics as corpus-level discrimination, and add a fresh-subagent-authored blind holdout — without changing the engine's matching logic.

**Architecture:** Three tiers of labeled corpora (`core` = existing `dyn_*`, `adversarial` = new `adv_*`, `holdout` = new `data/holdout/hold_*`) scored separately. `convergence/evaluation.py` gains an additive tiered driver and a reframed report; `evaluate_dynamics` and `EvalResult.metrics` stay byte-identical so `web/serialize.py` output does not drift. The holdout is authored by a subagent that never sees `coercion_grammar.py`, committed once, and reported (not asserted to a target).

**Tech Stack:** Python 3.10–3.12, stdlib only (`re`, `json`, `dataclasses`, `pathlib`); pytest; ruff; mypy. No new dependencies.

## Global Constraints

- **Engine matching logic is unchanged.** Touch only `data/`, `convergence/evaluation.py`, `demo.py` (one import + one call), and `tests/`. Do NOT edit `convergence/coercion_grammar.py`, the six stage regexes, `_REFUSAL`/`_LEGITIMACY`, `match_grammar`, `_run_envelope`, thread grouping, or any other layer.
- **`classify_coercive` signature and `EvalResult.metrics` dict keys stay stable** (`precision/recall/f1/specificity/accuracy`). The rename is human-facing report vocabulary + caveats only.
- **`evaluate_dynamics(data_dir)` returns byte-identical results** to today (core tier unchanged) — `web/serialize.py:126` depends on it; changing it would break the demo-data-drift gate.
- **Core 5 `dyn_*` corpora classify perfectly** (1 TP + 4 TN) — the behavior-preservation guard.
- **Adversarial: exactly 5 corpora** — 3 negatives (`adv_mixed_senders`, `adv_reversed_chronology`, `adv_unrelated_contamination`) must be TN; 2 positives (`adv_interleaved_threads`, `adv_subject_mismatch`) must be TP.
- **Holdout: 3 corpora**, authored by a subagent that does NOT see `coercion_grammar.py` or the matcher internals; frozen once written; scored on a separate generalization line; **reported, not asserted to a target**.
- **A failing adversarial/holdout corpus is surfaced and analyzed, never relabeled.** An engine fix is legitimate only as a separate, surfaced decision (escalate to the human — it is out of this plan's scope to silently change the engine).
- **Corpus JSON shape:** each file is a JSON list of message objects with EXACTLY these keys — `seq` (int), `thread` (str), `sender` (str), `timestamp` (str ISO), `domain` (str), `body` (str). No extra keys (`Message(**m)` raises on unknown keys). `seq` is monotonic record order.
- **Gates that must stay green on Python 3.10/3.11/3.12:** `ruff`, `mypy` (pragmatic), coverage ≥ 80% (`--cov-fail-under=80`), `pytest` ×2 (determinism), demo-data-drift (`python -m web.build && git diff --exit-code web/site/data/`), Pages test-gated.
- **SDD mechanics:** controller pre-creates the branch; implementer commits locally with explicit `git add <paths>` (never `git add -A`); push → PR → CI → squash-merge per task. `.superpowers/` is gitignored.

---

## File Structure

- `data/adv_mixed_senders.json` (new) — negative: stage cues split across senders.
- `data/adv_reversed_chronology.json` (new) — negative: full cue set, fait at lowest seq.
- `data/adv_unrelated_contamination.json` (new) — negative: benign thread, scattered cues, no completable structure.
- `data/adv_interleaved_threads.json` (new) — positive: genuine envelope in one thread, coercer also fires stray cues in other threads.
- `data/adv_subject_mismatch.json` (new) — positive: genuine envelope + off-subject distractor cues in another thread.
- `data/holdout/hold_*.json` (new, T3, subagent-authored) — 3 blind corpora.
- `convergence/evaluation.py` (modify) — add `ADVERSARIAL_LABELS`, `HOLDOUT_LABELS`, `TieredEval`, `evaluate_labelset`, `evaluate_tiered` (T1); reframe `format_report`, add `_format_tier`, `format_tiered_report` (T2); wire holdout (T3). `evaluate_dynamics`, `evaluate`, `metrics`, `EvalResult`, `CorpusEval`, `DocumentaryPrecision` and friends stay unchanged.
- `demo.py` (modify, T2) — switch `--eval` to the tiered report.
- `tests/test_adversarial_corpora.py` (new, T1) — per-corpus classification + core-tier regression.
- `tests/test_evaluation.py` (modify, T2) — report-format assertions for the reframed headline/caveat.
- `tests/test_holdout_corpora.py` (new, T3) — load/score determinism, no target assertion.

---

## Task 1: Tiering + adversarial corpora + core-tier regression

**Files:**
- Create: `data/adv_mixed_senders.json`, `data/adv_reversed_chronology.json`, `data/adv_unrelated_contamination.json`, `data/adv_interleaved_threads.json`, `data/adv_subject_mismatch.json`
- Modify: `convergence/evaluation.py` (additive only — new labels, `TieredEval`, `evaluate_labelset`, `evaluate_tiered`)
- Test: `tests/test_adversarial_corpora.py`

**Interfaces:**
- Consumes (existing, unchanged): `evaluate(labeled) -> EvalResult`, `evaluate_dynamics(data_dir) -> EvalResult`, `classify_coercive(messages) -> bool`, `convergence.corpus.load_corpus(path) -> list[Message]`, `convergence.coercion_grammar.match_grammar`.
- Produces (for T2/T3):
  - `ADVERSARIAL_LABELS: dict[str, bool]` — `adv_*.json` filename → ground-truth coercive.
  - `HOLDOUT_LABELS: dict[str, bool]` — empty `{}` in T1; filled in T3.
  - `evaluate_labelset(base_dir, labels: dict[str, bool]) -> EvalResult` — load each filename under `base_dir`, score via `evaluate`.
  - `TieredEval` (frozen dataclass): `core: EvalResult`, `adversarial: EvalResult`, `holdout: EvalResult | None`.
  - `evaluate_tiered(data_dir) -> TieredEval`.

### Corpus content (verified against `STAGES` + `match_grammar`/`_run_envelope`)

The stage cues below were checked against the live regexes: each body matches only its intended stage. Completion requires, within ONE thread, a stage-1 action (any sender) opening, then the SAME coercer running refusal(2/3) → legitimacy(4/5) [cycles≥1] → fait(6) in strictly increasing `seq`.

- [ ] **Step 1: Create the three negative corpora**

`data/adv_mixed_senders.json` — war/fait split across Victor/Pat so no single coercer owns an ordered refuse→legitimize→fait. Expected: **not coercive (TN)**.

```json
[
  {"seq": 1, "thread": "decision", "sender": "Rosa", "timestamp": "2024-03-01T09:00", "domain": "education", "body": "Can we decide on preschool together? I'd like to tour a few like we agreed."},
  {"seq": 2, "thread": "decision", "sender": "Victor", "timestamp": "2024-03-02T09:00", "domain": "education", "body": "I don't agree to the ones you picked."},
  {"seq": 3, "thread": "decision", "sender": "Pat", "timestamp": "2024-03-03T09:00", "domain": "education", "body": "Let's talk about this later, I'll get back to you."},
  {"seq": 4, "thread": "decision", "sender": "Rosa", "timestamp": "2024-03-04T09:00", "domain": "education", "body": "On what basis are you choosing schools without consulting me?"},
  {"seq": 5, "thread": "decision", "sender": "Victor", "timestamp": "2024-03-05T09:00", "domain": "education", "body": "I'm only trying to do what's best for her, and my lawyer says I have equal say."},
  {"seq": 6, "thread": "decision", "sender": "Pat", "timestamp": "2024-03-06T09:00", "domain": "education", "body": "It's already done - I enrolled her at Oakwood, there's nothing to discuss."}
]
```

`data/adv_reversed_chronology.json` — one coercer (Victor), full cue set, but fait at the lowest `seq` and action at the highest; the envelope cannot progress in increasing `seq`. Expected: **not coercive (TN)**.

```json
[
  {"seq": 1, "thread": "decision", "sender": "Victor", "timestamp": "2024-04-06T09:00", "domain": "education", "body": "It's already done - I enrolled her at Oakwood, there's nothing to discuss."},
  {"seq": 2, "thread": "decision", "sender": "Victor", "timestamp": "2024-04-05T09:00", "domain": "education", "body": "I'm only trying to do what's best for her, and my lawyer says I have equal say."},
  {"seq": 3, "thread": "decision", "sender": "Victor", "timestamp": "2024-04-04T09:00", "domain": "education", "body": "On what basis are you choosing schools without consulting me?"},
  {"seq": 4, "thread": "decision", "sender": "Victor", "timestamp": "2024-04-03T09:00", "domain": "education", "body": "Let's talk about this later, I'll get back to you."},
  {"seq": 5, "thread": "decision", "sender": "Victor", "timestamp": "2024-04-02T09:00", "domain": "education", "body": "I don't agree to the ones you picked."},
  {"seq": 6, "thread": "decision", "sender": "Rosa", "timestamp": "2024-04-01T09:00", "domain": "education", "body": "Can we decide on preschool together? I'd like to tour a few like we agreed."}
]
```

`data/adv_unrelated_contamination.json` — a cooperative thread whose messages happen to match stage regexes (action, a benign disagreement by the other party, a fait-shaped confirmation, a "per the agreement" line) but form no ordered single-coercer envelope. Expected: **not coercive (TN)**.

```json
[
  {"seq": 1, "thread": "logistics", "sender": "Dana", "timestamp": "2024-05-01T09:00", "domain": "schedule", "body": "Can we confirm the schedule like we agreed?"},
  {"seq": 2, "thread": "logistics", "sender": "Chris", "timestamp": "2024-05-01T10:00", "domain": "schedule", "body": "I don't agree, let's do 6pm instead - works better for the bus."},
  {"seq": 3, "thread": "logistics", "sender": "Dana", "timestamp": "2024-05-01T11:00", "domain": "schedule", "body": "Sounds good. It's already done, I updated the calendar."},
  {"seq": 4, "thread": "logistics", "sender": "Dana", "timestamp": "2024-05-01T12:00", "domain": "schedule", "body": "Per the agreement, that's the usual slot anyway. Thanks!"}
]
```

- [ ] **Step 2: Create the two positive corpora**

`data/adv_interleaved_threads.json` — genuine envelope in thread `school` by Victor, while Victor ALSO emits stray stage cues in `logistics` and `money`; the machine must fire on `school` and must NOT stitch a cross-thread envelope. Expected: **coercive (TP)**.

```json
[
  {"seq": 1, "thread": "school", "sender": "Rosa", "timestamp": "2024-06-01T09:00", "domain": "education", "body": "Can we decide on preschool together? I'd like to tour a few like we agreed."},
  {"seq": 2, "thread": "logistics", "sender": "Victor", "timestamp": "2024-06-02T09:00", "domain": "schedule", "body": "It's already done, I booked the dentist for Tuesday."},
  {"seq": 3, "thread": "school", "sender": "Victor", "timestamp": "2024-06-03T09:00", "domain": "education", "body": "I don't agree to the ones you picked."},
  {"seq": 4, "thread": "money", "sender": "Victor", "timestamp": "2024-06-04T09:00", "domain": "finance", "body": "On what basis is that bill mine?"},
  {"seq": 5, "thread": "school", "sender": "Victor", "timestamp": "2024-06-05T09:00", "domain": "education", "body": "I'm only trying to do what's best for her, and my lawyer says I have equal say."},
  {"seq": 6, "thread": "school", "sender": "Victor", "timestamp": "2024-06-06T09:00", "domain": "education", "body": "It's already done - I enrolled her at Oakwood, there's nothing to discuss."}
]
```

`data/adv_subject_mismatch.json` — genuine envelope in `parenting` by Victor + distractor cues (objection, justify) in a `finance` thread on an unrelated subject. Expected: **coercive (TP)**.

```json
[
  {"seq": 1, "thread": "parenting", "sender": "Rosa", "timestamp": "2024-07-01T09:00", "domain": "schedule", "body": "Can we confirm the schedule like we agreed?"},
  {"seq": 2, "thread": "finance", "sender": "Victor", "timestamp": "2024-07-02T09:00", "domain": "finance", "body": "I don't agree to that."},
  {"seq": 3, "thread": "parenting", "sender": "Victor", "timestamp": "2024-07-03T09:00", "domain": "schedule", "body": "I don't agree to the ones you picked."},
  {"seq": 4, "thread": "finance", "sender": "Victor", "timestamp": "2024-07-04T09:00", "domain": "finance", "body": "I'm only trying to help, and my lawyer says I have a say."},
  {"seq": 5, "thread": "parenting", "sender": "Victor", "timestamp": "2024-07-05T09:00", "domain": "schedule", "body": "I'm only trying to do what's best for her, and my lawyer says I have equal say."},
  {"seq": 6, "thread": "parenting", "sender": "Victor", "timestamp": "2024-07-06T09:00", "domain": "schedule", "body": "It's already done, there's nothing to discuss."}
]
```

- [ ] **Step 3: Write the failing tests**

Create `tests/test_adversarial_corpora.py`:

```python
"""Adversarial corpora: engineered to fool a stage-COUNTER but not the Phase-2
ordered, sender-aware machine. Three negatives must stay true negatives (no false
envelope); two robustness positives must stay true positives (a genuine envelope
survives interleaving and off-subject noise). Plus the core-tier regression guard:
the five dynamics corpora must still classify perfectly. Synthetic only.
"""
from pathlib import Path

from convergence.corpus import load_corpus
from convergence.evaluation import (
    ADVERSARIAL_LABELS,
    classify_coercive,
    evaluate_tiered,
)

DATA = Path(__file__).parent.parent / "data"

# ground truth, mirrored from the spec's adversarial table
EXPECTED = {
    "adv_mixed_senders.json": False,
    "adv_reversed_chronology.json": False,
    "adv_unrelated_contamination.json": False,
    "adv_interleaved_threads.json": True,
    "adv_subject_mismatch.json": True,
}


def test_labels_match_spec():
    assert ADVERSARIAL_LABELS == EXPECTED


def test_each_adversarial_corpus_classifies_correctly():
    for fname, expected in EXPECTED.items():
        msgs = load_corpus(DATA / fname)
        assert classify_coercive(msgs) is expected, f"{fname} misclassified"


def test_interleaved_positive_fires_on_its_own_thread_only():
    # the genuine envelope is in 'school'; stray cues live in other threads and
    # must NOT be stitched into a cross-thread envelope
    from convergence.coercion_grammar import match_grammar
    msgs = load_corpus(DATA / "adv_interleaved_threads.json")
    complete = [m for m in match_grammar(msgs) if m.complete]
    assert [m.thread for m in complete] == ["school"]
    assert all(m.coercer == "Victor" for m in complete)


def test_tiered_eval_core_is_perfect_and_adversarial_scores():
    t = evaluate_tiered(DATA)
    # core tier: the behavior-preservation guard — all 5 dynamics corpora correct
    assert t.core.fp == 0 and t.core.fn == 0
    assert t.core.metrics["precision"] == 1.0 and t.core.metrics["recall"] == 1.0
    # adversarial tier: 2 positives, 3 negatives, all correct -> no FP, no FN
    assert (t.adversarial.tp, t.adversarial.fp, t.adversarial.fn, t.adversarial.tn) == (2, 0, 0, 3)
    # holdout not wired until T3
    assert t.holdout is None
```

- [ ] **Step 4: Run the tests to verify they fail**

Run: `python -m pytest tests/test_adversarial_corpora.py -v`
Expected: FAIL with `ImportError: cannot import name 'ADVERSARIAL_LABELS'` (and `evaluate_tiered`).

- [ ] **Step 5: Add the tiered scaffolding to `convergence/evaluation.py`**

Insert after the existing `DYNAMICS_LABELS` block (keep `DYNAMICS_LABELS`, `classify_coercive`, `metrics`, `CorpusEval`, `EvalResult`, `evaluate`, `evaluate_dynamics` exactly as they are). Add:

```python
# Adversarial tier (Phase 3): engineered to fool a stage-counter, not the machine.
ADVERSARIAL_LABELS = {
    "adv_mixed_senders.json": False,
    "adv_reversed_chronology.json": False,
    "adv_unrelated_contamination.json": False,
    "adv_interleaved_threads.json": True,
    "adv_subject_mismatch.json": True,
}

# Blind holdout tier (Phase 3): filled in T3 by a fresh-subagent-authored set.
HOLDOUT_LABELS: dict[str, bool] = {}


def _corpus_label(fname: str) -> str:
    stem = fname.replace(".json", "")
    for prefix in ("dyn_", "adv_", "hold_"):
        if stem.startswith(prefix):
            return stem[len(prefix):]
    return stem


def evaluate_labelset(base_dir, labels: dict) -> EvalResult:
    """Score a labeled corpus set whose files live directly under base_dir."""
    base = Path(base_dir)
    labeled = [
        (_corpus_label(fname), load_corpus(base / fname), label)
        for fname, label in labels.items()
    ]
    return evaluate(labeled)
```

Add the import for `load_corpus` is already present (`from convergence.corpus import load_corpus`). Then add the tiered driver and its result type near the bottom (after `evaluate_dynamics`):

```python
@dataclass(frozen=True)
class TieredEval:
    core: EvalResult              # the 5 dynamics corpora (behavior-preservation guard)
    adversarial: EvalResult       # the 5 engineered corpora
    holdout: EvalResult | None    # the blind holdout (None until wired in T3)


def evaluate_tiered(data_dir) -> TieredEval:
    data_dir = Path(data_dir)
    core = evaluate_dynamics(data_dir)                    # unchanged result
    adversarial = evaluate_labelset(data_dir, ADVERSARIAL_LABELS)
    holdout = (
        evaluate_labelset(data_dir / "holdout", HOLDOUT_LABELS)
        if HOLDOUT_LABELS else None
    )
    return TieredEval(core=core, adversarial=adversarial, holdout=holdout)
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `python -m pytest tests/test_adversarial_corpora.py -v`
Expected: PASS (5 tests). If any adversarial corpus misclassifies, STOP — that is a real engine finding per the Global Constraints; surface it (corpus name, message seqs, `match_grammar` trace) and escalate. Do not edit the corpus to pass.

- [ ] **Step 7: Run the full suite + lint + type + drift to confirm no regression**

Run: `python -m pytest -q && ruff check . && mypy convergence web && python -m web.build && git diff --exit-code web/site/data/`
Expected: all pass; `git diff --exit-code web/site/data/` clean (no drift — `evaluate_dynamics` is unchanged, so `web/serialize.py` output is identical).

- [ ] **Step 8: Commit**

```bash
git add data/adv_mixed_senders.json data/adv_reversed_chronology.json data/adv_unrelated_contamination.json data/adv_interleaved_threads.json data/adv_subject_mismatch.json convergence/evaluation.py tests/test_adversarial_corpora.py
git commit -m "feat: adversarial corpora + tiered eval scaffold (Phase 3 T1)"
```

---

## Task 2: Honest metric reframing + report

**Files:**
- Modify: `convergence/evaluation.py` (reframe `format_report`; add `_format_tier`, `format_tiered_report`)
- Modify: `demo.py` (switch `--eval` to the tiered report)
- Test: `tests/test_evaluation.py` (add report-format assertions)

**Interfaces:**
- Consumes (from T1): `TieredEval`, `evaluate_tiered(data_dir) -> TieredEval`, `EvalResult` (fields `per_corpus, tp, fp, fn, tn, metrics`), `CorpusEval` (fields `name, label, predicted, stage_hits, envelopes, correct`).
- Produces:
  - `_format_tier(title: str, r: EvalResult) -> str` — one tier's section: a `k/N corpora correctly classified` headline, the confusion matrix, the diagnostics line (precision/recall/specificity), and the hard-negative line; `accuracy` demoted out of the headline.
  - `format_report(r: EvalResult) -> str` — reframed to delegate to `_format_tier("corpus-level discrimination", r)` plus the no-generalization caveat (keeps the word "precision"/"recall" present so existing tests hold).
  - `format_tiered_report(t: TieredEval) -> str` — core, adversarial, and (if present) holdout sections + the caveat header.

- [ ] **Step 1: Write the failing report-format tests**

Add to `tests/test_evaluation.py`:

```python
def test_report_is_reframed_as_corpus_level_with_caveat():
    from convergence.evaluation import format_report
    txt = format_report(evaluate([("pos", _ENVELOPE, True), ("neg", _BENIGN, False)]))
    low = txt.lower()
    # honest framing: corpus-level, explicit count, no-generalization caveat
    assert "corpus" in low
    assert "2/2" in txt  # k/N corpora correctly classified
    assert "no statistical generalization" in low or "not a sampled population" in low
    # diagnostics still present (keys unchanged)
    assert "precision" in low and "recall" in low


def test_tiered_report_names_each_tier():
    from convergence.evaluation import evaluate_tiered, format_tiered_report
    DATA = __import__("pathlib").Path(__file__).parent.parent / "data"
    txt = format_tiered_report(evaluate_tiered(DATA)).lower()
    assert "core" in txt and "adversarial" in txt
```

- [ ] **Step 2: Run to verify they fail**

Run: `python -m pytest tests/test_evaluation.py -k "reframed or tiered" -v`
Expected: FAIL (`2/2` not found in the current report; `format_tiered_report` not importable).

- [ ] **Step 3: Reframe `format_report` and add the tier renderers**

Replace the existing `format_report` in `convergence/evaluation.py` with the reframed version and add the two helpers. (The old report's metrics line is preserved as a diagnostics line; the new headline + caveat are added; `accuracy` is moved into the diagnostics line, out of the headline.)

```python
_CAVEAT = (
    "  (N curated corpora - corpus-level discrimination, not a sampled population; "
    "no statistical generalization is claimed.)"
)


def _format_tier(title: str, r: EvalResult) -> str:
    n = r.tp + r.fp + r.fn + r.tn
    correct = r.tp + r.tn
    m = r.metrics
    out = [
        f"{title}: {correct}/{n} corpora correctly classified",
        f"  {'corpus':16}{'label':>10}{'predicted':>11}{'stage_hits':>12}{'envelopes':>11}{'ok':>4}",  # noqa: E501
    ]
    for c in r.per_corpus:
        out.append(f"  {c.name:16}{('coercive' if c.label else 'other'):>10}"
                   f"{('coercive' if c.predicted else 'other'):>11}{c.stage_hits:>12}"
                   f"{c.envelopes:>11}{('y' if c.correct else 'N'):>4}")
    out += [
        f"  confusion:  TP={r.tp}  FP={r.fp}  FN={r.fn}  TN={r.tn}",
        f"  diagnostics: precision={m['precision']:.3f}  recall={m['recall']:.3f}  "
        f"F1={m['f1']:.3f}  specificity={m['specificity']:.3f}  accuracy={m['accuracy']:.3f}",
    ]
    negatives = [c for c in r.per_corpus if not c.label]
    if negatives:
        hard = max(negatives, key=lambda c: c.stage_hits)
        out.append(f"  hard negative: '{hard.name}' fired {hard.stage_hits} hostile stage-hits "
                   f"but {hard.envelopes} false envelopes - specificity holds under load.")
    return "\n".join(out)


def format_report(r: EvalResult) -> str:
    return "\n".join([
        "Coercion-grammar discriminator - corpus-level discrimination",
        _CAVEAT,
        "",
        _format_tier("corpus-level discrimination", r),
    ])


def format_tiered_report(t: TieredEval) -> str:
    out = [
        "Coercion-grammar discriminator - tiered corpus-level discrimination",
        _CAVEAT,
        "",
        _format_tier("CORE (dynamics; behavior-preservation guard)", t.core),
        "",
        _format_tier("ADVERSARIAL (engineered traps + robustness)", t.adversarial),
    ]
    if t.holdout is not None:
        out += [
            "",
            _format_tier("HOLDOUT (blind; generalization - reported, not tuned against)", t.holdout),
        ]
    return "\n".join(out)
```

- [ ] **Step 4: Switch `demo.py --eval` to the tiered report**

In `demo.py`, change the import (line ~32) from:

```python
from convergence.evaluation import evaluate_dynamics, format_report
```

to:

```python
from convergence.evaluation import evaluate_tiered, format_tiered_report
```

and the `--eval` body (line ~205) from:

```python
        print("\n" + format_report(evaluate_dynamics(DATA)))
```

to:

```python
        print("\n" + format_tiered_report(evaluate_tiered(DATA)))
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python -m pytest tests/test_evaluation.py -v`
Expected: PASS — including the pre-existing `test_report_mentions_metrics` (still finds "precision"/"recall") and the new reframed/tiered tests.

- [ ] **Step 6: Smoke-test the demo CLI + full gates**

Run: `python demo.py --eval | head -40 && python -m pytest -q && ruff check . && mypy convergence web && python -m web.build && git diff --exit-code web/site/data/`
Expected: the eval prints CORE then ADVERSARIAL sections with the `k/N corpora correctly classified` headline and the caveat; full suite passes; no web drift (the web build still calls `evaluate_dynamics`, untouched).

- [ ] **Step 7: Commit**

```bash
git add convergence/evaluation.py demo.py tests/test_evaluation.py
git commit -m "feat: reframe eval as honest corpus-level discrimination + tiered report (Phase 3 T2)"
```

---

## Task 3: Blind holdout (fresh-subagent authored)

**Files:**
- Create: `data/holdout/hold_coercive.json`, `data/holdout/hold_cooperative.json`, `data/holdout/hold_hostile.json` (authored by a blind subagent — see Step 1)
- Modify: `convergence/evaluation.py` (fill `HOLDOUT_LABELS`)
- Test: `tests/test_holdout_corpora.py`

**Interfaces:**
- Consumes (from T1/T2): `HOLDOUT_LABELS`, `evaluate_labelset`, `evaluate_tiered -> TieredEval` (now wires `holdout` once `HOLDOUT_LABELS` is non-empty), `format_tiered_report` (already renders the holdout section when present), `classify_coercive`.
- Produces: `HOLDOUT_LABELS = {"hold_coercive.json": True, "hold_cooperative.json": False, "hold_hostile.json": False}` and the three frozen corpora.

- [ ] **Step 1: Author the 3 holdout corpora via a BLIND subagent**

Dispatch a fresh subagent with ONLY the behavioral brief below. **Do not give it `convergence/coercion_grammar.py`, the stage regexes, `FRAGMENTS.md`, or any existing corpus to copy.** This quarantine is what makes the holdout measure generalization rather than the matcher's vocabulary.

Brief to hand the subagent verbatim:

> Write three short synthetic coparenting message logs as JSON files (4–10 messages each). Each message object has EXACTLY: `seq` (int, 1-based, strictly increasing in time order), `thread` (str), `sender` (str), `timestamp` (str ISO like `"2024-08-01T09:00"`), `domain` (str), `body` (str). Fictional names; no real data.
>
> Coercive control, in plain behavioral terms, is ONE party (the coercer) responding to the other party's reasonable proposal not by negotiating but by: first objecting/stonewalling, then questioning the other's standing while asserting borrowed authority for their own position, repeating that push-back, and finally announcing a unilateral decision as already done — leaving no room to respond. The proposal comes from the OTHER (target) party; the coercer drives the push-back and the unilateral conclusion, in time order.
>
> 1. `hold_coercive.json` — a clear case of the above: the target proposes something reasonable; ONE coercer pushes back, justifies with borrowed authority, pushes back again, then announces a done-deal unilateral decision. It should read as coercive to a human.
> 2. `hold_cooperative.json` — two parents who disagree briefly but negotiate in good faith and reach a joint decision. NOT coercive.
> 3. `hold_hostile.json` — a bitter, hostile exchange where BOTH parents attack and refuse — mutual, escalating, with no single party running a one-sided campaign to a unilateral done-deal. NOT coercive (hostility is bilateral).
>
> Write believable natural language; do not optimize for any keyword list. Return the three files written under `data/holdout/`.

The controller does NOT review the bodies for regex-fit (that would re-introduce the leak); it only confirms three valid JSON files exist with the correct keys and that the filenames match.

- [ ] **Step 2: Write the failing test**

Create `tests/test_holdout_corpora.py`:

```python
"""Blind holdout: a frozen, fresh-subagent-authored set scored on a separate
generalization line. We assert the holdout LOADS and SCORES deterministically and
that the tiered report includes it. We deliberately do NOT assert a holdout
pass-rate or per-corpus correctness — asserting that would re-introduce a tuning
signal and defeat the blindness. The number is reported, not chased.
"""
from pathlib import Path

from convergence.corpus import load_corpus
from convergence.evaluation import (
    HOLDOUT_LABELS,
    classify_coercive,
    evaluate_tiered,
    format_tiered_report,
)

DATA = Path(__file__).parent.parent / "data"
HOLDOUT = DATA / "holdout"


def test_holdout_set_is_three_labeled_corpora():
    assert set(HOLDOUT_LABELS) == {
        "hold_coercive.json", "hold_cooperative.json", "hold_hostile.json"
    }
    assert HOLDOUT_LABELS["hold_coercive.json"] is True
    assert HOLDOUT_LABELS["hold_cooperative.json"] is False
    assert HOLDOUT_LABELS["hold_hostile.json"] is False


def test_holdout_corpora_load_and_classify_deterministically():
    for fname in HOLDOUT_LABELS:
        msgs = load_corpus(HOLDOUT / fname)
        assert msgs, f"{fname} is empty"
        first = classify_coercive(msgs)
        second = classify_coercive(msgs)
        assert first == second  # deterministic; value itself is NOT asserted to a target


def test_tiered_report_includes_holdout_line():
    t = evaluate_tiered(DATA)
    assert t.holdout is not None
    assert "holdout" in format_tiered_report(t).lower()
```

- [ ] **Step 3: Run to verify it fails**

Run: `python -m pytest tests/test_holdout_corpora.py -v`
Expected: FAIL — `HOLDOUT_LABELS` is empty (set mismatch) and `t.holdout is None`.

- [ ] **Step 4: Fill `HOLDOUT_LABELS` in `convergence/evaluation.py`**

Replace the placeholder:

```python
HOLDOUT_LABELS: dict[str, bool] = {}
```

with:

```python
HOLDOUT_LABELS: dict[str, bool] = {
    "hold_coercive.json": True,
    "hold_cooperative.json": False,
    "hold_hostile.json": False,
}
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python -m pytest tests/test_holdout_corpora.py -v`
Expected: PASS (3 tests). If the holdout's coercive corpus does NOT classify as coercive (or a negative DOES), that is a genuine generalization finding — record it in the close-out report and surface it to the human. Do NOT edit the holdout corpus or relabel it; the only legitimate response is a separately-decided engine change.

- [ ] **Step 6: Full gates**

Run: `python -m pytest -q && ruff check . && mypy convergence web && python -m web.build && git diff --exit-code web/site/data/ && python demo.py --eval | tail -20`
Expected: all pass; the eval now prints CORE, ADVERSARIAL, and HOLDOUT sections; no web drift.

- [ ] **Step 7: Commit**

```bash
git add data/holdout/hold_coercive.json data/holdout/hold_cooperative.json data/holdout/hold_hostile.json convergence/evaluation.py tests/test_holdout_corpora.py
git commit -m "feat: blind holdout corpus + generalization report line (Phase 3 T3)"
```

---

## Notes for the controller

- **Parallelism (user-authorized):** within T1, the five `adv_*.json` files are independent inputs and may be authored by parallel sub-dispatches; the `evaluation.py` edit is single-threaded within the task. The T3 holdout authoring is a separate blind sub-dispatch. Edits to `convergence/evaluation.py` serialize across T1→T2→T3 (same file) to avoid merge conflicts.
- **The behavior-preservation tripwire** is `t.core` staying at FP=0/FN=0. If any task moves it, engine behavior changed — stop and investigate before merging.
- **Honesty discipline (load-bearing):** a misclassifying adversarial or holdout corpus is surfaced and analyzed, never relabeled or softened. An engine fix is a separate, human-approved decision outside this plan's scope.
- After T3 merges, run the **final whole-branch review on the most capable model** over the Phase-3 span before close-out, with specific attention to: `evaluate_dynamics`/`EvalResult.metrics` truly unchanged (no web drift), the adversarial classifications matching the spec table, the holdout blindness (no target assertion crept into the suite), and a character-corruption scan of the new JSON/string literals.
```
