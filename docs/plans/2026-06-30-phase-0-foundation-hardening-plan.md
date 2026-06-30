# Phase 0 — Foundation & Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a dev-tooling + CI safety net (ruff, pragmatic mypy, honest coverage, test-gated Pages) and harden the web demo's `/api/chat` boundary (constant-time auth, request/response validation, body-size cap, LLM-call timeout) — without changing engine behavior.

**Architecture:** Track A is config + CI-workflow edits plus behavior-preserving lint/type fixes. Track B refactors `web/server.py` to delegate request handling to small, directly-testable helpers (`validate_chat_request`, `parse_content_length`, `call_with_timeout`, a `ChatError`) that `do_POST` orchestrates, matching the repo's existing function-level test style (no real socket).

**Tech Stack:** Python ≥3.10 (stdlib only at runtime), `ruff` + `mypy` + `pytest-cov` (dev-only), GitHub Actions, `hmac`/`concurrent.futures` (stdlib).

## Global Constraints

- **Engine-untouching:** only `pyproject.toml`, `.github/workflows/*`, `web/`, and `tests/` change. Lint/type fixes may touch `convergence/` files but must be **behavior-preserving** (import order, unused names, annotations, `cast`/guards) — never logic.
- **No new runtime dependencies.** `ruff`, `mypy`, `pytest-cov` go in `[project.optional-dependencies].dev` only. Runtime stays stdlib-only.
- **Python floor 3.10**; everything must pass on the CI matrix 3.10 / 3.11 / 3.12.
- **Tests are keyless/deterministic** — no network; inject a `complete` stub.
- **Each task lands via its own branch → PR → CI → squash-merge.** The controller pre-creates the branch; the implementer commits locally with explicit `git add` (never `-A`).
- **Constants (Track B):** `MAX_BODY_BYTES = 16384`, `MAX_QUESTION_LEN = 4000`, `LLM_TIMEOUT_S = 30`, `ALLOWED_VOICES = {"blanc", "plain"}`, `ALLOWED_MODELS = {"claude", "openai", "grok", "gemini", "agy"}`.
- **Task order:** A1 → A2 → A3 → A4 → B1 → B2 → B3 (lint/type gates land first so every later PR is checked by them).

## File Structure

- `pyproject.toml` — add `[tool.ruff]`, `[tool.mypy]`, `[tool.coverage.*]`; extend `dev` deps.
- `.github/workflows/ci.yml` — add `ruff check` + `mypy` steps; keep the coverage + drift gates.
- `.github/workflows/pages.yml` — switch to a `workflow_run` trigger gated on the `tests` workflow succeeding.
- `web/server.py` — constant-time auth + extracted request-handling helpers + a `do_POST` that orchestrates them.
- `tests/test_web_server.py` — extend with helper-level tests (validation, body cap, timeout).
- `convergence/**` — behavior-preserving lint/type fixes only; narrow one OpenAI adapter pragma.

---

### Task A1: Lint — ruff

**Files:**
- Modify: `pyproject.toml` (dev deps + `[tool.ruff]`)
- Modify: `.github/workflows/ci.yml` (add a `ruff check` step)
- Modify: any files ruff flags (behavior-preserving fixes)

**Interfaces:**
- Produces: a green `ruff check .` and a CI lint gate that every later PR must pass.

- [ ] **Step 1: Add ruff to dev deps.** In `pyproject.toml`, change the `dev` extra:

```toml
dev = ["pytest>=7", "pytest-cov>=4", "ruff>=0.6"]
```

- [ ] **Step 2: Add the ruff config.** Append to `pyproject.toml`:

```toml
[tool.ruff]
line-length = 100
target-version = "py310"

[tool.ruff.lint]
select = ["E", "W", "F", "I", "B", "UP"]
# E/W pycodestyle, F pyflakes, I isort, B bugbear, UP pyupgrade.

[tool.ruff.lint.per-file-ignores]
"__init__.py" = ["F401"]  # re-exports
"tests/*" = ["E402"]      # tests may import after small setup
```

- [ ] **Step 3: Install and auto-fix.** Run:

```bash
pip install -e ".[dev]"
ruff check . --fix
```

Auto-fix resolves import order (`I`), `pyupgrade` (`UP`), and unused imports (`F401`). Expected: most violations fixed automatically.

- [ ] **Step 4: Fix the remainder by hand, behavior-preserving.** Run `ruff check .`; for each remaining finding apply the minimal behavior-preserving fix (rename an unused variable to `_`, split a long line, add a `# noqa: <code>` ONLY with a one-line justification if a rule is genuinely wrong for that spot). Do NOT change any logic. Re-run until clean:

