# Phase 4 — Generic engine UI / curated Blanc lecture separation

**Goal:** Separate the **generic, corpus-agnostic engine output** from the **curated
Benoit-Blanc lecture-demo** that currently wraps it — establishing a real code
boundary (`web/serialize.py` generic core has no Blanc dependency) plus a standalone
plain "engine view" page — and lock the (already-satisfied) thread-locality property
of `run_engine` with an explicit characterization test.

**Status:** design approved 2026-06-30. Final planned phase of the convergence
redesign; Phases 0 (tooling/web hardening), 1 (Signal provenance), 2 (sender-aware
coercion machine), 3 (evaluation honesty), and the engine recall-fix phase are all
merged. Build method: **Subagent-Driven Development**. Repo: `dsmcewan/Convergence`.

**Scope boundary (presentation/architecture refactor + one test):** Phase 4 changes
only the **web serialization/UI layer** (`web/serialize.py`, a new `web/curated.py`,
`web/build.py`, `web/site/`), adds one engine-invariant **test**, and rebuilds
`web/site/data/`. It does **not** change any engine finding, layer, elevation rule,
the coercion machine, the eval tiers, or any corpus. The generic serialized values
are byte-identical to today; the Blanc output merely moves under a `curated` section.

---

## Context

The current web demo is a single curated artifact: `web/site/index.html` is a
"disembodied Blanc lecture" slideshow (`fragment -> purpose -> behavior -> pattern ->
campaign -> phase`) with an "Ask Blanc" chat. `web/serialize.py serialize_corpus(name)`
ships, in one payload per corpus, BOTH the **generic engine output** (`corpus` stats,
`messages`, `findings`, `patterns`, `campaigns`, plain narration) and the **curated
Blanc translations** (`narration.blanc`, `composition_narration.blanc`). `serialize.py`
imports `BlancNarrator` directly, so the generic serialization cannot stand alone.

The original redesign workstream — "separate generic engine UI from curated
lecture-demo (Blanc) translations" — names Blanc a *translation/presentation layer*
over generic engine facts. This phase makes that separation real: the generic engine
view is self-contained and reusable; the Blanc lecture is an optional curated layer
on top.

**Thread-locality finding (measured against the real `load_analysis` pipeline,
2026-06-30):** the other half of the original "thread-local omission/pattern"
workstream needs **no behavior change** — but the accurate invariant is narrower than
"every finding is single-thread." L2 omission already gates on `within_thread` (only
within-thread gaps become signals). For elevation, `run_engine` groups signals by
**seq overlap**, and each seq belongs to exactly one thread, so the **within-thread-only
layers (L1 pattern, L2 omission, L5 register)** can never assemble a finding across
threads by themselves. A finding *may* still legitimately span threads — but only via
a **bridging layer** that by its nature references another context: **L3** (a claim
contradicted by a record/message elsewhere), **L4** (a token converging across
domains/threads), or **L6** (cross-channel). The flagship **contractor** demo finding
is exactly this: an L2 omission in thread T1 + an L3 contradiction in T2 (tied back to
T1 by record R1) + L4 domain convergence — a correct, intended elevated finding that
spans threads. So the property to lock is: *within-thread-only layers {L1,L2,L5} never
span threads; bridging layers {L3,L4,L6} may.* This phase locks that with a
characterization test (verified: 0 violations) rather than changing behavior.

(An earlier draft of this spec claimed "no elevated cross-thread finding exists" and
treated L3 as within-thread — both were wrong: that measurement used a bare
`run_engine` without records/included_seqs, so L2/L3 did not fire as they do in the
real analysis. Corrected here.)

## Component 1 — thread-locality invariant lock (no behavior change)

A characterization test (`tests/test_thread_locality.py`) over the real demo corpora
(via `web.serialize.load_analysis`, which enables records + included_seqs so L2/L3
fire as in production) that locks the accurate invariant:

- **Within-thread-only layers never span threads:** no L1/L2/L5 signal's seqs
  (anchor + support) cross more than one thread.
- **Cross-thread findings require a bridging layer:** any finding whose seqs span
  more than one thread contains at least one of {L3, L4, L6}. (And at least one
  cross-thread finding exists — the contractor finding — so the assertion is live.)

No engine code changes. Verified: 0 violations across the demo corpora. If a future
change lets a within-thread-only layer assemble across threads, this test fails. If
the property is found not to hold, that is a real finding — surface it; do not weaken
the test or edit the engine.

## Component 2 — module boundary (the architectural core)

- **New `web/curated.py`** — owns all Blanc/lecture serialization. `serialize_curated(name)
  -> dict` returns the curated section: `narration_blanc` (`BlancNarrator(messages).narrate(result)`),
  `composition_blanc` (`narrate_composition(..., voice="blanc")`), and any
  lecture/slide metadata the lecture UI needs. This is the **only** web module that
  imports `BlancNarrator` / the Blanc persona.
- **`web/serialize.py`** — `serialize_engine(name) -> dict` returns the **generic core
  only**: `corpus` stats, `messages`, `findings` (layers, confidence, seqs, evidence,
  provenance), `patterns`, `campaigns`, and the **plain** narration (`TemplateNarrator`,
  already generic — `narration_plain`, `composition_plain`). After this change
  `web/serialize.py` imports **no** `BlancNarrator`. The existing `serialize_dynamics`
  / scorecard stays in `serialize.py` (it is generic eval output, not Blanc).
