"""Optional adapter that drives the installed Antigravity CLI (`agy`).

Like the Gemini CLI adapter, this needs no API key: `agy` is authenticated through
the Antigravity app (Google account / OAuth) and answers from a fast Gemini backend
(`cloudcode-pa.googleapis.com`). It returns the same `complete(prompt) -> str` seam
to inject into `Conversation`, so the Voice of Convergence can speak through it.

The wrinkle: `agy --print` renders its answer to the terminal, and writes *nothing*
to a redirected pipe - so a plain `subprocess.run(capture_output=True)` comes back
empty. We instead run it inside a pseudo-console (ConPTY, via `pywinpty`) so the CLI
believes it has a real terminal, then strip the terminal control sequences from the
captured stream. The prompt is passed as a single argv element (it won't read stdin),
which preserves the embedded quotes and newlines of the findings dump.

Like the other adapters this lives only here; the core never imports it, and a
missing CLI or missing `pywinpty` raises a clear error so the demo falls back to the
deterministic narrator.
"""
from __future__ import annotations

import re
import shutil
import time
from typing import Callable

# CSI / simple-escape control sequences, plus OSC (window-title) strings. `agy` in
# print mode emits only a short terminal handshake (\x1b[1t \x1b[c \x1b[?1004h
# \x1b[?9001h) ahead of plain text, but we strip the general families to be safe.
_ANSI = re.compile(
    r"\x1b\[[0-9;?]*[ -/]*[@-~]"      # CSI ... final byte
    r"|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)"  # OSC ... BEL/ST
    r"|\x1b[()][AB0-2]"              # charset select
    r"|\x1b[=>]"                     # keypad mode
)


def _strip(raw: str) -> str:
    return _ANSI.sub("", raw).replace("\r\n", "\n").replace("\r", "").strip()


def make_antigravity_cli_complete(model: str | None = None, _which=shutil.which,
                                  timeout: float = 180.0) -> Callable[[str], str]:
    exe = _which("agy") or _which("agy.exe")
    if not exe:
        raise RuntimeError(
            "agy (Antigravity CLI) not found on PATH - install it and sign in via the "
            "Antigravity app, or use the deterministic narrator."
        )

    def complete(prompt: str) -> str:  # pragma: no cover - needs the CLI + a ConPTY + network
        try:
            from winpty import PtyProcess
        except ImportError as e:
            raise RuntimeError(
                "pywinpty not installed - `agy` only emits its answer to a real "
                "terminal, so this adapter needs a ConPTY (`pip install pywinpty`). "
                "Use the deterministic narrator instead."
            ) from e

        # A single prompt as one argv element keeps its quotes/newlines intact; `agy`
        # does not read the prompt from stdin. A wide, tall pseudo-console keeps the
        # CLI from wrapping or scrolling the answer.
        argv = [exe, "--print", prompt]
        if model:
            argv += ["--model", model]
        proc = PtyProcess.spawn(argv, dimensions=(200, 1000))
        chunks = []
        start = time.time()
        try:
            while True:
                try:
                    data = proc.read(8192)
                except EOFError:
                    break
                if data:
                    chunks.append(data)
                elif not proc.isalive():
                    break
                else:
                    time.sleep(0.03)
                if time.time() - start > timeout:
                    raise RuntimeError(f"agy timed out after {timeout:.0f}s")
        finally:
            try:
                if proc.isalive():
                    proc.terminate(force=True)
            except Exception:
                pass

        out = _strip("".join(chunks))
        if not out:
            raise RuntimeError(
                "agy returned no text - it may not be signed in (open the Antigravity "
                "app to authenticate). Use the deterministic narrator instead."
            )
        return out

    return complete