```bash
ruff check .
```
Expected: `All checks passed!`

- [ ] **Step 5: Confirm tests still pass** (lint fixes must not change behavior):

```bash
pytest -q
```
Expected: `194 passed` (or current count), unchanged.

- [ ] **Step 6: Add the CI step.** In `.github/workflows/ci.yml`, add as the FIRST step after `Install` (before the test runs):

```yaml
      - name: Lint (ruff)
        run: ruff check .
```

- [ ] **Step 7: Commit.**

```bash
git add pyproject.toml .github/workflows/ci.yml convergence web tests
git commit -m "ci: add ruff lint gate + fix violations (behavior-preserving)"
```

### Task A2: Typing — mypy (pragmatic)

**Files:**
- Modify: `pyproject.toml` (dev deps + `[tool.mypy]`)
- Modify: `.github/workflows/ci.yml` (add a `mypy` step)
- Modify: files mypy flags (annotations/guards only)

**Interfaces:**
- Consumes: A1's tooling baseline.
- Produces: a green `mypy convergence web` and a CI type gate.

- [ ] **Step 1: Add mypy to dev deps:**

```toml
dev = ["pytest>=7", "pytest-cov>=4", "ruff>=0.6", "mypy>=1.8"]
```

- [ ] **Step 2: Add the mypy config.** Append to `pyproject.toml`:

```toml
[tool.mypy]
python_version = "3.10"
warn_unused_ignores = true
no_implicit_optional = true
check_untyped_defs = true
warn_redundant_casts = true
warn_unused_configs = true
# ratchet (enable in a later phase): disallow_untyped_defs, disallow_any_generics,
# warn_return_any, strict_equality.

[[tool.mypy.overrides]]
module = ["openai.*", "anthropic.*", "google.*", "pexpect.*", "wexpect.*"]
ignore_missing_imports = true
```

- [ ] **Step 3: Run mypy and fix what it surfaces, type-only:**

```bash
mypy convergence web
```
For each error apply the minimal type fix — add a return/param annotation, a `cast(...)`, an `assert x is not None`, or narrow an `Optional` — **never** change runtime behavior. Expected hot spots: `web/server.py`, `web/serialize.py`, `convergence/narration.py`, the adapters. Re-run until clean:
```bash
mypy convergence web
```
Expected: `Success: no issues found`.

- [ ] **Step 4: Confirm tests still pass:**

```bash
pytest -q
```
Expected: unchanged pass count.

- [ ] **Step 5: Add the CI step.** In `.github/workflows/ci.yml`, add right after the `Lint (ruff)` step:

```yaml
      - name: Type check (mypy)
        run: mypy convergence web
```

- [ ] **Step 6: Commit.**

```bash
git add pyproject.toml .github/workflows/ci.yml convergence web
git commit -m "ci: add mypy type gate (pragmatic) + type fixes"
```

### Task A3: Real coverage enforcement (pragma audit + honest floor)

**Files:**
- Modify: `pyproject.toml` (`[tool.coverage.*]`)
- Modify: `.github/workflows/ci.yml` (align the `--cov-fail-under` number)
- Modify: `convergence/adapters/openai_llm.py` (narrow one pragma)

**Interfaces:**
- Produces: a declarative coverage config and a trustworthy required floor.

- [ ] **Step 1: Audit the pragmas.** Run:

```bash
grep -rn "pragma: no cover" convergence web
```
All 11 marks are on genuine untestable seams (network `complete()` closures, `ImportError` branches, CLI/ConPTY paths) — **keep those**. The ONE exception: `convergence/adapters/openai_llm.py`'s `complete()` carries a function-level pragma, but its error path is now exercised by `tests/test_llm_adapter.py::test_openai_api_error_degrades_to_clear_error` (via the `_client` hook). Narrow it so the tested wrapper counts and only the real network call is excluded.

- [ ] **Step 2: Narrow the OpenAI pragma.** In `convergence/adapters/openai_llm.py`, move the pragma off the `def complete` line and onto the network-call line only:

```python
    def complete(prompt: str) -> str:
        # Any API-side failure ... fall back to the deterministic narrator.
        try:
            resp = client.chat.completions.create(  # pragma: no cover - needs network/key
                model=model,
                max_completion_tokens=700,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as e:
            raise RuntimeError(
                f"OpenAI request failed ({type(e).__name__}: {e}) - check the model "
                "name/availability, or use the deterministic narrator."
            ) from e
        return resp.choices[0].message.content or ""
```

- [ ] **Step 3: Add declarative coverage config.** Append to `pyproject.toml`:

