"""Local stdlib server for the convergence web demo."""
from __future__ import annotations

import hmac
import json
import mimetypes
import os
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from convergence.conversation import BLANC_PERSONA, Conversation
from web.build import build
from web.serialize import (
    corpus_names,
    load_analysis,
    serialize_corpus,
    serialize_dynamics,
    serialize_index,
)

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "web" / "site"
DATA_CACHE: dict[str, dict] = {}

MAX_BODY_BYTES = int(os.environ.get("CONVERGENCE_MAX_BODY_BYTES", "16384"))
MAX_QUESTION_LEN = 4000
ALLOWED_VOICES = {"blanc", "plain"}
ALLOWED_MODELS = {"claude", "openai", "grok", "gemini", "agy"}

LLM_TIMEOUT_S = float(os.environ.get("CONVERGENCE_LLM_TIMEOUT_S", "30"))
# Bounded pool: also caps concurrent chat work. A timed-out worker keeps running
# to completion in the background (threads can't be force-killed) — acceptable
# for a local demo; the request already returned 504.
_CHAT_POOL = ThreadPoolExecutor(max_workers=4)


class ChatError(Exception):
    """A client-facing chat error carrying an HTTP status code."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


def call_with_timeout(fn: Callable[[], str], timeout_s: float) -> str:
    future = _CHAT_POOL.submit(fn)
    try:
        return future.result(timeout=timeout_s)
    except FuturesTimeout:
        raise ChatError(504, "the language model did not respond in time") from None


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


def ensure_static_data() -> None:
    if not (SITE / "data" / "index.json").exists():
        build()


def make_complete(model: str):
    if model == "openai":
        from convergence.adapters.openai_llm import make_openai_complete
        return make_openai_complete()
    if model == "grok":
        from convergence.adapters.grok_llm import make_grok_complete
        return make_grok_complete()
    if model == "gemini":
        try:
            from convergence.adapters.gemini_llm import make_gemini_complete
            return make_gemini_complete()
        except Exception:
            from convergence.adapters.gemini_cli_llm import make_gemini_cli_complete
            return make_gemini_cli_complete()
    if model == "agy":
        from convergence.adapters.antigravity_cli_llm import make_antigravity_cli_complete
        return make_antigravity_cli_complete()
    from convergence.adapters.anthropic_llm import make_anthropic_complete
    return make_anthropic_complete()


def answer_chat(corpus: str, question: str, voice: str = "blanc", model: str = "claude", complete=None) -> str:  # noqa: E501
    if corpus not in corpus_names():
        raise KeyError(f"unknown corpus: {corpus}")
    if not question.strip():
        raise ValueError("question is required")

    _, result, _ = load_analysis(corpus)
    complete_fn = complete or make_complete(model)
    persona = BLANC_PERSONA if voice == "blanc" else ""
    conversation = Conversation(result, complete_fn, persona=persona, compact=(model == "agy"))
    return conversation.ask(question)


class Handler(BaseHTTPRequestHandler):
    server_version = "convergence-demo/1.0"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self._json({"ok": True, "chat": True, "corpora": corpus_names()})
            return
        if parsed.path == "/api/index":
            self._json(serialize_index())
            return
        if parsed.path == "/api/dynamics":
            self._json(serialize_dynamics())
            return
        if parsed.path.startswith("/api/corpus/"):
            name = unquote(parsed.path.rsplit("/", 1)[-1])
            if name not in corpus_names():
                self._json({"error": f"unknown corpus: {name}"}, status=404)
                return
            self._json(DATA_CACHE.setdefault(name, serialize_corpus(name)))
            return
        self._static(parsed.path)

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
            answer = call_with_timeout(
                lambda: answer_chat(corpus=corpus, question=question, voice=voice, model=model),
                LLM_TIMEOUT_S,
            )
            self._json({"answer": str(answer)})
        except ChatError as exc:
            self._json({"error": exc.message}, status=exc.status)
        except json.JSONDecodeError:
            self._json({"error": "request body must be valid JSON"}, status=400)
        except Exception as exc:
            self._json({"error": str(exc)}, status=400)

    def log_message(self, format, *args):  # noqa: A002 - stdlib signature
        return

    def _static(self, request_path: str) -> None:
        safe_path = request_path.strip("/") or "index.html"
        target = (SITE / safe_path).resolve()
        site = SITE.resolve()
        if not (site == target or site in target.parents) or not target.is_file():
            self._json({"error": "not found"}, status=404)
            return
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        body = target.read_bytes()
        self.send_response(200)
        self.send_header("content-type", content_type)
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, payload, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def serve(host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    ensure_static_data()
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"convergence demo: http://{host}:{port}/")
    server.serve_forever()
    return server


def _chat_authorized(headers) -> bool:
    """Gate /api/chat. Open by default (localhost dev); when CONVERGENCE_API_KEY
    is set, require a matching `X-API-Key` header (constant-time compare)."""
    required = os.environ.get("CONVERGENCE_API_KEY")
    if not required:
        return True
    provided = headers.get("X-API-Key") or ""
    return hmac.compare_digest(provided, required)


def _config_from_env() -> tuple[str, int]:
    """Bind config. Defaults to localhost (safe); override via env for containers.

    CONVERGENCE_HOST=0.0.0.0 exposes the server beyond localhost — only do this
    behind a trusted boundary, since /api/chat proxies to paid LLM backends.
    """
    host = os.environ.get("CONVERGENCE_HOST", "127.0.0.1")
    port = int(os.environ.get("CONVERGENCE_PORT", "8765"))
    return host, port


_LOOPBACK = {"127.0.0.1", "localhost", "::1"}


def main() -> None:
    host, port = _config_from_env()
    if host not in _LOOPBACK and not os.environ.get("CONVERGENCE_API_KEY"):
        raise SystemExit(
            "ERROR: CONVERGENCE_API_KEY must be set when binding to a non-loopback "
            f"address ({host!r}). Set CONVERGENCE_API_KEY or bind to localhost."
        )
    serve(host, port)


if __name__ == "__main__":
    main()
