"""Optional OpenAI adapter for the conversational layer.

Like the other adapters, this is one of the only places the engine touches a
third-party SDK or an API key, and the core never imports it. It produces a
`complete(prompt) -> str` callable to inject into `Conversation` - so the same
Blanc prompt and structured findings can be answered by an OpenAI model. The key
is read from OPENAI_API_KEY in the environment or a local .env file. If there is
no key or no SDK, it raises a clear error so the demo falls back to the
deterministic narrator.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

_MODEL = "gpt-4o"  # override via make_openai_complete(model=...)
_KEYS = ("OPENAI_API_KEY",)


def _default_dotenv_paths():
    return [Path.cwd() / ".env", Path(__file__).resolve().parents[2] / ".env"]


def _read_dotenv(paths) -> str | None:
    """Minimal KEY=VALUE .env reader (stdlib only); returns the first matching key."""
    for p in paths:
        try:
            if not p.is_file():
                continue
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                if k.strip() in _KEYS:
                    v = v.strip().strip('"').strip("'")
                    if v:
                        return v
        except OSError:
            continue
    return None


def make_openai_complete(model: str = _MODEL, api_key: str | None = None,
                         _env=None, _dotenv_paths=None, _client=None) -> Callable[[str], str]:
    env = _env if _env is not None else os.environ
    key = api_key or env.get("OPENAI_API_KEY")
    if not key:  # fall back to a local .env file
        paths = _default_dotenv_paths() if _dotenv_paths is None else _dotenv_paths
        key = _read_dotenv(paths)
    if not key:
        raise RuntimeError(
            "OPENAI_API_KEY not set in the environment or a .env file - conversational "
            "mode needs a key. Use the deterministic narrator instead."
        )
    if _client is not None:
        client = _client
    else:
        try:
            from openai import OpenAI
        except ImportError as e:  # pragma: no cover - depends on environment
            raise RuntimeError(
                "openai SDK not installed - run `pip install openai`, or use the "
                "deterministic narrator."
            ) from e
        client = OpenAI(api_key=key)

    def complete(prompt: str) -> str:
        # Any API-side failure (invalid model, rate limit, network) degrades to the
        # same clear, caller-catchable error as a missing key/SDK, so the demo can
        # fall back to the deterministic narrator instead of leaking a raw traceback.
        try:
            resp = client.chat.completions.create(
                model=model,
                max_completion_tokens=700,  # required by gpt-5.x; also accepted by gpt-4.x
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as e:
            raise RuntimeError(
                f"OpenAI request failed ({type(e).__name__}: {e}) - check the model "
                "name/availability, or use the deterministic narrator."
            ) from e
        return resp.choices[0].message.content or ""

    return complete