```toml
[tool.coverage.run]
source = ["convergence", "web"]

[tool.coverage.report]
exclude_also = [
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
    "raise NotImplementedError",
]
```

- [ ] **Step 4: Measure the honest floor.** Run:

```bash
pytest --cov=convergence --cov=web --cov-report=term -q | tail -3
```
Read the `TOTAL` percentage. Set the floor to that integer rounded **down** to a clean number, but never below 80 (e.g. measured 84% → floor 80; if measured ≥ 85 you may set 85). Record the measured number in the commit message.

- [ ] **Step 5: Align the CI gate.** In `.github/workflows/ci.yml`, set the `Coverage gate` step's number to the chosen floor (keep ≥ 80):

```yaml
      - name: Coverage gate (>= 80%)
        run: pytest --cov=convergence --cov=web --cov-fail-under=80 -q
```

- [ ] **Step 6: Verify the gate passes locally:**

```bash
pytest --cov=convergence --cov=web --cov-fail-under=80 -q ; echo "exit=$?"
```
Expected: `exit=0`.

- [ ] **Step 7: Commit.**

```bash
git add pyproject.toml .github/workflows/ci.yml convergence/adapters/openai_llm.py
git commit -m "ci: declarative coverage config + pragma audit (honest floor; measured NN%)"
```

### Task A4: Test-gated Pages

**Files:**
- Modify: `.github/workflows/pages.yml`

**Interfaces:**
- Produces: Pages that deploys only after the `tests` workflow succeeds on `main`.

- [ ] **Step 1: Rewrite the trigger + guard.** Replace the `on:` block and `jobs.deploy` header in `.github/workflows/pages.yml` so it is driven by the `tests` workflow:

```yaml
on:
  workflow_run:
    workflows: ["tests"]
    types: [completed]
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: false

jobs:
  deploy:
    runs-on: ubuntu-latest
    # Deploy only when the tests run that triggered us passed (or on a manual run).
    if: ${{ github.event_name == 'workflow_dispatch' || github.event.workflow_run.conclusion == 'success' }}
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - uses: actions/checkout@v5
        with:
          ref: main
      - uses: actions/configure-pages@v5
      - uses: actions/upload-pages-artifact@v3
        with:
          path: web/site
      - id: deployment
        uses: actions/deploy-pages@v4
```

Keep the file's top comment block. The `name: pages` line stays.

- [ ] **Step 2: Validate the YAML locally** (syntax only — the gate is verified operationally after merge):

```bash
python -c "import yaml; yaml.safe_load(open('.github/workflows/pages.yml')); print('pages.yml OK')"
```
Expected: `pages.yml OK`. (If `pyyaml` is absent, `pip install pyyaml` in the dev shell — it is not a project dep.)

- [ ] **Step 3: Commit.**

```bash
git add .github/workflows/pages.yml
git commit -m "ci: gate Pages deploy on a successful tests run (workflow_run)"
```

> **Reviewer/controller note:** A4 can't be self-tested in CI ("a red build does not deploy"). After merge, confirm operationally: the push's `tests` run completes, then the `pages` run fires via `workflow_run` and deploys; the live site still returns 200.

### Task B1: Constant-time chat auth

**Files:**
- Modify: `web/server.py` (`_chat_authorized` + an `import hmac`)
- Test: `tests/test_web_server.py` (existing auth tests cover behavior)

**Interfaces:**
- Produces: `_chat_authorized(headers) -> bool` — same contract, constant-time compare.

- [ ] **Step 1: Add the import.** At the top of `web/server.py`, add `import hmac` with the other stdlib imports.

- [ ] **Step 2: Replace the compare.** Change `_chat_authorized`:

```python
def _chat_authorized(headers) -> bool:
    """Gate /api/chat. Open by default (localhost dev); when CONVERGENCE_API_KEY
    is set, require a matching `X-API-Key` header (constant-time compare)."""
    required = os.environ.get("CONVERGENCE_API_KEY")
    if not required:
        return True
    provided = headers.get("X-API-Key") or ""
    return hmac.compare_digest(provided, required)
```

- [ ] **Step 3: Run the existing auth tests** (behavior is unchanged, so they must still pass):

```bash
pytest tests/test_web_server.py -q -k "chat_open or requires_matching_key"
```
Expected: PASS (open when no key; missing/wrong → False; match → True).

- [ ] **Step 4: Commit.**

```bash
git add web/server.py
git commit -m "web: constant-time chat-auth compare (hmac.compare_digest)"
```

### Task B2: Request validation + body-size cap

**Files:**
- Modify: `web/server.py` (constants, `ChatError`, `parse_content_length`, `validate_chat_request`, `do_POST`)
- Test: `tests/test_web_server.py`

