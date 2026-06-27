"""Local stdlib server for the convergence web demo."""
from __future__ import annotations

import json
import mimetypes
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from convergence.conversation import BLANC_PERSONA, Conversation
from web.build import build
from web.serialize import corpus_names, load_analysis, serialize_corpus, serialize_dynamics, serialize_index

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "web" / "site"
DATA_CACHE: dict[str, dict] = {}


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


def answer_chat(corpus: str, question: str, voice: str = "blanc", model: str = "claude", complete=None) -> str:
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
            length = int(self.headers.get("content-length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            answer = answer_chat(
                corpus=str(payload.get("corpus", "")),
                question=str(payload.get("question", "")),
                voice=str(payload.get("voice", "blanc")),
                model=str(payload.get("model", "claude")),
            )
            self._json({"answer": answer})
        except Exception as exc:
            self._json({"error": str(exc)}, status=400)

    def log_message(self, format, *args):  # noqa: A002 - stdlib signature
        return

    def _static(self, request_path: str) -> None:
        safe_path = request_path.strip("/") or "index.html"
        target = (SITE / safe_path).resolve()
        if not str(target).startswith(str(SITE.resolve())) or not target.is_file():
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
    is set, require a matching `X-API-Key` header. /api/chat proxies to paid LLM
    backends, so an exposed deployment should set the key to prevent abuse."""
    required = os.environ.get("CONVERGENCE_API_KEY")
    if not required:
        return True
    return headers.get("X-API-Key") == required


def _config_from_env() -> tuple[str, int]:
    """Bind config. Defaults to localhost (safe); override via env for containers.

    CONVERGENCE_HOST=0.0.0.0 exposes the server beyond localhost — only do this
    behind a trusted boundary, since /api/chat proxies to paid LLM backends.
    """
    host = os.environ.get("CONVERGENCE_HOST", "127.0.0.1")
    port = int(os.environ.get("CONVERGENCE_PORT", "8765"))
    return host, port


def main() -> None:
    host, port = _config_from_env()
    serve(host, port)


if __name__ == "__main__":
    main()
