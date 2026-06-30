# Phase 4 — Engine UI / Blanc lecture separation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Separate the generic, corpus-agnostic engine output from the curated Benoit-Blanc lecture-demo — a real import boundary (`web/serialize.py` generic core has no Blanc dependency) plus a standalone plain `engine.html` view — and lock the already-satisfied thread-locality property of `run_engine` with a characterization test.

**Architecture:** `web/serialize.py` keeps the generic core (`serialize_engine`, Blanc-free); a new `web/curated.py` owns all Blanc/lecture serialization and composes the full demo payload (`serialize_corpus = {**serialize_engine, "curated": serialize_curated}`); `web/build.py`/`web/server.py` consume the composed payload; the lecture `app.js` re-hydrates the curated section onto the shapes it already expects; a new `engine.html`/`engine.js` renders the generic core only.

**Tech Stack:** Python 3.10–3.12, stdlib only; pytest; ruff; mypy. Vanilla JS/HTML/CSS (no framework, no build step for the site). No new dependencies.

## Global Constraints

- **Behavior preservation:** the generic serialized values (corpus stats, messages, findings, patterns, campaigns, plain narration) are byte-identical to today. The only intended change to `web/site/data/*.json` is that the Blanc fields move under a top-level `curated` section. The demo-data-drift gate (`python -m web.build && git diff --exit-code web/site/data/`) is the proof.
- **Import boundary:** after this phase, `web/serialize.py` imports **no** `BlancNarrator` and nothing from `web/curated.py`. `web/curated.py` is the ONLY web module that imports `BlancNarrator` / the Blanc persona.
- **No engine change:** do NOT modify `convergence/` at all. The thread-locality work is a test only; if the invariant does not hold, surface it — do not edit the engine or a corpus.
- **The lecture (`index.html` + `app.js`) keeps its behavior and appearance.** The existing `test_web_ui_contract.py` lecture assertions (`'voice: "blanc"' in app.js`, `data-voice not in index.html`, slide-stage, chat-lock, etc.) must stay green.
- **The plain `engine.html` is read-only and generic:** corpus picker + messages + findings (layers, confidence, seqs, evidence) + plain narration. No Blanc voice, no slideshow, no chat.
- **Curated payload shape** (top-level `curated` key): `{"narration_blanc": str, "composition_blanc": str, "finding_blanc": [str, ...]}` where `finding_blanc[i]` aligns to `findings[i]`.
- **Gates that must stay green on Python 3.10/3.11/3.12:** `ruff`, `mypy`, coverage ≥ 80% (`--cov-fail-under=80`), `pytest` ×2, demo-data-drift, Pages test-gated.
- **SDD mechanics:** controller pre-creates each branch; implementer commits locally with explicit `git add <paths>` (never `git add -A`); push → PR → CI → squash-merge per task. `.superpowers/` is gitignored. T2 precedes T3; T1 is independent.

---

## File Structure

- `tests/test_thread_locality.py` (new, T1) — characterization test locking the thread-locality invariant. No engine change.
- `web/serialize.py` (modify, T2) — rename `serialize_corpus` → `serialize_engine` (generic core), drop Blanc from it and from `_finding`; remove `_finding_blanc_narration` and the `BlancNarrator` import. Keep `serialize_dynamics`, `serialize_index`, `load_analysis`, helpers.
- `web/curated.py` (new, T2) — `serialize_curated(name)` (Blanc section) and `serialize_corpus(name)` (composed full payload). The only Blanc importer.
- `web/build.py` (modify, T2) — import `serialize_corpus` from `web.curated`.
- `web/server.py` (modify, T2) — update its `serialize_corpus` import to `web.curated` (if it imports it).
- `web/site/app.js` (modify, T2) — re-hydrate `curated` onto `state.corpus` after load (one block at the corpus-load site).
- `tests/test_web_serialize.py`, `tests/test_web_build.py` (modify, T2) — update for the `curated` shape and the `web.curated` import.
- `web/site/data/*.json` (rebuilt, T2).
- `web/site/engine.html`, `web/site/engine.js` (new, T3) — plain generic view; a cross-link added to `index.html`.
- `tests/test_engine_page_contract.py` (new, T3) — contract test for the plain page.

---

## Task 1: Thread-locality invariant lock

**Files:**
- Create: `tests/test_thread_locality.py`

**Interfaces:**
- Consumes: `web.serialize.corpus_names() -> list[str]`, `web.serialize.load_analysis(name) -> (messages, EngineResult, meta)`. (These exist today and are generic.)
- Produces: nothing; a test only.

- [ ] **Step 1: Write the characterization test**

