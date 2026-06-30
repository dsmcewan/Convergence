"""Optional Anthropic adapter for the conversational layer.

This is the ONLY place the engine can touch a third-party SDK or an API key,
and the core never imports it. It produces a `complete(prompt) -> str` callable
to inject into `Conversation`. If there is no key or no SDK, it raises a clear
error so the demo can fall back to the deterministic narrator.
"""
from __future__ import annotations

import os
from typing import Callable

_MODEL = "claude-sonnet-4-6"


def make_anthropic_complete(model: str = _MODEL, api_key: str | None = None, _env=None) -> Callable[[str], str]:
    env = _env if _env is not None else os.environ
    key = api_key or env.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY not set - conversational mode needs a key. "
            "Use the deterministic narrator instead."
        )
    try:
        import anthropic
    except ImportError as e:  # pragma: no cover - depends on environment
        raise RuntimeError(
            "anthropic SDK not installed - run `pip install anthropic`, "
            "or use the deterministic narrator."
        ) from e

    client = anthropic.Anthropic(api_key=key)

    def complete(prompt: str) -> str:  # pragma: no cover - needs network/key
        try:
            msg = client.messages.create(
                model=model,
                max_tokens=700,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as e:
            raise RuntimeError(
                f"Anthropic request failed ({type(e).__name__}: {e}) - check the model "
                "name/availability, or use the deterministic narrator."
            ) from e
        return "".join(getattr(b, "text", "") for b in msg.content)

    return complete
