# Phase 1 — Signal Provenance Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enrich `Signal` with `anchor/actor/thread/target/evidence/support` (derived from the messages each layer already sees), keep `seqs` as a derived property that returns the identical pre-redesign tuple, and surface the new provenance in the web demo — changing **no** engine finding.

**Architecture:** Two tasks. Task 1 redefines `Signal`, derives the provenance in `_collect_signals`, performs the atomic `.detail → .evidence` rename across the readers (so the suite stays green), and adds derivation tests — `web/site/data` stays byte-identical because `evidence` carries the exact `detail` string and `serialize` keeps the `detail` JSON key. Task 2 adds the new provenance keys to `serialize` and renders them in `app.js`, rebuilding `web/site/data` and updating the web tests.

**Tech Stack:** Python ≥3.10 (stdlib-only runtime), pytest, ruff, mypy, GitHub Actions.

## Global Constraints

- **Behavior-preserving (load-bearing):** grouping, elevation, the convergence rule, narration text, metrics, and which messages become findings are **unchanged**. The 199 existing tests passing unchanged is the proof; any drift means a behavior change.
- `seqs` is a derived property: `tuple(sorted({self.anchor, *self.support}))` — it returns the identical tuple for every layer (verified: `cv.seqs` and L3's old `seqs` are both sorted).
- `evidence` carries the **exact** string that was `detail`; `serialize` keeps the `detail` JSON key (value `s.evidence`) so the web shape is unchanged in Task 1.
- `target` is best-effort, `None` by default — populated only where a detector unambiguously names a directed party; `None` for all six layers in Phase 1's derivation (no forced guessing).
- **No new runtime dependency**; stdlib-only runtime. All Phase-0 gates stay green: `ruff check .`, `mypy convergence web`, coverage ≥ 80%, tests ×2, demo-data-drift, on Python 3.10–3.12.
- Each task lands via its own branch → PR → CI → squash-merge. Implementer commits locally with explicit `git add` (never `-A`).
- **Only these files change.** Task 1: `convergence/engine.py`, `convergence/conversation.py`, `convergence/narration.py`, `web/serialize.py`, `tests/test_engine.py`, new `tests/test_signal_provenance.py`. Task 2: `web/serialize.py`, `web/site/app.js`, `web/site/data/*.json`, `tests/test_web_serialize.py` / `tests/test_web_ui_contract.py`. **`composition.py` is NOT touched** (it reads `s.kind`/`s.seqs`, never `Signal.detail`).

## File Structure

- `convergence/engine.py` — `Signal` redefinition (new fields + `seqs` property), `_collect_signals` derivation, `_signal_sort_key` last key `.detail`→`.evidence`.
- `convergence/conversation.py`, `convergence/narration.py` — `Signal.detail`→`.evidence` reads (leave `Pattern.detail` reads alone).
- `web/serialize.py` — Task 1: `s.detail`→`s.evidence` (JSON key unchanged). Task 2: add `actor/thread/target/anchor` keys.
- `web/site/app.js` — Task 2: render `actor/thread/target` additively.
- `tests/` — fix the `Signal`-constructing test; add provenance derivation tests; update web tests.

---

### Task 1: New `Signal` model, derivation, atomic rename, and provenance tests

**Files:**
- Modify: `convergence/engine.py` (`Signal`, `_collect_signals`, `_signal_sort_key`)
- Modify: `convergence/conversation.py:63`, `convergence/narration.py` (Signal `.detail`→`.evidence`)
- Modify: `web/serialize.py:179` (`s.detail`→`s.evidence`; JSON key stays `"detail"`)
- Modify: `tests/test_engine.py` (the `Signal`-constructing test)
- Create: `tests/test_signal_provenance.py`

**Interfaces:**
- Produces: `Signal(layer: str, kind: str, anchor: int, actor: str, thread: str, target: str | None, evidence: str, support: tuple[int, ...] = ())` with `@property seqs -> tuple[int, ...]`. The old `Signal(layer, seqs, kind, detail)` is gone; `.detail` is gone (renamed `evidence`); `.seqs` is now a property.

- [ ] **Step 1: Redefine `Signal` in `convergence/engine.py`.** Replace the existing `Signal` dataclass with:

```python
@dataclass(frozen=True)
class Signal:
    layer: str                  # "L1".."L6"
    kind: str                   # tactic / kind
    anchor: int                 # the single message the move is ABOUT
    actor: str                  # sender of the anchor message
    thread: str                 # thread of the anchor message
    target: str | None          # who the move is aimed at, when determinable; else None
    evidence: str               # the proof/cue string (was `detail`)
    support: tuple[int, ...] = ()  # the move's other seqs (anchor excluded)

    @property
    def seqs(self) -> tuple[int, ...]:
        return tuple(sorted({self.anchor, *self.support}))
```

- [ ] **Step 2: Update `_signal_sort_key`** in `convergence/engine.py` — change the last key from `s.detail` to `s.evidence` (same values, version-stable order preserved):

```python
def _signal_sort_key(s) -> tuple:
    """Total, version-stable ordering key for a Signal: (layer, seqs, kind, evidence)."""
    return (_LAYER_ORDER.get(s.layer, 99), s.seqs, s.kind, s.evidence)
```

- [ ] **Step 3: Rewrite `_collect_signals`** in `convergence/engine.py` to derive the provenance. Replace the whole function with:

```python
def _collect_signals(full, included_seqs, records, cross_channel) -> list[Signal]:
    by_seq = {m.seq: m for m in full}

    def prov(anchor: int) -> tuple[str, str]:
        m = by_seq.get(anchor)
        return (m.sender, m.thread) if m else ("", "")

    signals: list[Signal] = []
    for h in detect_patterns(full):
        actor, thread = prov(h.seq)
        signals.append(Signal("L1", h.tactic, h.seq, actor, thread, None, h.cue))
    if included_seqs is not None:
        for g in find_omissions(full, included_seqs):
            if g.within_thread:
                actor, thread = prov(g.seq)
                signals.append(Signal(
                    "L2", "within_thread_omission", g.seq, actor, thread, None,
                    f"cut between shown {g.prev_seq} and {g.next_seq}"))
    if records is not None:
        for c in check_claims(full, records):
            actor, thread = prov(c.seq)
            support = (c.contradicting_seq,) if c.contradicting_seq is not None else ()
            signals.append(Signal(
                "L3", "claim_contradicted", c.seq, actor, thread, None, c.basis, support))
    if cross_channel is not None:
        # L6 anchors only on the primary seq (support stays empty) so it never
        # collides with an unrelated primary message — exactly as before.
        for d in find_cross_channel_divergences(full, cross_channel):
            actor, thread = prov(d.seq)
            signals.append(Signal(
                "L6", "cross_channel_divergence", d.seq, actor, thread, None, d.basis))
    for cv in find_convergences(full):
        anchor = min(cv.seqs)
        support = tuple(s for s in sorted(cv.seqs) if s != anchor)
        actor, thread = prov(anchor)
        signals.append(Signal(
            "L4", "domain_convergence", anchor, actor, thread, None,
            f"{cv.anchor} across {', '.join(cv.domains)}", support))
    for a in detect_register_anomalies(full):
        actor, thread = prov(a.seq)
        signals.append(Signal(
            "L5", "register_anomaly", a.seq, actor, thread, None, a.reason))
    return signals
```

- [ ] **Step 4: Rename the Signal `.detail` reads in the consumers** (leave `Pattern.detail` reads untouched):
  - `convergence/conversation.py:63` — `{s.detail}` → `{s.evidence}`.
  - `convergence/narration.py` — at the Signal sites only: line ~74 `lambda s: (_l4_specificity(s.detail), s.detail)` → `(_l4_specificity(s.evidence), s.evidence)`; line ~76 `f"    - [{s.layer}] {s.detail}"` → `{s.evidence}`; line ~78 same; line ~149 `f"   {conj} the {s.layer} thread - {s.detail}."` → `{s.evidence}`; line ~157 `self._mark(body, s.detail)` → `s.evidence`; line ~399 `self._mark(self._bodies[seq], spoken[0].detail)` → `spoken[0].evidence`. **Do NOT change** `narration.py:435` / `:453` (those are `p.detail` = `Pattern.detail`).
  - `web/serialize.py:179` — `"detail": s.detail,` → `"detail": s.evidence,` (the JSON key stays `"detail"`; only the field read changes).

- [ ] **Step 5: Fix the `Signal`-constructing test in `tests/test_engine.py`.** The test `test_signal_order_is_canonical_and_input_independent` builds `Signal` positionally with the old 4-arg shape and reads `.detail`. Replace its body with the new constructor (keyword args) and `.evidence`:

```python
def test_signal_order_is_canonical_and_input_independent():
    # Multiple L4 corroborators on one anchor: their emission order from
    # find_convergences can vary with set/dict iteration (and thus across Python
    # versions), so a finding must impose a total, version-stable signal order.
    a = Signal("L4", "domain_convergence", 8, "Sam", "T", None, "weekend across medical, schedule")
    b = Signal("L4", "domain_convergence", 8, "Sam", "T", None, "agreed across medical, schedule")
    c = Signal("L4", "domain_convergence", 8, "Sam", "T", None, "swap across medical, schedule")
    forward = sorted([a, b, c], key=_signal_sort_key)
    reverse = sorted([c, b, a], key=_signal_sort_key)
    assert forward == reverse  # final order does not depend on input order
    # canonical: ascending by evidence within the same layer + seqs
    assert [s.evidence for s in forward] == sorted(s.evidence for s in (a, b, c))
    # substantive layers sort before contextual ones regardless of input order
    sub = Signal("L1", "borrow_authority", 8, "Sam", "T", None, "lawyer says")
    assert sorted([a, sub], key=_signal_sort_key)[0] is sub
```

(The other test, `test_engine_emits_signals_in_canonical_order`, does not construct `Signal` and needs no change — it reads `f.signals` via `_signal_sort_key`, which now uses `evidence`.)

- [ ] **Step 6: Run the full existing suite — it must pass unchanged (behavior-preservation proof):**

```bash
pytest -q
```
Expected: `199 passed` (the same count). If any corpus/narration/snapshot test fails, the migration changed behavior — fix the derivation (most likely a `seqs` or `evidence` mismatch), do NOT edit the snapshot.

- [ ] **Step 7: Write the provenance derivation tests.** Create `tests/test_signal_provenance.py`:

```python
"""Phase 1: Signal carries correct provenance, derived from the anchor message."""
import json
from pathlib import Path

from convergence.corpus import Message, load_corpus
from convergence.records import load_records
from convergence.engine import run_engine

DATA = Path(__file__).parent.parent / "data"


def _msg(seq, sender, domain, body, thread="T"):
    return Message(seq=seq, thread=thread, sender=sender, timestamp="t", domain=domain, body=body)


def _coparenting():
    full = load_corpus(DATA / "coparenting_full.json")
    included = json.loads((DATA / "coparenting_exhibit.json").read_text(encoding="utf-8"))["included_seqs"]
    records = load_records(DATA / "coparenting_records.json")
    return run_engine(full, included_seqs=included, records=records), {m.seq: m for m in full}


def test_actor_and_thread_derive_from_the_anchor_message():
    result, by_seq = _coparenting()
    assert result.all_signals  # the corpus fires several layers
    for s in result.all_signals:
        anchor_msg = by_seq[s.anchor]
        assert s.actor == anchor_msg.sender
        assert s.thread == anchor_msg.thread


def test_seqs_property_is_anchor_union_support_sorted():
    result, _ = _coparenting()
    for s in result.all_signals:
        assert s.anchor in s.seqs
        assert s.seqs == tuple(sorted({s.anchor, *s.support}))
        assert s.anchor not in s.support  # anchor is excluded from support


def test_l3_contradiction_carries_the_contradicting_seq_in_support():
    result, _ = _coparenting()
    l3 = [s for s in result.all_signals if s.layer == "L3"]
    assert l3, "coparenting corpus should produce an L3 contradiction"
    # an L3 signal spanning two messages keeps the contradicting seq in support
    multi = [s for s in l3 if len(s.seqs) > 1]
    assert multi, "expected at least one two-seq L3 contradiction"
    for s in multi:
        assert len(s.support) == 1 and s.support[0] != s.anchor


def test_l1_pattern_anchor_actor_evidence():
    # A lone borrow-authority message: anchor=its seq, actor=its sender, evidence=the cue.
    msgs = [_msg(1, "Mara", "scope", "my accountant says I am not approving the authorization")]
    result = run_engine(msgs)
    l1 = [s for s in result.all_signals if s.layer == "L1"]
    assert l1
    s = l1[0]
    assert s.anchor == 1 and s.actor == "Mara" and s.thread == "T"
    assert s.support == () and s.target is None
    assert "accountant" in s.evidence


def test_target_defaults_to_none_in_phase1_layers():
    result, _ = _coparenting()
    assert all(s.target is None for s in result.all_signals)
```

- [ ] **Step 8: Run the new tests + the full suite + the gates:**

```bash
pytest tests/test_signal_provenance.py -q
pytest -q
ruff check . && mypy convergence web
pytest --cov=convergence --cov=web --cov-fail-under=80 -q
```
Expected: new provenance tests pass; full suite `204 passed` (199 + 5 new); ruff/mypy clean; coverage gate exit 0. **Confirm `web/site/data` is unchanged:** `git diff --exit-code web/site/data/` (Task 1 must not alter the demo data — `evidence` carries the same string and the `detail` JSON key is unchanged).

- [ ] **Step 9: Commit.**

```bash
git add convergence/engine.py convergence/conversation.py convergence/narration.py web/serialize.py tests/test_engine.py tests/test_signal_provenance.py
git commit -m "feat: Signal provenance model (anchor/actor/thread/target/evidence/support), behavior-preserving"
```

---

### Task 2: Surface provenance in the web demo

**Files:**
- Modify: `web/serialize.py` (`_signal`: add `actor/thread/target/anchor` keys)
- Modify: `web/site/app.js` (render the new provenance)
- Modify: `web/site/data/*.json` (rebuilt)
- Modify: `tests/test_web_serialize.py` and/or `tests/test_web_ui_contract.py`

**Interfaces:**
- Consumes: the `Signal` provenance fields from Task 1.
- Produces: each serialized signal gains `"actor"`, `"thread"`, `"target"`, `"anchor"` (the existing `layer/seqs/kind/detail` keys are unchanged).

- [ ] **Step 1: Add the failing web-serialize test.** In `tests/test_web_serialize.py`, add (use the module's existing corpus-loading helper; if it serializes the contractor corpus, mirror that):

```python
def test_signal_json_includes_provenance_fields():
    from web.serialize import serialize_corpus
    data = serialize_corpus("contractor")
    sigs = [s for f in data["findings"] for s in f["signals"]]
    assert sigs, "contractor corpus should produce signals"
    for s in sigs:
        # additive provenance — existing keys still present
        assert {"layer", "seqs", "kind", "detail"} <= set(s)
        # new keys
        assert {"actor", "thread", "target", "anchor"} <= set(s)
        assert isinstance(s["actor"], str) and isinstance(s["thread"], str)
        assert s["anchor"] in s["seqs"]
        assert s["target"] is None or isinstance(s["target"], str)
```

- [ ] **Step 2: Run it — expect failure** (new keys absent):

```bash
pytest tests/test_web_serialize.py -q -k "provenance"
```
Expected: FAIL (KeyError / assertion on missing `actor`).

- [ ] **Step 3: Add the provenance keys in `web/serialize.py`'s `_signal`:**

```python
def _signal(s: Signal) -> dict[str, Any]:
    return {
        "layer": s.layer,
        "seqs": list(s.seqs),
        "kind": s.kind,
        "detail": s.evidence,
        "anchor": s.anchor,
        "actor": s.actor,
        "thread": s.thread,
        "target": s.target,
    }
```

- [ ] **Step 4: Render the provenance in `web/site/app.js`.** In the signal-card template (around line 405–411), add an actor/thread line and, when present, a target — additively (keep the existing `signal.detail` line):

```javascript
      ${finding.signals.map((signal, index) => `
        <article class="signal-card layer-${escapeHtml(signal.layer)}" style="--d:${index * 95}ms">
          <span>${escapeHtml(signal.layer)} / ${escapeHtml(LAYER_LABELS[signal.layer] || "signal")}</span>
          <strong>${escapeHtml(signal.kind)}</strong>
          <p>${escapeHtml(signal.detail)}</p>
          <small>${escapeHtml(signal.actor)} · thread ${escapeHtml(signal.thread)}${signal.target ? ` · re: ${escapeHtml(signal.target)}` : ""}</small>
          <small>seqs ${escapeHtml(signal.seqs.join(", "))}</small>
        </article>
      `).join("")}
```

(The other signal renders — `reviewMarkup` line ~820 and the copy-text at line ~1037 — may stay as they are; they read `signal.detail`, which still exists. Optionally add `signal.actor` to the copy-text line, but it is not required.)

- [ ] **Step 5: Rebuild the demo data:**

```bash
python -m web.build
```
This regenerates `web/site/data/*.json` with the new signal keys. Confirm only the expected change: `git status web/site/data/` shows the JSON files modified (new `actor/thread/target/anchor` keys present).

- [ ] **Step 6: Run the web tests + full suite + gates:**

```bash
pytest tests/test_web_serialize.py tests/test_web_ui_contract.py -q
pytest -q
ruff check . && mypy convergence web
python -m web.build && git diff --exit-code web/site/data/   # drift gate: data matches a fresh build
```
Expected: web tests pass (incl. the new provenance assertion); full suite green; ruff/mypy clean; drift check clean (exit 0). If `test_web_ui_contract` asserts an exact key set per signal, update its expected set to include the four new keys (do NOT remove the existing ones).

- [ ] **Step 7: Commit.**

```bash
git add web/serialize.py web/site/app.js web/site/data tests/test_web_serialize.py tests/test_web_ui_contract.py
git commit -m "feat: surface signal provenance (actor/thread/target/anchor) in the web demo"
```

---

## Notes for the executor

- The controller pre-creates each task's branch; implementers commit LOCALLY (explicit `git add` of the listed paths). The controller pushes → PR → CI → squash-merge.
- **The 199-tests-green requirement in Task 1 is the load-bearing guard** — it proves the model migration changed no finding. If a corpus snapshot test fails, the derivation is wrong (a `seqs` or `evidence` mismatch); fix the derivation, never the snapshot.
- **Do not touch `composition.py`** — it reads `s.kind`/`s.seqs`, never `Signal.detail`.
- **Do not change grouping, elevation, the convergence rule, metrics, or corpora.** `seqs` as a sorted property reproduces every layer's old tuple exactly (`cv.seqs` and L3's old `seqs` are both already sorted).
- Task 1 must leave `web/site/data` byte-identical (Step 8 checks it); Task 2 is the only task that changes the demo data.
- `target` is `None` for all six layers in this phase — that is the spec-intended honest outcome; the field exists for later phases. Do not invent target values.
