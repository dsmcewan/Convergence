# Phase 0 — Foundation & Hardening (convergence redesign)

**Goal:** Establish a dev-tooling + CI safety net (lint, typing, honest coverage,
test-gated Pages) and harden the web demo's runtime boundary (chat auth,
request/response validation, resource limits) — all without touching the engine,
so the subsequent provenance redesign (Phases 1–4) lands on solid ground.

**Status:** design approved 2026-06-30. This is sub-project 0 of a five-phase
redesign program. Phases 1–4 (Signal provenance → provenance-aware engine →
adversarial validation → UI/demo separation) follow, each its own spec → plan →
build. Build method: **Subagent-Driven Development** (branch → PR → CI →
squash-merge per task, review between, final whole-branch review).

**Scope boundary:** Phase 0 changes only dev config, CI workflows, `web/`, and
tests. It does **not** modify `convergence/` engine logic, the `Signal` model, the
layers, `evaluation.py`, or the corpora. (Lint/type fixes may touch engine files
cosmetically — import order, an unused variable, a type annotation — but never
behavior.)

---

## Context

The repo (`dsmcewan/Convergence`) ships green CI (tests ×2 across Python 3.10–3.12),
a coverage gate, a Pages demo, and badges. But: there is no linter or type
checker; the coverage floor is trustworthy only if the `# pragma: no cover` marks
are honest; Pages deploys on every push regardless of whether tests pass; and the
`/api/chat` boundary has a timing-unsafe key compare, loose payload coercion, no
body-size cap, and no LLM-call timeout. Phase 0 closes these foundational gaps.

## Track A — Tooling & CI (#8)

### A1. Lint — `ruff`
- Add `ruff` to `[project.optional-dependencies].dev`.
- `[tool.ruff]` in `pyproject.toml`: `line-length = 100` (matches the codebase),
  `target-version = "py310"`; `[tool.ruff.lint]` `select = ["E", "W", "F", "I",
  "B", "UP"]` (pycodestyle, pyflakes, isort, bugbear, pyupgrade). Add per-file
  ignores only where justified (e.g. `__init__.py` re-export `F401`).
- Fix all violations the selected rules surface. Behavior-preserving only.
- CI step (in the `tests` workflow): `ruff check .`.

### A2. Typing — `mypy` (pragmatic, ratchet later)
- Add `mypy` to dev deps.
- `[tool.mypy]`: `python_version = "3.10"`, `warn_unused_ignores = true`,
  `no_implicit_optional = true`, `check_untyped_defs = true`,
  `warn_redundant_casts = true`, `warn_unused_configs = true`. **Not** strict:
  `disallow_untyped_defs` stays off for now. Third-party SDKs without stubs
  (`openai`, `anthropic`, `google.genai`) get `ignore_missing_imports` via
  `[[tool.mypy.overrides]]`.
- Fix the type errors this surfaces (expected mostly in `web/`, `narration.py`,
  and the adapters). Annotations/`cast`/guards only — no behavior change.
- A commented `# ratchet:` block in the config lists the stricter flags to enable
  in a later phase (`disallow_untyped_defs`, `disallow_any_generics`,
  `warn_return_any`).
- CI step: `mypy convergence web`.

### A3. Real coverage enforcement
- **Audit `# pragma: no cover`:** review every occurrence. Keep it only on
  genuinely-untestable seams — the network/CLI subprocess bodies in
  `convergence/adapters/*` (the `complete()` closures, CLI `spawn`/`pexpect`
  paths). Remove it anywhere it hides testable branch logic, and add the tests
  that the removal exposes.
- Add `[tool.coverage.run]` `source = ["convergence", "web"]` and
  `[tool.coverage.report]` with `exclude_also` for the standard untestable lines
  (`if __name__`, `raise NotImplementedError`, `if TYPE_CHECKING:`) so the config
  is declarative rather than living only in the CI flags.
- Set the floor to an honest number that holds after the audit (target ≥ 80%, and
  ≥ the post-audit measured value). The existing CI `--cov-fail-under` step is the
  required gate; align its number to the config.

### A4. Test-gated Pages
- Change `.github/workflows/pages.yml` trigger from `on: push` to
  `on: workflow_run: { workflows: ["tests"], types: [completed], branches: [main] }`,
  plus `workflow_dispatch`.
- Guard the deploy job with `if: ${{ github.event.workflow_run.conclusion ==
  'success' || github.event_name == 'workflow_dispatch' }}` so Pages publishes
  only after the `tests` workflow passes on `main` (a red build never deploys).
- The job still checks out `main` and uploads `web/site/`; behavior is otherwise
  unchanged.

## Track B — Web hardening (#7)

### B1. Chat auth repair
- In `web/server.py`, replace `headers.get("X-API-Key") == required` with a
  constant-time compare: `hmac.compare_digest(provided, required)` where
  `provided = headers.get("X-API-Key") or ""`. Both args coerced to `str`.
