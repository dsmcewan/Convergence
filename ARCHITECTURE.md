# Architecture

A contributor-facing map of how data flows and where to extend. For the *why*
(design principles), see `ENGINEERING.md`; for the layer catalog, see `README.md`.

## Data flow

```
corpus (data/*.json  |  an SQLite export)
   │  corpus.py: load_corpus / load_sqlite_corpus  ->  list[Message]
   ▼
engine.py: run_engine(messages)               # L1–L6 detectors -> Signals
   │                                          # group; elevate only on cross-layer corroboration
   ▼
EngineResult(findings, all_signals, corpus_size)
   ├─ composition.py: find_patterns (L7) / find_campaigns (L8)   # structure above findings
   ├─ narration.py: TemplateNarrator / BlancNarrator             # deterministic prose (verdict-immune)
   ├─ conversation.py: Conversation(persona=…)                   # optional LLM; explains, never moves a verdict
   └─ evaluation.py: evaluate_dynamics / documentary_precision   # scored eval (synthetic + real-data)
   ▼
demo.py (CLI)   |   web/ (serialize.py -> JSON -> server.py + site/)
```

The engine core (`convergence/`, minus `adapters/`) is **stdlib-only and
deterministic**: same input → byte-identical output. The LLM adapters are the
only network egress and are strictly optional (each degrades to the deterministic
narrator). See `SECURITY.md` for trust boundaries.

## The invariant that governs everything

**A model can never move a verdict.** Verdicts are computed by the layers before
any prompt is built; narration and conversation are presentation-only. Any change
that lets a model, a label, or a display ranking alter which findings are elevated
is a bug. The test suite enforces this — every layer/composition/eval change runs
the full deterministic suite as a guardrail.

## Extension points

- **Add a detection layer.** Write `layers/<name>.py` returning its findings;
  reduce them to `Signal`s in `engine.py::_collect_signals`. Keep it deterministic
  and stdlib-only. Add a `tests/test_<name>.py`.
- **Add a corpus.** Drop a JSON file in `data/` (same `Message` shape) — the engine
  runs unchanged. For a new DB shape, add a loader in `corpus.py` beside
  `load_sqlite_corpus`.
- **Add an LLM backend.** Add `adapters/<name>_llm.py` exposing a
  `make_<name>_complete() -> (prompt -> str)`; wire it into `demo.py` /
  `web/server.py::make_complete`. The core never imports adapters.
- **Add a composition rule.** Extend `composition.py` (templates/recurrence for
  L7, campaign attribution for L8) — it only *reads* the `EngineResult`.
- **Add an eval.** Labeled data → extend `evaluation.py::evaluate`; real data with
  no truth → follow `documentary_precision` (precision-only against independent
  anchors; never score against pipeline triage labels).

## Web layer

`web/build.py` serializes each corpus's `EngineResult` to `web/site/data/*.json`
for static hosting; `web/server.py` serves the site and adds a `/api/chat`
endpoint (optional, gated by `CONVERGENCE_API_KEY`). The site (`web/site/`) is
vanilla HTML/CSS/JS — no build step. Bind/auth config is environment-driven
(`CONVERGENCE_HOST` / `CONVERGENCE_PORT` / `CONVERGENCE_API_KEY`).