- **`web/build.py`** — writes one JSON per corpus shaped as
  `{ ...serialize_engine(name), "curated": serialize_curated(name) }`: a generic core
  plus an optional top-level `curated` section. One drift-gated artifact; the generic
  view ignores `curated`, the lecture uses both.

**Behavior preservation:** the generic core's keys/values are identical to today's
payload minus the Blanc fields; the Blanc fields move under `curated` (possibly
renamed for clarity, e.g. `narration.blanc` -> `curated.narration_blanc`). The
demo-data-drift gate enforces the rebuilt `web/site/data/`; the only intended diff is
this reorganization.

## Component 3 — the two pages

- **`web/site/index.html` + `app.js`** — the **unchanged front door**: the curated
  Blanc lecture slideshow, "Ask Blanc" chat included. Updated only as needed to read
  Blanc fields from their new `curated` location (no visual/UX change).
- **`web/site/engine.html` + `engine.js` (new)** — the **plain generic engine view**:
  a corpus picker, the message list, and the findings rendered with their layers,
  confidence (elevated/low), seqs, and evidence, plus the **plain** narration. No
  Blanc voice, no slideshow, no chat. Loads only the generic core of the per-corpus
  JSON (ignores `curated`). Corpus-agnostic and read-only.
- A small reciprocal link between the two pages ("plain engine view" ⇄ "Blanc
  lecture").

## Testing

- **Invariant lock** (Component 1) as above.
- **Generic core is Blanc-free:** a test asserting `serialize_engine(name)` contains
  the generic keys and **no** `blanc` field, and that importing/using it does not
  require `BlancNarrator` (e.g. the generic core for a corpus equals today's payload
  with the Blanc fields removed).
- **Curated section:** `serialize_curated(name)` returns the Blanc narration +
  composition; `build` composes them under `curated`; the combined file round-trips.
- **Web-contract tests updated** for the new payload shape (`curated` section), and a
  contract test for `engine.html` (the plain view renders findings + messages +
  plain narration and contains no Blanc/lecture markup).
- **Drift:** `web/site/data/` rebuilt so `python -m web.build && git diff --exit-code
  web/site/data/` is clean.
- All gates stay green: `ruff`, `mypy`, coverage ≥ 80%, tests ×2, demo-data-drift,
  Pages test-gated, on Python 3.10–3.12.

## Build decomposition (Subagent-Driven Development)

Each task lands via branch → PR → CI → squash-merge; final whole-branch review on the
most capable model before close-out.

- **T1 — thread-locality invariant lock.** Add the characterization test; no engine
  code change. (Independent of the web work.)
- **T2 — serialization split.** Add `web/curated.py` (`serialize_curated`); make
  `serialize.py serialize_engine` Blanc-free; `build` composes the `curated` section;
  update `test_web_serialize` / `test_web_build`; rebuild `web/site/data/`. Update
  `app.js` to read Blanc from `curated`.
- **T3 — plain engine page.** Add `web/site/engine.html` + `engine.js` (generic view),
  the reciprocal cross-link, and a UI-contract test for the plain page.

T2 precedes T3 (the page consumes the split payload). T1 is independent and may run
first or in parallel-authored isolation.

## Exit criteria

- `web/serialize.py` `serialize_engine` is the generic core and imports no
  `BlancNarrator`; `web/curated.py` owns the Blanc/lecture serialization; `build`
  emits one per-corpus JSON with a generic core + optional `curated` section.
- `web/site/engine.html` renders a plain, corpus-agnostic, read-only engine view
  (messages + findings with layers/confidence/evidence + plain narration), no Blanc,
  no chat; `index.html` Blanc lecture unchanged in behavior; the two pages cross-link.
- The thread-locality invariant is locked by a characterization test; no engine
  behavior changed.
- Generic serialized values byte-identical to before (Blanc moved under `curated`);
  `web/site/data/` rebuilt; drift gate clean.
- `ruff` / `mypy` / coverage (≥80) / tests ×2 / drift green on 3.10–3.12; Pages
  test-gated.

## Decisions log (brainstorming, 2026-06-30)

- **Separation goal = architectural boundary + a plain generic view (both).** The
  generic serialization/render path must not depend on Blanc; expose a standalone
  plain engine view distinct from the curated lecture.
- **Split = separate module + sectioned payload.** `web/curated.py` for Blanc; one
  per-corpus JSON with a generic core + optional `curated` section (one drift-gated
  artifact, clean import boundary).
- **Exposure = two pages, lecture stays the front door.** `index.html` remains the
  Blanc lecture; new `engine.html` is the plain generic view; small cross-link. No
  front-door flip.
- **Plain page = read-only generic forensic view, no chat.**
- **Thread-locality = already satisfied; lock with a test, no behavior change.**
  Measured: no elevated cross-thread finding exists; only exempt L4 spans. The
  engine-half of the original workstream collapses to a characterization test, folded
  in as T1 rather than a separate spec.

## Non-goals (Phase 4 — YAGNI)

- No change to engine findings, layers, elevation, the coercion machine, the eval
  tiers, or any corpus (the invariant lock is a test only; no thread-locality
  behavior change).
- No chat on the plain engine page; no new narration voices; no restyle of the Blanc
  lecture; no front-door flip.
- No new corpora; no metric changes.
