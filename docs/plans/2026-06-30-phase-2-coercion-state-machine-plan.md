# Phase 2 — Sender-aware Ordered Coercion State Machine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `match_grammar`'s stage-counting with a per-coercer ordered state machine — a proposer's action opens the episode, then one coercer (owning stages 2/3/4/5/6) runs ≥1 ordered refuse→legitimize round and a fait, all increasing in `seq` — so a coercive envelope can't be assembled across senders or out of order.

**Architecture:** Two tasks in `convergence/coercion_grammar.py`. Task 1 adds `sender` to `StageHit` (additive; old `match_grammar` keeps working). Task 2 rewrites `match_grammar` to run the per-coercer ordered machine, adds `coercer` to `GrammarMatch`, and updates/extends the tests. `match_grammar`/`classify_coercive` signatures are stable; the 5-corpus dynamics eval stays precision=recall=F1=1.00.

**Tech Stack:** Python ≥3.10 (stdlib-only), pytest, ruff, mypy.

## Global Constraints

- **The coercer owns stages 2/3/4/5/6** (objection · obstruction · question · justify · fait). **The action (1) opens the episode and is the proposer's — any party** (the good-faith request being steamrolled; typically the victim's). Verified against `dyn_coercive` (Rosa's action → Victor's war+fait) and `_full_thread` (Alex's action → Sam's war+fait).
- **Ordered, by `seq`:** transitions fire only on strictly increasing `seq`. A *complete* envelope = an action (any party) → ≥1 ordered round (coercer refusal `2/3` then a later coercer legitimacy `4/5`) → coercer fait `6` (requires `cycles ≥ 1`).
- **The 5 labeled dynamics corpora MUST still score precision=recall=F1=1.00.** `dyn_coercive` must complete (both `preschool` and `summer` threads, coercer = Victor); `cooperative`/`parallel`/`conflicted`/`high_conflict` must NOT. If `dyn_coercive` genuinely fails to complete, STOP and surface it — re-baseline a corpus only with explicit justification; never weaken the machine.
- **Interface stability:** `match_grammar(messages) -> list[GrammarMatch]` and `classify_coercive(messages) -> bool` keep their signatures. `StageHit` gains `sender: str`; `GrammarMatch` gains `coercer: str`.
- **Unchanged:** the six stage regexes, `_REFUSAL`/`_LEGITIMACY` groups, thread grouping, every other engine layer, `evaluation.py`.
- **No new runtime dependency.** All Phase-0/1 gates stay green: `ruff check .`, `mypy convergence web`, coverage ≥ 80%, tests ×2, demo-data-drift, on Python 3.10–3.12.
- Each task lands via its own branch → PR → CI → squash-merge. Implementer commits locally with explicit `git add`.

## File Structure

- `convergence/coercion_grammar.py` — Task 1: `StageHit.sender` + `tag_stages`. Task 2: `GrammarMatch.coercer`, the `_run_envelope` state machine, the `match_grammar` rewrite.
- `tests/test_coercion_grammar.py` — Task 1: a sender-on-hit test. Task 2: re-baseline `cycles` (3→2) and add the `coercer` assertion + the 4 new state-machine unit tests.
- `tests/test_dynamics_corpora.py` — Task 2: keep the 1.00 classification outcomes; add a `coercer` check on `dyn_coercive`.

---

### Task 1: `StageHit` gains `sender`

**Files:**
- Modify: `convergence/coercion_grammar.py` (`StageHit`, `tag_stages`)
- Modify: `tests/test_coercion_grammar.py` (add one test)

**Interfaces:**
- Produces: `StageHit(seq, stage, name, cue, sender)` — `tag_stages` populates `sender` from each message. The old `match_grammar` ignores it (still works).

- [ ] **Step 1: Add the failing test.** In `tests/test_coercion_grammar.py`, add:

```python
def test_tag_stages_carries_sender():
    hits = tag_stages([_msg(1, "I don't agree that this weekend works.", sender="Victor")])
    assert hits and all(h.sender == "Victor" for h in hits)
```

- [ ] **Step 2: Run it — expect failure** (`StageHit` has no `sender`):

```bash
pytest tests/test_coercion_grammar.py -q -k "carries_sender"
```
Expected: FAIL (`TypeError`/`AttributeError`).

- [ ] **Step 3: Add the field + populate it.** In `convergence/coercion_grammar.py`:

```python
@dataclass(frozen=True)
class StageHit:
    seq: int
    stage: int
    name: str
    cue: str
    sender: str
```

and in `tag_stages`, change the construction to pass the sender:

```python
                out.append(StageHit(seq=m.seq, stage=s.num, name=s.name, cue=hit.group(0), sender=m.sender))
```

- [ ] **Step 4: Run the test + the full suite** (old `match_grammar` still works — it ignores `sender`):

```bash
pytest tests/test_coercion_grammar.py -q
pytest -q
```
Expected: the new test passes; full suite green (unchanged count + 1).

- [ ] **Step 5: Gates + commit.**

```bash
ruff check . && mypy convergence web
git add convergence/coercion_grammar.py tests/test_coercion_grammar.py
git commit -m "feat: StageHit carries sender (enables sender-aware grammar)"
```

---

### Task 2: The per-coercer ordered state machine

**Files:**
- Modify: `convergence/coercion_grammar.py` (`GrammarMatch`, new `_run_envelope`, `match_grammar` rewrite)
- Modify: `tests/test_coercion_grammar.py` (re-baseline `cycles`; add `coercer`; 4 new unit tests)
- Modify: `tests/test_dynamics_corpora.py` (add a `coercer` check)

**Interfaces:**
- Consumes: `StageHit.sender` (Task 1), `_REFUSAL = {2,3}`, `_LEGITIMACY = {4,5}` (unchanged).
- Produces: `GrammarMatch(..., coercer: str)`; `match_grammar` signature unchanged; `classify_coercive` unchanged.

