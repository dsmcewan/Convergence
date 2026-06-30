"""Optional Grok/xAI adapter for the conversational layer.

Grok's API is OpenAI-compatible, so this adapter uses the optional `openai`
SDK with xAI's base URL. The key is read from XAI_API_KEY or GROK_API_KEY in
the environment or a local .env file. The deterministic engine remains
stdlib-only and never imports this module.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

_MODEL = "grok-4"
_BASE_URL = "https://api.x.ai/v1"
_KEYS = ("XAI_API_KEY", "GROK_API_KEY")


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


def make_grok_complete(model: str = _MODEL, api_key: str | None = None,
                       _env=None, _dotenv_paths=None) -> Callable[[str], str]:
    env = _env if _env is not None else os.environ
    key = api_key or next((env.get(k) for k in _KEYS if env.get(k)), None)
    if not key:
        paths = _default_dotenv_paths() if _dotenv_paths is None else _dotenv_paths
        key = _read_dotenv(paths)
    if not key:
        raise RuntimeError(
            "XAI_API_KEY or GROK_API_KEY not set in the environment or a .env file - "
            "conversational mode needs a key. Use the deterministic narrator instead."
        )
    try:
        from openai import OpenAI
    except ImportError as e:  # pragma: no cover - depends on environment
        raise RuntimeError(
            "openai SDK not installed - run `pip install openai`, or use the "
            "deterministic narrator."
        ) from e

    client = OpenAI(api_key=key, base_url=_BASE_URL)

    def complete(prompt: str) -> str:  # pragma: no cover - needs network/key
        try:
            resp = client.chat.completions.create(
                model=model,
                max_tokens=700,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as e:
            raise RuntimeError(
                f"Grok request failed ({type(e).__name__}: {e}) - check the model "
                "name/availability, or use the deterministic narrator."
            ) from e
        return resp.choices[0].message.content or ""

    return complete