- Keep the existing model: open when `CONVERGENCE_API_KEY` is unset (localhost
  dev), required when set; the fail-closed non-loopback bind guard in `main()`
  stays.

### B2. Structured request/response validation
- Add a `validate_chat_request(payload) -> tuple[corpus, question, voice, model]`
  (or a small dataclass) that enforces, before any dispatch:
  - `corpus`: a string in `corpus_names()` → else 400.
  - `question`: a non-empty string, `len(question) <= MAX_QUESTION_LEN` (4000) →
    else 400.
  - `voice`: in `{"blanc", "plain"}` → else 400.
  - `model`: in the allowed set `{"claude", "openai", "grok", "gemini", "agy"}` →
    else 400.
  Each failure returns `400` with a clear `{"error": "..."}` naming the bad field.
  Replaces the loose `str(payload.get(...))` coercion in `do_POST`.
- Defensive response shape: `/api/chat` returns exactly `{"answer": <str>}`; a
  small assertion (or typed construction) guarantees the emitted object matches
  the documented shape before `_json`.

### B3. Resource limits
- **Body-size cap:** parse `content-length`; if missing/non-integer →
  400, if `> MAX_BODY_BYTES` (16384) → `413` without reading the body; otherwise
  read exactly `length` bytes (never more).
- **LLM-call timeout:** run `complete_fn(...)`/`answer_chat(...)` via a
  `concurrent.futures.ThreadPoolExecutor` with `future.result(timeout=LLM_TIMEOUT_S)`
  (30); on `TimeoutError` return `504` with a clear message. (The worker thread may
  outlive the request — acceptable for the demo; documented.)
- Constants (`MAX_BODY_BYTES`, `MAX_QUESTION_LEN`, `LLM_TIMEOUT_S`) defined at
  module top, overridable via env where it makes sense.

## Testing

All gates run on the existing `tests` workflow (ubuntu, Python 3.10–3.12):

- **A1/A2:** CI is green only when `ruff check .` and `mypy convergence web` pass.
- **A3:** coverage audit lands new unit tests for any logic un-hidden by removing a
  `pragma`; the `--cov-fail-under` gate holds at the honest floor.
- **A4:** verified operationally — a push with green tests deploys Pages; the
  workflow_run guard is inspected in review (CI can't easily self-test "a red build
  doesn't deploy", so this is a review-confirmed change + a manual `workflow_dispatch`
  smoke).
- **B1–B3 (unit tests, no network, injected `complete`):**
  - auth: correct key → allowed; wrong key → 401; missing key header when required
    → 401; no key configured → open.
  - validation: unknown corpus → 400; empty question → 400; over-long question →
    400; bad voice → 400; bad model → 400; a well-formed request → 200 with
    `{"answer": ...}`.
  - limits: `content-length` > cap → 413 (body not read); missing/invalid
    content-length → 400; a `complete` stub that sleeps past the timeout → 504.
  These extend `tests/test_web_server.py`.

## Exit criteria

- `pytest` (×2, determinism) green on 3.10–3.12; `ruff check .` clean; `mypy
  convergence web` clean; coverage ≥ the honest floor — all required in CI.
- `pages.yml` deploys only after a successful `tests` run on `main`.
- `web/server.py`: constant-time auth, schema-validated `/api/chat` requests,
  body-size cap, and an LLM-call timeout — each covered by a test.
- No engine/`Signal`/layer/`evaluation`/corpus behavior changed.

## Decisions log (brainstorming, 2026-06-30)

- **Decomposition:** the 8 requested workstreams split into 5 sequenced
  sub-projects; Phase 0 = tooling (#8) + web hardening (#7), the engine-independent
  foundation, built first as the safety net for the redesign.
- **Build method:** Subagent-Driven Development for every phase.
- **Typing:** mypy pragmatic-then-ratchet (sensible checks now, strict flags
  deferred) — lands the gate without a large upfront type-debt cleanup.
- **Coverage:** "real" = audit the `# pragma: no cover` marks so the number isn't
  inflated by hidden code, with a meaningful required floor (not a 90–95% push,
  not per-module minimums).
- **Web hardening:** core hardening only — constant-time compare, request
  validation, body cap, LLM timeout. Rate-limiting / max-concurrency and an
  always-require-a-key auth model are deferred.
- **"Structured-output validation"** read as schema validation at the API boundary
  (validate inbound requests, assert the outbound shape), confirmed at design
  approval.

## Non-goals (Phase 0 — YAGNI)

- No rate-limiting, max-concurrency bound, or auth-model change.
- No strict-mypy cleanup; no per-module coverage minimums; no branch coverage.
- No engine, `Signal`, layer, evaluation-metric, or corpus changes (those are
  Phases 1–4).
- No new web features; hardening only.