Create `tests/test_thread_locality.py`:

```python
"""Thread-locality is an architectural invariant of run_engine's elevation, not a
behavior added here. Elevation groups signals by SEQ OVERLAP, and each seq belongs to
exactly one thread, so within-thread substantive layers (L1/L2/L3/L5) can only
converge inside one thread. The only layers that may span threads are the bridging
layers L4 (domain convergence) and L6 (cross-channel) - and a single such layer never
elevates on its own. This test locks that property so a future change cannot silently
introduce cross-thread elevation. (Measured 2026-06-30: no elevated cross-thread
finding exists across the demo corpora.)
"""
from web.serialize import corpus_names, load_analysis

_SPANNING_LAYERS = {"L4", "L6"}


def _threads_of(finding, messages):
    by_seq = {m.seq: m.thread for m in messages}
    return {by_seq[s] for s in finding.seqs if s in by_seq}


def test_every_elevated_finding_is_single_thread():
    saw_elevated = False
    for name in corpus_names():
        messages, result, _ = load_analysis(name)
        for f in result.findings:
            if f.confidence == "elevated":
                saw_elevated = True
                threads = _threads_of(f, messages)
                assert len(threads) == 1, (
                    f"{name}: elevated finding spans threads {sorted(threads)} "
                    f"(seqs {list(f.seqs)}, layers {list(f.layers)})"
                )
    assert saw_elevated, "the elevation bar must be reachable within a thread"


def test_multithread_findings_are_only_bridging_layers():
    for name in corpus_names():
        messages, result, _ = load_analysis(name)
        for f in result.findings:
            threads = _threads_of(f, messages)
            if len(threads) > 1:
                assert set(f.layers) <= _SPANNING_LAYERS, (
                    f"{name}: finding across threads {sorted(threads)} has "
                    f"non-bridging layers {set(f.layers) - _SPANNING_LAYERS}"
                )
```

- [ ] **Step 2: Run the test to verify it passes (characterization, not TDD-red)**

Run: `python -m pytest tests/test_thread_locality.py -v`
Expected: PASS (both tests). This locks an existing property; it should pass against current `main`. If it FAILS, do NOT change the engine or the test — surface it: the invariant does not hold and the design assumption is wrong.

- [ ] **Step 3: Commit**

```bash
git add tests/test_thread_locality.py
git commit -m "test: lock the thread-locality invariant of run_engine elevation (Phase 4 T1)"
```

---

## Task 2: Serialization split (generic core + curated module)

**Files:**
- Modify: `web/serialize.py`
- Create: `web/curated.py`
- Modify: `web/build.py`, `web/server.py` (imports), `web/site/app.js`
- Test: `tests/test_web_serialize.py`, `tests/test_web_build.py`
- Rebuild: `web/site/data/*.json`

**Interfaces:**
- Produces: `web.serialize.serialize_engine(name) -> dict` (generic core, Blanc-free); `web.curated.serialize_curated(name) -> dict` (curated section); `web.curated.serialize_corpus(name) -> dict` (composed: `{**serialize_engine(name), "curated": serialize_curated(name)}`).
- Consumes (unchanged): `load_analysis`, `find_patterns`, `find_campaigns`, `TemplateNarrator`, `BlancNarrator`, `narrate_composition`.

- [ ] **Step 1: Update the failing serialize tests (define the new contract)**

Edit `tests/test_web_serialize.py`. Change the import line:

```python
from web.serialize import DATA, serialize_dynamics
from web.curated import serialize_corpus
```

Replace `test_serialized_corpus_has_frontend_contract` with:

```python
def test_serialized_engine_core_is_blanc_free():
    from web.serialize import serialize_engine
    core = serialize_engine("coparenting")
    assert core["corpus"]["name"] == "coparenting"
    assert core["messages"]
    assert set(core["narration"]) == {"plain"}
    assert set(core["composition_narration"]) == {"plain"}
    assert "curated" not in core
    assert all("blanc" not in f.get("narration", {}) for f in core["findings"])
    assert all({"seqs", "confidence", "layers", "signals", "messages"} <= set(f) for f in core["findings"])  # noqa: E501


def test_composed_corpus_has_curated_section():
    payload = serialize_corpus("coparenting")
    # generic core present
    assert set(payload["narration"]) == {"plain"}
    # curated section present and aligned
    cur = payload["curated"]
    assert isinstance(cur["narration_blanc"], str) and cur["narration_blanc"]
    assert isinstance(cur["composition_blanc"], str)
    assert len(cur["finding_blanc"]) == len(payload["findings"])


def test_serialize_module_has_no_blanc_dependency():
    import web.serialize as s
    src = __import__("inspect").getsource(s)
    assert "BlancNarrator" not in src
    assert "import web.curated" not in src and "from web.curated" not in src
```

