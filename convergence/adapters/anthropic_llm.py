"""Optional Anthropic adapter for the conversational layer.

This is the ONLY place the engine can touch a third-party SDK or an API key,
and the core never imports it. It produces a `complete(prompt) -> str` callable
to inject into `Conversation`. If there is no key or no SDK, it raises a clear
error so the demo can fall back to the deterministic narrator.
"""
from __future__ import annotations

import os
from collections.abc import Callable

_MODEL = "claude-sonnet-4-6"


def make_anthropic_complete(
    model: str = _MODEL, api_key: str | None = None, _env=None, _client=None
) -> Callable[[str], str]:
    env = _env if _env is not None else os.environ
    key = api_key or env.get("ANTHROPIC_API_KEY")
    if not key and _client is None:
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

    client = _client or anthropic.Anthropic(api_key=key)

    def complete(prompt: str) -> str:  # pragma: no cover - needs network/key
        try:
            kwargs: dict = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
            }
            # Enable thinking/reasoning for models that support it
            if "claude-3-7" in model:
                kwargs["max_tokens"] = 4096
                kwargs["thinking"] = {
                    "type": "enabled",
                    "budget_tokens": 1024
                }
            elif (
                "claude-sonnet-4-6" in model
                or "claude-4" in model
                or "claude-sonnet-latest" in model
                or "claude-opus-latest" in model
            ):
                kwargs["max_tokens"] = 8192
                kwargs["thinking"] = {
                    "type": "adaptive"
                }
                kwargs["output_config"] = {
                    "effort": "high"
                }
            else:
                kwargs["max_tokens"] = 700

            msg = client.messages.create(**kwargs)
        except Exception as e:
            raise RuntimeError(
                f"Anthropic request failed ({type(e).__name__}: {e}) - check the model "
                "name/availability, or use the deterministic narrator."
            ) from e

        # Extract thinking and text blocks
        thoughts = []
        texts = []
        for block in msg.content:
            b_type = getattr(block, "type", None)
            if b_type == "thinking":
                thoughts.append(getattr(block, "thinking", ""))
            elif b_type == "text":
                texts.append(getattr(block, "text", ""))

        if thoughts:
            thinking_process = "".join(thoughts)
            if thinking_process.strip():
                print(f"\n[Claude Thinking]\n{thinking_process.strip()}\n")

        return "".join(texts)

    return complete

