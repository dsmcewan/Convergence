# Security & Threat Model

Convergence is a **deterministic, local-first** communication-forensics engine.
The engine core is stdlib-only, reads no network, and holds no secrets. The
attack surface is small and concentrated in the optional web server and the
optional LLM chat backends. This document states what is trusted, what is not,
and how to deploy safely.

## Assets

- **The corpus under analysis** — message/record data (synthetic demo corpora, or
  a private SQLite DB you supply). May be sensitive.
- **LLM API keys** — `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `XAI_API_KEY`/
  `GROK_API_KEY`, `GEMINI_API_KEY`. Spendable credentials.
- **Engine verdicts** — the elevated/low findings. Integrity matters: a verdict
  must come only from the deterministic layers, never from a model.

## Trust boundaries

- **The engine and the deterministic narrator are trusted and offline.** No
  network, no key handling, no I/O beyond reading the corpus. A model can never
  move a verdict — `Conversation` answers from the structured findings only, and
  the prompt is built *after* the verdict is fixed.
- **The LLM adapters are the only network egress.** They are opt-in; absent a
  key/CLI each degrades to the deterministic narrator. Findings are computed
  locally; only an explanation prompt (already-public finding text) leaves the
  machine when a chat backend is selected.
- **The web server is local-first.** It binds `127.0.0.1` by default.

## Threats and mitigations

| Threat | Mitigation |
|---|---|
| **`/api/chat` abuse → runaway LLM spend.** The chat endpoint proxies to paid backends. If exposed, an attacker can drive cost. | Localhost bind by default. For any exposed deployment, set `CONVERGENCE_API_KEY` — `/api/chat` then requires a matching `X-API-Key` header (HTTP 401 otherwise). Consider a reverse proxy with rate limiting (see below). |
| **Key disclosure.** Committed or logged keys. | Keys live in env or a gitignored `.env` (`.env`, `.env.*` ignored; `.env.example` is the only tracked variant). The server never logs request bodies or keys. CI/history scanned for committed keys. |
| **Path traversal on static files.** `/<path>` could escape the site root. | `_static` resolves the target and rejects anything whose resolved path is not equal to or under `web/site` (parent-walk check) and any non-file. |
| **SQL injection via a DB table or column name.** `load_sqlite_corpus(table=...)` and `load_documentary_ids(sources=...)`. | Both loaders validate every identifier (`replace("_","").isalnum()`) before any interpolation, and both open the DB read-only (`mode=ro`). |
| **Corpus exfiltration via chat prompt.** A model sees finding text. | The prompt carries only structured findings (never raw corpus dumps or detection code), and only for the corpus the user selected. Selecting a chat backend is an explicit, network-egress action. |
| **Verdict tampering by a model.** | Verdicts are computed before any prompt is built; the conversational layer is presentation-only and cannot elevate or suppress a finding. |

## Deploying beyond localhost

The default is safe; exposing the server is a deliberate, gated choice:

1. Set `CONVERGENCE_HOST=0.0.0.0` (the Docker image does this).
2. Set `CONVERGENCE_API_KEY` to a strong random value and send it as `X-API-Key`.
3. Put it behind a reverse proxy (TLS + rate limiting). The in-process key gate
   stops casual abuse; it is not a substitute for network-level rate limiting.
4. Never expose a server configured with real LLM keys without (2) and (3).

## Reporting

This is a research/demo project. If you find a vulnerability, open an issue
describing it (omit any real keys or private corpus data from the report).