Keep `test_serialized_elevated_seqs_match_engine` and `test_serialized_dynamics_scorecard_is_perfect_for_demo_corpora` and `test_signal_json_includes_provenance_fields`, but update the latter two's import: they use `serialize_corpus` (now from `web.curated`) and `serialize_dynamics` (still `web.serialize`). Ensure the file's imports cover both.

- [ ] **Step 2: Run to verify they fail**

Run: `python -m pytest tests/test_web_serialize.py -v`
Expected: FAIL — `serialize_engine` and `web.curated` do not exist yet.

- [ ] **Step 3: Make `serialize_engine` the generic, Blanc-free core in `web/serialize.py`**

In `web/serialize.py`: change the import line 18 from

```python
from convergence.narration import BlancNarrator, TemplateNarrator, narrate_composition
```

to

```python
from convergence.narration import TemplateNarrator, narrate_composition
```

Rename `serialize_corpus` to `serialize_engine` and drop the Blanc fields:

```python
def serialize_engine(name: str) -> dict[str, Any]:
    messages, result, meta = load_analysis(name)
    patterns = find_patterns(result)
    campaigns = find_campaigns(result, messages)

    return {
        "corpus": {
            **meta,
            "message_count": len(messages),
            "finding_count": len(result.findings),
            "elevated_count": sum(1 for f in result.findings if f.confidence == "elevated"),
            "low_count": sum(1 for f in result.findings if f.confidence == "low"),
        },
        "messages": [_message(m) for m in messages],
        "findings": [_finding(f, messages) for f in result.findings],
        "patterns": [_pattern(p) for p in patterns],
        "campaigns": [_campaign(c) for c in campaigns],
        "narration": {
            "plain": TemplateNarrator().narrate(result),
        },
        "composition_narration": {
            "plain": narrate_composition(patterns, campaigns, voice="plain"),
        },
    }
```

Make `_finding` plain-only (drop the `blanc` key):

```python
    return {
        "seqs": list(f.seqs),
        "confidence": f.confidence,
        "layers": list(f.layers),
        "summary": f.summary,
        "signals": [_signal(s) for s in f.signals],
        "messages": [_message(m) for m in cited],
        "narration": {
            "plain": _finding_narration(f),
        },
    }
```

Delete the `_finding_blanc_narration` function entirely from `web/serialize.py` (it moves to `web/curated.py`). `_finding_narration` stays.

- [ ] **Step 4: Create `web/curated.py`**

```python
"""Curated Benoit-Blanc lecture layer over the generic engine output.

This is the ONLY web module that imports the Blanc narrator. The generic engine
serialization (web/serialize.py) does not depend on this module; the lecture demo
composes the generic core with the curated section here.
"""
from __future__ import annotations

from typing import Any

from convergence.composition import find_campaigns, find_patterns
from convergence.engine import Finding
from convergence.narration import BlancNarrator, narrate_composition
from web.serialize import load_analysis, serialize_engine


def _finding_blanc_narration(f: Finding) -> str:
    if f.confidence == "elevated":
        return (
            f"Here the threads meet: seqs {list(f.seqs)}, layers {', '.join(f.layers)}. "
            "Not a hunch, but corroboration."
        )
    return (
        f"Seqs {list(f.seqs)} remain low. Suggestive, perhaps, but the method refuses "
        "to elevate a lone thread."
    )


def serialize_curated(name: str) -> dict[str, Any]:
    messages, result, _ = load_analysis(name)
    patterns = find_patterns(result)
    campaigns = find_campaigns(result, messages)
    return {
        "narration_blanc": BlancNarrator(messages).narrate(result),
        "composition_blanc": narrate_composition(patterns, campaigns, voice="blanc"),
        "finding_blanc": [_finding_blanc_narration(f) for f in result.findings],
    }


def serialize_corpus(name: str) -> dict[str, Any]:
    """The full demo payload: generic engine core + the curated Blanc section."""
    return {**serialize_engine(name), "curated": serialize_curated(name)}
```

- [ ] **Step 5: Update `web/build.py` and `web/server.py` imports**

In `web/build.py`, change the import from `web.serialize`:

```python
from web.serialize import corpus_names, serialize_dynamics, serialize_index
from web.curated import serialize_corpus
```

