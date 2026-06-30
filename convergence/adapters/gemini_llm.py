"""Optional Gemini adapter for the conversational layer.

Like the Anthropic adapter, this is one of the only places the engine touches a
third-party SDK or an API key, and the core never imports it. It produces a
`complete(prompt) -> str` callable to inject into `Conversation` - so the *same*
Blanc prompt and structured findings can be answered by Gemini (a flash model is
fast). If there is no key or no SDK, it raises a clear error so the demo falls
back to the deterministic narrator.

Supports either Google SDK: the classic `google-generativeai` or the newer
`google-genai`. Key from GEMINI_API_KEY or GOOGLE_API_KEY.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

_MODEL = "gemini-2.5-flash"  # flash = fast; override via make_gemini_complete(model=...)
_KEYS = ("GEMINI_API_KEY", "GOOGLE_API_KEY")


def _default_dotenv_paths():
    # the cwd (where `python demo.py` runs) and the demo root (this file's great-grandparent)
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


def make_gemini_complete(model: str = _MODEL, api_key: str | None = None,
                         _env=None, _dotenv_paths=None) -> Callable[[str], str]:
    env = _env if _env is not None else os.environ
    key = api_key or env.get("GEMINI_API_KEY") or env.get("GOOGLE_API_KEY")
    if not key:  # fall back to a local .env file
        paths = _default_dotenv_paths() if _dotenv_paths is None else _dotenv_paths
        key = _read_dotenv(paths)
    if not key:
        raise RuntimeError(
            "GEMINI_API_KEY (or GOOGLE_API_KEY) not set in the environment or a .env file - "
            "conversational mode needs a key. Use the deterministic narrator instead."
        )

    # classic SDK: google-generativeai
    try:
        import google.generativeai as genai  # type: ignore
    except ImportError:
        genai = None
    if genai is not None:  # pragma: no cover - needs SDK/network
        genai.configure(api_key=key)
        gm = genai.GenerativeModel(model)

        def complete(prompt: str) -> str:
            return (gm.generate_content(prompt).text or "")

        return complete

    # newer SDK: google-genai
    try:
        from google import genai as _genai  # type: ignore
    except ImportError as e:  # pragma: no cover - depends on environment
        raise RuntimeError(
            "Neither `google-generativeai` nor `google-genai` is installed - "
            "run `pip install google-generativeai`, or use the deterministic narrator."
        ) from e

    client = _genai.Client(api_key=key)  # pragma: no cover - needs SDK/network

    def complete(prompt: str) -> str:  # pragma: no cover - needs network/key
        try:
            resp = client.models.generate_content(model=model, contents=prompt)
        except Exception as e:
            raise RuntimeError(
                f"Gemini request failed ({type(e).__name__}: {e}) - check the model "
                "name/availability, or use the deterministic narrator."
            ) from e
        return getattr(resp, "text", "") or ""

    return complete
