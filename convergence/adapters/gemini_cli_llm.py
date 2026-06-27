"""Optional Gemini adapter that drives the installed `gemini` CLI.

Your setup authenticates the Gemini CLI by Google account (oauth-personal), not an
API key - so the API-key SDK in `gemini_llm.py` can't see it. This adapter instead
shells out to the `gemini` CLI, reusing that OAuth, and returns the same
`complete(prompt) -> str` seam to inject into `Conversation`. The prompt is fed on
stdin (no command-length limit). Like the other adapters, it lives only here; the
core never imports it, and a missing CLI raises a clear error so the demo falls back
to the deterministic narrator.
"""
from __future__ import annotations

import shutil
import subprocess
from typing import Callable

_MODEL = "gemini-2.5-flash"  # flash = fast


def make_gemini_cli_complete(model: str = _MODEL, _which=shutil.which) -> Callable[[str], str]:
    exe = _which("gemini") or _which("gemini.cmd")
    if not exe:
        raise RuntimeError(
            "gemini CLI not found on PATH - install it (`npm i -g @google/gemini-cli`) "
            "and `gemini` to sign in, or use the deterministic narrator."
        )

    def complete(prompt: str) -> str:  # pragma: no cover - needs the CLI + network
        proc = subprocess.run(
            [exe, "-m", model],
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"gemini CLI error: {(proc.stderr or '').strip()[:300]}")
        return (proc.stdout or "").strip()

    return complete