In `web/server.py`, find its `serialize_corpus` import (if present) and repoint it to `web.curated` (leave `serialize_dynamics`/`serialize_index` on `web.serialize`). Run `grep -n "serialize_corpus" web/server.py` to confirm; if it imports it, change the source module to `web.curated`.

- [ ] **Step 6: Re-hydrate the curated section in `web/site/app.js`**

In `web/site/app.js`, immediately after the corpus payload is loaded in `selectCorpus` (the line `state.corpus = await loadJson(url);`, ~line 104), insert:

```javascript
  if (state.corpus && state.corpus.curated) {
    const cur = state.corpus.curated;
    state.corpus.narration = state.corpus.narration || {};
    state.corpus.narration.blanc = cur.narration_blanc;
    state.corpus.composition_narration = state.corpus.composition_narration || {};
    state.corpus.composition_narration.blanc = cur.composition_blanc;
    (state.corpus.findings || []).forEach((f, i) => {
      f.narration = f.narration || {};
      f.narration.blanc = (cur.finding_blanc || [])[i];
    });
  }
```

This restores the `narration.blanc` / `composition_narration.blanc` / per-finding `narration.blanc` shapes the rest of `app.js` already reads, so no other lecture code changes.

- [ ] **Step 7: Run the serialize/build tests + rebuild data**

Run: `python -m pytest tests/test_web_serialize.py tests/test_web_build.py -v && python -m web.build`
Expected: the serialize/build tests pass. `python -m web.build` rewrites `web/site/data/*.json` with the `curated` section.

- [ ] **Step 8: Run the full gate suite**