**Interfaces:**
- Consumes: `corpus_names()` (existing), B1's server.
- Produces: `ChatError(status, message)`; `validate_chat_request(payload) -> tuple[str,str,str,str]`; `parse_content_length(headers) -> int`. `do_POST` maps `ChatError` → its status.

- [ ] **Step 1: Add the failing tests.** Append to `tests/test_web_server.py`:

```python
import pytest


def _clh(value):
    import email.message
    m = email.message.Message()
    if value is not None:
        m["content-length"] = value
    return m


def test_validate_chat_request_accepts_valid_and_defaults():
    from web.server import validate_chat_request
    assert validate_chat_request({"corpus": "contractor", "question": "why?"}) == (
        "contractor", "why?", "blanc", "claude")
    assert validate_chat_request(
        {"corpus": "contractor", "question": "q", "voice": "plain", "model": "openai"}
    ) == ("contractor", "q", "plain", "openai")


def test_validate_chat_request_rejects_bad_fields():
    from web.server import validate_chat_request, ChatError
    bad_payloads = [
        {},                                                         # missing corpus
        {"corpus": "nope", "question": "q"},                        # unknown corpus
        {"corpus": "contractor", "question": "   "},                # blank question
        {"corpus": "contractor", "question": "x" * 4001},           # over-long
        {"corpus": "contractor", "question": "q", "voice": "x"},    # bad voice
        {"corpus": "contractor", "question": "q", "model": "x"},    # bad model
        "not-a-dict",                                               # wrong type
    ]
    for payload in bad_payloads:
        with pytest.raises(ChatError) as exc:
            validate_chat_request(payload)
        assert exc.value.status == 400


def test_parse_content_length_enforces_cap():
    from web.server import parse_content_length, ChatError, MAX_BODY_BYTES
    assert parse_content_length(_clh("10")) == 10
    for header, status in [(_clh(None), 400), (_clh("abc"), 400),
                           (_clh(str(MAX_BODY_BYTES + 1)), 413)]:
        with pytest.raises(ChatError) as exc:
            parse_content_length(header)
        assert exc.value.status == status
```

- [ ] **Step 2: Run them — expect failure** (`ChatError`/helpers not defined):

```bash
pytest tests/test_web_server.py -q -k "validate_chat_request or parse_content_length"
```
Expected: FAIL (ImportError / AttributeError).

- [ ] **Step 3: Add constants + `ChatError`.** Near the top of `web/server.py` (after the imports / `DATA_CACHE`):

```python
MAX_BODY_BYTES = int(os.environ.get("CONVERGENCE_MAX_BODY_BYTES", "16384"))
MAX_QUESTION_LEN = 4000
ALLOWED_VOICES = {"blanc", "plain"}
ALLOWED_MODELS = {"claude", "openai", "grok", "gemini", "agy"}


class ChatError(Exception):
    """A client-facing chat error carrying an HTTP status code."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message
```

- [ ] **Step 4: Add the validators.** Add to `web/server.py`:

```python
def parse_content_length(headers) -> int:
    raw = headers.get("content-length")
    if raw is None:
        raise ChatError(400, "content-length header is required")
    try:
        length = int(raw)
    except (TypeError, ValueError) as exc:
        raise ChatError(400, "content-length must be an integer") from exc
    if length < 0:
        raise ChatError(400, "content-length must be non-negative")
    if length > MAX_BODY_BYTES:
        raise ChatError(413, f"request body too large (max {MAX_BODY_BYTES} bytes)")
    return length


def validate_chat_request(payload) -> tuple[str, str, str, str]:
    if not isinstance(payload, dict):
        raise ChatError(400, "request body must be a JSON object")
    corpus = payload.get("corpus")
    if not isinstance(corpus, str) or corpus not in corpus_names():
        raise ChatError(400, f"unknown or missing corpus: {corpus!r}")
    question = payload.get("question")
    if not isinstance(question, str) or not question.strip():
        raise ChatError(400, "question is required")
    if len(question) > MAX_QUESTION_LEN:
        raise ChatError(400, f"question too long (max {MAX_QUESTION_LEN} chars)")
    voice = payload.get("voice", "blanc")
    if voice not in ALLOWED_VOICES:
        raise ChatError(400, f"voice must be one of {sorted(ALLOWED_VOICES)}")
    model = payload.get("model", "claude")
    if model not in ALLOWED_MODELS:
        raise ChatError(400, f"model must be one of {sorted(ALLOWED_MODELS)}")
    return corpus, question, voice, model
```

- [ ] **Step 5: Rewrite `do_POST`** to use them and map `ChatError` → status:

```python
    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/chat":
            self._json({"error": "unknown endpoint"}, status=404)
            return
        if not _chat_authorized(self.headers):
            self._json({"error": "unauthorized"}, status=401)
            return
        try:
            length = parse_content_length(self.headers)
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            corpus, question, voice, model = validate_chat_request(payload)
            answer = answer_chat(corpus=corpus, question=question, voice=voice, model=model)
            self._json({"answer": str(answer)})
        except ChatError as exc:
            self._json({"error": exc.message}, status=exc.status)
        except json.JSONDecodeError:
            self._json({"error": "request body must be valid JSON"}, status=400)
        except Exception as exc:
            self._json({"error": str(exc)}, status=400)
```

- [ ] **Step 6: Run the new tests + the suite:**

```bash
pytest tests/test_web_server.py -q
pytest -q
```
Expected: new validation/cap tests PASS; full suite green.

- [ ] **Step 7: Commit.**

```bash
git add web/server.py tests/test_web_server.py
git commit -m "web: schema-validate /api/chat requests + cap request body (400/413)"
```

### Task B3: LLM-call timeout

**Files:**
- Modify: `web/server.py` (`LLM_TIMEOUT_S`, a bounded pool, `call_with_timeout`, `do_POST`)
- Test: `tests/test_web_server.py`

**Interfaces:**
- Consumes: B2's `ChatError`.
- Produces: `call_with_timeout(fn, timeout_s)` — runs `fn()` with a result timeout, raising `ChatError(504, ...)` on hang.

- [ ] **Step 1: Add the failing test.** Append to `tests/test_web_server.py`:

```python
def test_call_with_timeout_returns_fast_and_504s_slow():
    import time
    from web.server import call_with_timeout, ChatError
    assert call_with_timeout(lambda: 7, 5) == 7
    with pytest.raises(ChatError) as exc:
        call_with_timeout(lambda: time.sleep(2), 0.05)
    assert exc.value.status == 504
```

- [ ] **Step 2: Run it — expect failure:**

```bash
pytest tests/test_web_server.py -q -k "call_with_timeout"
```
Expected: FAIL (not defined).

- [ ] **Step 3: Add the timeout helper.** In `web/server.py`, add the import at top:

```python
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
```

and, near the other constants:

```python
LLM_TIMEOUT_S = float(os.environ.get("CONVERGENCE_LLM_TIMEOUT_S", "30"))
# Bounded pool: also caps concurrent chat work. A timed-out worker keeps running
# to completion in the background (threads can't be force-killed) — acceptable
# for a local demo; the request already returned 504.
_CHAT_POOL = ThreadPoolExecutor(max_workers=4)


def call_with_timeout(fn, timeout_s: float):
    future = _CHAT_POOL.submit(fn)
    try:
        return future.result(timeout=timeout_s)
    except FuturesTimeout:
        raise ChatError(504, "the language model did not respond in time") from None
```

- [ ] **Step 4: Wrap the call in `do_POST`.** Change the `answer = answer_chat(...)` line to:

```python
            answer = call_with_timeout(
                lambda: answer_chat(corpus=corpus, question=question, voice=voice, model=model),
                LLM_TIMEOUT_S,
            )
```

- [ ] **Step 5: Run the new test + suite + lint + types:**

```bash
pytest tests/test_web_server.py -q
pytest -q
ruff check . && mypy convergence web
```
Expected: all green.

- [ ] **Step 6: Commit.**

```bash
git add web/server.py tests/test_web_server.py
git commit -m "web: timeout the LLM call in /api/chat (504 on hang) + bound concurrency"
```

---

## Notes for the executor

- The controller pre-creates each task's branch; implementers commit LOCALLY (explicit `git add` of the listed paths). The controller pushes → opens a PR → waits for the `tests` workflow (and, from A1/A2 on, the ruff/mypy gates) → squash-merges.
- **Behavior-preserving discipline (A1/A2):** if a lint or type "fix" would change runtime behavior, it is wrong — annotate/guard instead, or leave a justified `# noqa`/`# type: ignore[code]` with a one-line reason. The full test suite must show the same pass count before and after.
- **No engine logic changes.** The only `convergence/` edits are import/annotation/pragma cosmetics. If a real bug surfaces, log it for a later phase — do not fix it here.
- **A4 is review-confirmed**, not CI-self-tested; the controller verifies the workflow_run gate operationally after merge.
- After B3, `web/server.py` request flow is: auth → `parse_content_length` → read body → JSON parse → `validate_chat_request` → `call_with_timeout(answer_chat)` → `{"answer": ...}`, with `ChatError` mapping cleanly to 400/413/504.
