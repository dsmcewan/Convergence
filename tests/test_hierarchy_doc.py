"""HIERARCHY.md must describe the spine the engine actually builds.

The four tiers (tactics -> findings -> patterns -> campaigns) map to four
dataclasses and six layers in code. These tests fail if the doc omits a tier's
data structure or a layer - so the documented spine cannot drift from the code.
"""
from pathlib import Path

from convergence.engine import _KIND_PHRASES

DOC = (Path(__file__).parent.parent / "HIERARCHY.md").read_text(encoding="utf-8")
_LOWER = DOC.lower()


def test_every_tier_datastructure_named():
    for name in ("Signal", "Finding", "Pattern", "Campaign"):
        assert name in DOC


def test_every_tier_label_present():
    for tier in ("tactic", "finding", "pattern", "campaign"):
        assert tier in _LOWER


def test_every_layer_referenced():
    for layer in ("L1", "L2", "L3", "L4", "L5", "L6"):
        assert layer in DOC


def test_signal_kinds_appear():
    # the moves the spine is built from are named in the doc
    assert [k for k in _KIND_PHRASES if k not in _LOWER] == []
