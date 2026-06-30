"""Smoke tests for demo.py CLI branches that read Signal.evidence.

These tests are deterministic (no LLM/network calls) and cover the three
CLI paths that were raising AttributeError: 'Signal' object has no attribute
'detail' before the Phase 1 fix (demo.py:139, demo.py:161).
"""

import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "demo.py", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )


def test_demo_summary_exits_zero() -> None:
    """--summary prints elevated/low counts; exercises demo.py:139 (s.evidence)."""
    result = _run("--corpus", "contractor", "--summary")
    assert result.returncode == 0, result.stderr


def test_demo_seq_exits_zero() -> None:
    """--seq prints signal detail; exercises demo.py:161 (s.evidence)."""
    result = _run("--corpus", "contractor", "--seq", "1")
    assert result.returncode == 0, result.stderr


def test_demo_sender_exits_zero() -> None:
    """--sender filters summary; exercises demo.py:133/139 (s.evidence)."""
    result = _run("--corpus", "contractor", "--sender", "Morgan")
    assert result.returncode == 0, result.stderr
