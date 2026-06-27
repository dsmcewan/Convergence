"""INTENT.md must cover every detectable move.

Provenance of the *why*: a move should never be detected without its communicative
function written down. These tests fail if a signal kind (engine) or a named
tactic-chain (composition) is added in code but not documented in INTENT.md.
"""
from pathlib import Path

from convergence.engine import _KIND_PHRASES
from convergence.composition import _TEMPLATES

DOC = (Path(__file__).parent.parent / "INTENT.md").read_text(encoding="utf-8").lower()


def test_every_signal_kind_has_a_documented_function():
    assert [k for k in _KIND_PHRASES if k not in DOC] == []


def test_every_template_has_a_documented_function():
    assert [t.name for t in _TEMPLATES if t.name.lower() not in DOC] == []
