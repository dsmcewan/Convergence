# Phase 1 — Signal provenance redesign (convergence redesign)

**Goal:** Enrich the `Signal` data model with explicit provenance —
`anchor · actor · thread · target · evidence · support` — derived from the
messages each layer already sees, and thread it through every consumer, **without
changing any engine finding**. This is the keystone the later phases build on
(Phase 2 sender-aware state machine, Phase 3 thread-local omission/pattern,
Phase 4 UI/demo split).

**Status:** design approved 2026-06-30. Sub-project 1 of the five-phase redesign;
Phase 0 (tooling/CI + web hardening) is merged. Build method: **Subagent-Driven
Development** (branch → PR → CI → squash-merge per task, review between, final
whole-branch review). Repo: `dsmcewan/Convergence`.

**Scope boundary (behavior-preserving):** Phase 1 changes the `Signal` shape and
its derivation, the mechanical `.detail → .evidence` rename in consumers, and the
web demo's *display* of the new provenance — but it does **not** change grouping,
elevation, the convergence rule, the corpora, the metrics, or which messages
become findings. The 199 existing tests passing unchanged is the proof of
behavior preservation. Sender/thread-aware *policy* is explicitly deferred to
Phases 2–3.

---

## Context

`Signal` is currently `(layer, seqs, kind, detail)` — a frozen dataclass in
`convergence/engine.py`, constructed in `_collect_signals` across the six layers
and consumed by engine grouping, `composition.py`, `narration.py`,
`web/serialize.py`, and `web/site/app.js` (~143 references). Every `Message`
already carries `seq · thread · sender · domain · timestamp · body`, and the layer
detectors already hold the relevant message (L5 `RegisterAnomaly` and L6
`ChannelDivergence` even carry `sender` explicitly) — but `Signal` discards sender
and thread and crams the proof into a free-text `detail` string. Phases 2–4 need
that discarded provenance: sender-awareness (so a coercive shape can't be assembled
from different senders) and thread-locality (so it can't be assembled across
interleaved threads). Phase 1 surfaces the provenance; the later phases use it.

## The new `Signal`

```python
@dataclass(frozen=True)
class Signal:
    layer: str                  # "L1".."L6" (unchanged)
    kind: str                   # tactic / kind (unchanged)
    anchor: int                 # the single message the move is ABOUT
    actor: str                  # sender of the anchor message
    thread: str                 # thread of the anchor message
    target: str | None          # who the move is aimed at, when determinable; else None
    evidence: str               # the proof/cue string (== today's `detail`, renamed)
    support: tuple[int, ...]    # the move's other seqs (anchor excluded; may be empty)

    @property
    def seqs(self) -> tuple[int, ...]:
        return tuple(sorted({self.anchor, *self.support}))
```

**Behavior-preserving guarantee (the load-bearing property):**
- `seqs` is a derived property that returns the **identical tuple** the engine
  grouped on before the redesign, for every layer (verified per-layer below). So
  `run_engine`'s grouping/elevation/summary and the resulting findings are
  byte-for-byte unchanged.
- `evidence` carries the **exact string** that was `detail`, so `narration` output
  is unchanged.
- `anchor`, `actor`, `thread`, `target`, `support` are new, derived, and tested,
  but no finding depends on them in Phase 1.

`anchor` is the single message the signal is *about*; `support` holds any other
seqs that were part of the old `seqs` tuple (so `anchor ∪ support == old seqs`).

## Per-layer derivation

`_collect_signals(full, ...)` already has the full message list; it builds a
`by_seq: dict[int, Message]` once and derives `actor = by_seq[anchor].sender`,
`thread = by_seq[anchor].thread`.

| layer | kind | anchor | support | target | evidence (== old detail) | old `seqs` it must reproduce |
|---|---|---|---|---|---|---|
| **L1** pattern | `hit.tactic` | `hit.seq` | `()` | None | `hit.cue` | `(hit.seq,)` |
| **L2** omission | `within_thread_omission` | `gap.seq` | `()` | None | `cut between shown {prev} and {next}` | `(gap.seq,)` |
| **L3** third-party | `claim_contradicted` | `c.seq` | `(c.contradicting_seq,)` if not None else `()` | None | `c.basis` | `sorted({c.seq} ∪ {c.contradicting_seq?})` |
| **L4** convergence | `domain_convergence` | `min(cv.seqs)` | `tuple(s for s in sorted(cv.seqs) if s != anchor)` | None | `{cv.anchor} across {', '.join(cv.domains)}` | `cv.seqs` |
| **L5** register | `register_anomaly` | `a.seq` | `()` | None | `a.reason` | `(a.seq,)` |
| **L6** cross-channel | `cross_channel_divergence` | `d.seq` | `()` (the cross-channel seq stays OUT of `seqs`, exactly as today) | None | `d.basis` | `(d.seq,)` |

Notes:
- **L4** has no single message-anchor (its anchor is a *token*, e.g. "weekend"),
  so by convention `anchor = min(cv.seqs)` and the rest go to `support`; `seqs`
  derives to `cv.seqs` unchanged. `actor`/`thread` are the anchor message's (the
  fact that L4 may span senders/threads is what Phase 3 addresses — not Phase 1).