Run: `python -m pytest -q && python -m ruff check . && python -m mypy convergence web && git add web/site/data && python -m web.build && git diff --exit-code web/site/data/`
Expected: all green. The drift check should be clean after the rebuild in Step 7 is staged (the only change to `web/site/data/` is the Blanc fields relocating under `curated`). The lecture contract tests in `tests/test_web_ui_contract.py` must stay green (the hydration keeps `app.js`'s reads working).

- [ ] **Step 9: Commit**

```bash
git add web/serialize.py web/curated.py web/build.py web/server.py web/site/app.js tests/test_web_serialize.py tests/test_web_build.py web/site/data
git commit -m "refactor: split generic engine serialization from curated Blanc layer (Phase 4 T2)"
```

---

## Task 3: Plain generic engine page

**Files:**
- Create: `web/site/engine.html`, `web/site/engine.js`
- Modify: `web/site/index.html` (add a cross-link)
- Test: `tests/test_engine_page_contract.py`

**Interfaces:**
- Consumes: the built `web/site/data/index.json` (corpus list) and `web/site/data/<corpus>.json` (generic core; ignores `curated`).
- Produces: a standalone read-only page; no new Python symbols.

- [ ] **Step 1: Write the contract test**

Create `tests/test_engine_page_contract.py`:

```python
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(p: str) -> str:
    return (ROOT / p).read_text(encoding="utf-8")


def test_engine_page_exists_and_is_plain():
    html = read("web/site/engine.html")
    js = read("web/site/engine.js")
    # plain, generic view: a corpus picker, a findings container, loads engine.js
    assert 'id="corpus-select"' in html
    assert 'id="findings"' in html
    assert "engine.js" in html
    # it is NOT the Blanc lecture: no slideshow, no Blanc voice, no chat
    assert "slide-stage" not in html
    assert "Blanc" not in html and "blanc" not in js
    assert "chat-form" not in html
    # engine.js renders the generic core fields
    assert "data/index.json" in js
    assert "findings" in js and "confidence" in js and "layers" in js


def test_lecture_links_to_engine_page():
    assert "engine.html" in read("web/site/index.html")


def test_engine_js_ignores_curated_section():
    js = read("web/site/engine.js")
    assert "curated" not in js  # the plain view must not read the curated section
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_engine_page_contract.py -v`
Expected: FAIL — `engine.html` / `engine.js` do not exist.

- [ ] **Step 3: Create `web/site/engine.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>convergence — engine view</title>
  <link rel="stylesheet" href="style.css" />
</head>
<body class="engine-view">
  <header class="engine-topbar">
    <strong>convergence · engine view</strong>
    <a href="index.html">Blanc lecture →</a>
  </header>
  <main class="engine-main">
    <label for="corpus-select">Corpus</label>
    <select id="corpus-select" aria-label="corpus"></select>
    <section id="corpus-summary" class="engine-summary" aria-live="polite"></section>
    <h2>Findings</h2>
    <ol id="findings" class="engine-findings"></ol>
    <h2>Narration</h2>
    <pre id="narration" class="engine-narration"></pre>
  </main>
  <script src="engine.js"></script>
</body>
</html>
```

- [ ] **Step 4: Create `web/site/engine.js`**

```javascript
// Plain, read-only generic engine view. Loads the generic core of each corpus
// payload and renders findings with their layers, confidence, seqs, and evidence.
// It deliberately ignores the `curated` (Blanc lecture) section.
const $ = (id) => document.getElementById(id);

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

async function loadJson(url) {
  const r = await fetch(url, { cache: "no-store" });
  if (!r.ok) throw new Error(`failed to load ${url}`);
  return r.json();
}

function renderFindings(data) {
  const ol = $("findings");
  ol.innerHTML = "";
  for (const f of data.findings) {
    const li = document.createElement("li");
    li.className = `finding ${f.confidence}`;
    const sigs = f.signals
      .map((s) => `${s.layer} ${escapeHtml(s.kind)} — ${escapeHtml(s.detail)} (seq ${s.anchor}, ${escapeHtml(s.thread)})`)
      .join("<br>");
    li.innerHTML =
      `<div class="finding-head"><span class="badge">${f.confidence}</span>` +
      `<span class="layers">${f.layers.join(" · ")}</span>` +
      `<span class="seqs">seqs ${f.seqs.join(", ")}</span></div>` +
      `<p class="finding-summary">${escapeHtml(f.summary)}</p>` +
      `<div class="finding-signals">${sigs}</div>`;
    ol.appendChild(li);
  }
}

function renderCorpus(data) {
  const c = data.corpus;
  $("corpus-summary").textContent =
    `${c.label} · ${c.message_count} messages · ${c.finding_count} findings ` +
    `(${c.elevated_count} elevated, ${c.low_count} low)`;
  renderFindings(data);
  $("narration").textContent = data.narration.plain || "";
}

async function selectCorpus(name) {
  renderCorpus(await loadJson(`data/${name}.json`));
}

async function init() {
  const index = await loadJson("data/index.json");
  const select = $("corpus-select");
  for (const corpus of index.corpora) {
    const opt = document.createElement("option");
    opt.value = corpus.name;
    opt.textContent = corpus.label;
    select.appendChild(opt);
  }
  select.value = index.default_corpus;
  select.addEventListener("change", () => selectCorpus(select.value));
  await selectCorpus(index.default_corpus);
}

init();
```

- [ ] **Step 5: Add the cross-link in `web/site/index.html`**

Add a small link to the lecture's top bar so the two pages cross-link. In `web/site/index.html`, inside the `<header class="topbar">` block, add after the brand link:

```html
        <a class="engine-link" href="engine.html" aria-label="plain engine view">engine view →</a>
```

- [ ] **Step 6: Run the contract test + full gates**

Run: `python -m pytest tests/test_engine_page_contract.py -v && python -m pytest -q && python -m ruff check . && python -m mypy convergence web && python -m web.build && git diff --exit-code web/site/data/`
Expected: all green; no web-data drift (T3 adds static page files only — `engine.html`/`engine.js` are not under `web/site/data/`). The lecture contract tests stay green (only an additive link was added to `index.html`).

- [ ] **Step 7: Commit**

```bash
git add web/site/engine.html web/site/engine.js web/site/index.html tests/test_engine_page_contract.py
git commit -m "feat: plain generic engine view page, separate from the Blanc lecture (Phase 4 T3)"
```

---

## Notes for the controller

- **T1 is independent** (a test-only invariant lock); it can be the first branch off `main`. **T2 precedes T3** (the page consumes the split payload). Each task branches from the latest merged state.
- **The import boundary is the architectural deliverable:** after T2, `tests/test_web_serialize.py::test_serialize_module_has_no_blanc_dependency` proves `web/serialize.py` is Blanc-free. Do not let a later task re-introduce a Blanc import into `web/serialize.py`.
- **Drift discipline:** only T2 changes `web/site/data/`. Its sole intended diff is the Blanc fields relocating under `curated`. If the rebuild shows any change to a generic field (a finding seq, a plain narration string), STOP — behavior was not preserved; surface it.
- **Pages gating note:** the new `engine.html` is a static file served by GitHub Pages alongside `index.html`; no workflow change is needed (Pages publishes the whole `web/site/` tree). Confirm the Pages job is unaffected.
- After T3 merges, run the **final whole-branch review on the most capable model** over the Phase-4 span, with attention to: the Blanc-free import boundary actually holding, the generic serialized values being byte-identical (drift), the `engine.html` page reading only the generic core (no `curated`), the lecture's behavior unchanged, and a character-corruption scan of the new JS/HTML string literals.
```