- [ ] **Step 1: Add the failing state-machine unit tests.** In `tests/test_coercion_grammar.py`, add (these encode the spec's guards):

```python
def _coercion_thread(coercer="Victor", proposer="Rosa", thread="t"):
    # proposer's action opens it; the coercer runs refuse->legitimize x2 then faits.
    return [
        _msg(1, "Can we decide on preschool together like we agreed?", sender=proposer, thread=thread),
        _msg(2, "I don't agree to the ones you picked.", sender=coercer, thread=thread),          # refusal (2)
        _msg(3, "On what basis are you choosing without consulting me?", sender=coercer, thread=thread),  # legitimacy (4)
        _msg(4, "I still don't agree to your list.", sender=coercer, thread=thread),               # refusal (2)
        _msg(5, "Per the agreement, I have decision-making too.", sender=coercer, thread=thread),   # legitimacy (5)
        _msg(6, "It's already done - I enrolled her at Oakwood.", sender=coercer, thread=thread),   # fait (6)
    ]


def test_single_coercer_envelope_completes():
    m = match_grammar(_coercion_thread())
    assert len(m) == 1
    assert m[0].complete and m[0].coercer == "Victor"
    assert m[0].cycles >= 1
    assert m[0].has_action and m[0].has_fait_accompli


def test_envelope_split_across_two_senders_does_not_complete():
    # The refusals come from one sender, the legitimacy+fait from another:
    # no single sender owns the ordered refuse->legitimize->fait war.
    msgs = [
        _msg(1, "Can we decide on preschool together like we agreed?", sender="Rosa", thread="t"),
        _msg(2, "I don't agree to the ones you picked.", sender="Pat", thread="t"),      # refusal by Pat
        _msg(3, "On what basis are you choosing without consulting me?", sender="Victor", thread="t"),  # legitimacy by Victor
        _msg(4, "It's already done - I enrolled her at Oakwood.", sender="Victor", thread="t"),  # fait by Victor
    ]
    assert [x for x in match_grammar(msgs) if x.complete] == []


def test_reverse_seq_order_does_not_complete():
    # The same single-coercer cues, but the fait precedes the war precedes the action.
    base = _coercion_thread()
    reversed_seqs = [
        _msg(7 - m.seq, m.body, sender=m.sender, thread=m.thread) for m in base
    ]
    assert [x for x in match_grammar(reversed_seqs) if x.complete] == []


def test_bilateral_hostility_is_not_a_single_coercer_envelope():
    # Both parties refuse and justify; neither runs a lone ordered action->war->fait.
    msgs = [
        _msg(1, "Can we confirm the schedule like we agreed?", sender="Rosa", thread="t"),
        _msg(2, "I don't agree.", sender="Victor", thread="t"),
        _msg(3, "On what basis do you decide?", sender="Rosa", thread="t"),
        _msg(4, "I'm only protecting her, the order stands.", sender="Victor", thread="t"),
        _msg(5, "That's not acceptable.", sender="Rosa", thread="t"),
    ]
    assert [x for x in match_grammar(msgs) if x.complete] == []
```

- [ ] **Step 2: Run them — expect failures** (`coercer` field missing; old counting machine misbehaves on these):

```bash
pytest tests/test_coercion_grammar.py -q -k "single_coercer or split_across or reverse_seq or bilateral"
```
Expected: FAIL.

- [ ] **Step 3: Add `coercer` to `GrammarMatch`.** In `convergence/coercion_grammar.py`:

```python
@dataclass(frozen=True)
class GrammarMatch:
    thread: str
    coercer: str
    seqs: tuple[int, ...]
    stages_present: tuple[int, ...]
    has_action: bool
    has_fait_accompli: bool
    cycles: int                  # ordered refuse->legitimize rounds before the fait
    status_quo_seq: int | None   # the fait accompli that set the status quo
    complete: bool
    summary: str
```

- [ ] **Step 4: Add the ordered state machine** `_run_envelope`, and rewrite `match_grammar`:

```python
def _run_envelope(hits: list[StageHit], coercer: str) -> tuple[int, bool]:
    """Ordered per-coercer machine over seq-sorted hits.
    An action (1, any party) opens it; then the coercer runs >=1 ordered
    refuse(2/3)->legitimize(4/5) round and a fait(6). Returns (cycles, complete)."""
    state = "S0"
    cycles = 0
    for h in hits:
        if state == "S0":
            if h.stage == 1:                      # the proposal opens it (any sender)
                state = "OPENED"
            continue
        if h.sender != coercer:                   # only the coercer drives the war/fait
            continue
        if state == "OPENED" and h.stage in _REFUSAL:
            state = "REFUSED"
        elif state == "REFUSED" and h.stage in _LEGITIMACY:
            cycles += 1
            state = "CYCLED"
        elif state == "CYCLED" and h.stage in _REFUSAL:
            state = "REFUSED"                     # start the next round
        elif state == "CYCLED" and h.stage == 6 and cycles >= 1:
            state = "COMPLETE"
            break
    return cycles, state == "COMPLETE"


def match_grammar(messages: list[Message]) -> list[GrammarMatch]:
    by_thread: dict[str, list[Message]] = defaultdict(list)
    for m in messages:
        by_thread[m.thread].append(m)

    out: list[GrammarMatch] = []
    for thread, msgs in sorted(by_thread.items()):
        hits = tag_stages(msgs)  # already sorted by (seq, stage)
        if not hits:
            continue
        has_action = any(h.stage == 1 for h in hits)
        # candidate coercers: any sender who shows war activity (refusal/legitimacy)
        # OR a fait. (A war without a fait, or a fait without a war, still yields a
        # PARTIAL match — preserving the incomplete/fait-alone behavior.)
        candidates = sorted({
            h.sender for h in hits
            if h.stage in _REFUSAL or h.stage in _LEGITIMACY or h.stage == 6
        })
        for coercer in candidates:
            cycles, complete = _run_envelope(hits, coercer)
            coercer_faits = [h.seq for h in hits if h.stage == 6 and h.sender == coercer]
            has_fait_c = bool(coercer_faits)
            if cycles < 1 and not has_fait_c:
                continue  # no coercion-grammar activity for this candidate (mirrors old skip)
            status_quo_seq = max(coercer_faits) if has_fait_c else None
            env = [h for h in hits if h.sender == coercer or h.stage == 1]
            sq = (f"; fait accompli at seq {status_quo_seq} set the status quo"
                  if status_quo_seq is not None else "")
            out.append(GrammarMatch(
                thread=thread,
                coercer=coercer,
                seqs=tuple(sorted({h.seq for h in env})),
                stages_present=tuple(sorted({h.stage for h in env})),
                has_action=has_action,
                has_fait_accompli=has_fait_c,
                cycles=cycles,
                status_quo_seq=status_quo_seq,
                complete=complete,
                summary=(f"{thread}: {'complete' if complete else 'partial'} coercion grammar by "
                         f"{coercer} - action={has_action}, {cycles} ordered refuse-legitimize "
                         f"round(s){sq}"),
            ))
    return out
```

Notes for the implementer:
- `classify_coercive` is unchanged (`any(m.complete for m in match_grammar(messages))`).
- A bare second refusal while in `REFUSED` is a no-op (stays `REFUSED`); a second legitimacy while in `CYCLED` is a no-op (stays `CYCLED`) — a round is exactly one refusal followed by one later legitimacy. This makes `cycles` deterministic.
- `status_quo_seq` is the coercer's fait seq (the one that completed), or `None`.

- [ ] **Step 5: Re-baseline the existing `cycles` assertions.** The old `cycles = min(len(refusal), len(legitimacy))` gave 3 on `_full_thread`; the new ordered-round count is **2** (rounds: refuse@2→legit@4, refuse@6→legit@7; refusal@3 and legit@5 are absorbed). Update `tests/test_coercion_grammar.py`:
  - `test_cycles_counted`: `assert m[0].cycles == 3` → `assert m[0].cycles == 2  # ordered refuse->legitimize rounds (was min-count 3)`.
  - `test_cycles_counted_only_before_the_fait_accompli`: the `cycles == 3` assertion → `cycles == 2` (the post-fait seq still adds nothing). Keep the `status_quo_seq == 8` assertion (unchanged — the fait is still seq 8).
  - `test_complete_envelope_detected` / `test_incomplete_without_fait_accompli` / `test_fait_accompli_alone_is_not_complete`: confirm they still hold (the `_full_thread` coercer is "Sam", who owns 2-8; `complete` true; a fait with no prior round is not complete). If any asserts `len(m) == 1`, it still holds (only "Sam" is a candidate; "Alex" made only the action). Adjust only if a `cycles`/`coercer` value is asserted.
  - `test_incomplete_without_fait_accompli` (war, no fait), `test_fait_accompli_alone_is_not_complete` (fait, no war), and `test_grouped_by_thread` must still pass unchanged — the broadened candidate set (any sender with a war OR fait stage) and the `cycles < 1 and not has_fait_c` skip preserve exactly these partial/fait-alone/grouped behaviors. Confirm them; do not edit them (they assert no `cycles` constant).
  - **Run the existing file and fix each asserted constant to the value the new machine produces — do NOT change what is being tested, only the expected numbers, and only where the ordered semantics legitimately differ from min-counting. Record each change.**

- [ ] **Step 6: Update `tests/test_dynamics_corpora.py`** — keep all classification outcomes (coercive completes; the 4 negatives don't) and add a coercer check:

```python
def test_coercive_envelopes_are_single_coercer():
    complete = _complete("coercive")
    assert complete, "coercive must still complete under the sender-aware machine"
    assert all(m.coercer == "Victor" for m in complete)  # one coercer drives every envelope
```

- [ ] **Step 7: Verify the eval holds at 1.00 (the load-bearing check).**

```bash
python -c "from convergence.evaluation import evaluate_dynamics; r = evaluate_dynamics('data'); print(r.metrics); print([(c.name, c.label, c.predicted) for c in r.per_corpus])"
```
Expected: `{'precision': 1.0, 'recall': 1.0, 'f1': 1.0, 'specificity': 1.0, 'accuracy': 1.0}` and `coercive` predicted True, the other four False. **If `coercive` predicts False (the strict machine rejected `dyn_coercive`), STOP and report BLOCKED with the thread + where the machine stalls — do NOT weaken the machine; a corpus re-baseline needs explicit human sign-off.**

- [ ] **Step 8: Full suite + gates.**

```bash
pytest -q
ruff check . && mypy convergence web
pytest --cov=convergence --cov=web --cov-fail-under=80 -q
python -m web.build && git diff --exit-code web/site/data/
```
Expected: full suite green (new unit tests pass, re-baselined cycles pass, dynamics eval 1.00); ruff/mypy clean; coverage ≥ 80; demo-data-drift clean (the coercer field is not serialized to the web, so `web/site/data` should be unchanged — if `web/build` touches it, investigate).

- [ ] **Step 9: Commit.**

```bash
git add convergence/coercion_grammar.py tests/test_coercion_grammar.py tests/test_dynamics_corpora.py
git commit -m "feat: sender-aware ordered coercion state machine (replaces stage-counting)"
```

---

## Notes for the executor

- The controller pre-creates each task's branch; implementers commit LOCALLY (explicit `git add`). The controller pushes → PR → CI → squash-merge.
- **The 1.00 dynamics eval is the load-bearing guard (Step 7).** The corrected attribution (coercer owns 2/3/4/5/6; action is the proposer's) is exactly what makes `dyn_coercive` (Rosa's action → Victor's war+fait) complete — if it does NOT complete, something is wrong with the machine or the corpus genuinely changed; surface it, never weaken the machine to force the number.
- **`cycles` semantics changed** from `min(len(refusal), len(legitimacy))` to ordered refuse→legitimize rounds — the `_full_thread` value drops 3→2. This is the only expected test re-baseline; change the expected constant, not the assertion's intent.
- Do not touch the six stage regexes, `_REFUSAL`/`_LEGITIMACY`, thread grouping, `evaluation.py`, or any other layer.
- Adversarial regression corpora (mixed senders / interleaved threads / subject mismatch / unrelated-pattern contamination), the metric rename, and the blind holdout are **Phase 3** — not here.