- **L6**'s `support` is empty so `seqs == (d.seq,)` exactly as today (the comment
  in `_collect_signals` notes L6 anchors only on the primary seq so it never
  collides). The contradicting cross-channel message is provenance carried in
  `evidence`/`target`, not in the grouping `seqs`.
- **`target`** is best-effort and conservative: `None` by default, populated
  **only** where a detector can unambiguously name a party the move is directed at
  (e.g. an L1 cue that explicitly names "you/her/him"). L6 is self-contradiction
  (the same sender across two channels), so it has no other-party target → `None`.
  In Phase 1's six layers `target` will frequently be `None` — that is the honest
  outcome; the field exists for the cases that are determinable and for later
  phases (and a future behaviors integration) to populate. No sentinel, no forced
  guessing.

## Consumer migration

- **Engine grouping (`run_engine`):** unchanged — it reads `s.seqs` (now a
  property returning the same value) and `s.layer`/`s.kind`. `_signal_sort_key`
  (the Phase-0 version-stable order) keeps working (it reads `s.layer, s.seqs,
  s.kind, s.detail` → update its last key to `s.evidence`, same values).
- **Mechanical rename:** every read of `.detail` becomes `.evidence` across
  `composition.py`, `narration.py`, and `web/serialize.py`; the six `Signal(...)`
  construction sites in `_collect_signals` are updated to the new keyword args.
  `.seqs` reads are unchanged (the property covers them).
- **Web demo (display the new provenance):** `web/serialize.py` emits `actor`,
  `thread`, `target`, and `anchor` **additively** in each signal's JSON (no
  existing key removed); `web/site/app.js` surfaces them in the rendered finding;
  `web/site/data/*.json` is rebuilt (the demo-data-drift CI gate enforces it
  matches a fresh build); the web-contract / web-serialize tests are updated for
  the additive shape. This is additive provenance *display*, distinct from Phase
  4's UI/demo-architecture split.

## Testing

- **Behavior preservation (primary):** the full existing suite (199 tests) passes
  unchanged — same findings, same narration, same elevated/low verdicts. This is
  the central guard; any drift means the migration changed behavior.
- **New per-layer derivation tests** (in `tests/test_engine.py` or a new
  `tests/test_signal_provenance.py`): for each of L1–L6, build a minimal corpus
  that fires that layer and assert the resulting `Signal` has the correct
  `anchor`, `actor` (= anchor sender), `thread` (= anchor thread), `support`,
  `target`, and that `signal.seqs == <the pre-redesign tuple>` for that layer.
- **`seqs`-equivalence test:** over a representative corpus (e.g. coparenting),
  assert every `signal.seqs` equals what the old construction would have produced
  — i.e. `seqs == tuple(sorted({anchor} | set(support)))` and matches the layer's
  documented value. (Locks the behavior-preserving property against regression.)
- **Web tests:** `test_web_serialize` / `test_web_ui_contract` updated to assert
  the new fields are present and the existing fields are unchanged.
- All gates from Phase 0 stay green: `ruff`, `mypy`, coverage ≥ 80%, tests ×2,
  demo-data-drift; Pages remains test-gated.

## Exit criteria

- `Signal` carries `anchor/actor/thread/target/evidence/support` with `seqs` as a
  derived property; all six layers populate them correctly (tested).
- The 199 pre-existing tests pass unchanged (behavior preserved); new derivation
  tests pass; `ruff`/`mypy`/coverage(≥80)/drift all green on 3.10–3.12.
- `web/serialize.py` + `app.js` + `web/site/data` surface the new provenance; web
  tests updated; the live demo still renders.
- No change to grouping, elevation, the convergence rule, metrics, or corpora.

## Decisions log (brainstorming, 2026-06-30)

- **Phase 1 = enrich only, behavior-preserving.** Add provenance + derivation +
  thread through consumers; keep grouping/elevation identical. The sender/thread
  *policy* changes are Phases 2–3, which now have the fields. Separates model from
  policy; bounds risk; the 199 tests are the proof.
- **`evidence` = proof string + `support` seqs** (not a structured `Evidence`
  object). YAGNI: don't structure the heterogeneous per-layer proof until a
  consumer needs it. `evidence` == today's `detail` (behavior-preserving).
- **`target` = best-effort optional (`None` default).** Populate only where a
  detector can cheaply determine it; no sentinels, no forced guessing.
- **Update `app.js` now** (rather than deferring all UI to Phase 4): surface the
  new provenance in the demo additively. The UI/demo-architecture *split* remains
  Phase 4.
- **`seqs` stays a derived property** so the engine groups on the identical value
  — the mechanism that makes the whole redesign behavior-preserving.

## Non-goals (Phase 1 — YAGNI)

- No sender/thread-aware grouping or elevation policy (Phases 2–3).
- No structured `Evidence` object; no per-layer evidence schemas.
- No coercion-grammar / omission / pattern changes (Phases 2–3).
- No metric rename, holdout corpus, or adversarial corpora (Phase 3).
- No UI/demo-architecture separation (Phase 4) — only additive provenance display.
- No new corpora and no change to existing corpus data.
