"""FRAGMENTS.md must stay in sync with the code lexicons.

Provenance is the point of this engine: a finding traces to a named fragment in a
named file. A catalog that drifts from the vocabulary it claims to describe is
worse than none. These tests fail if a fragment is added to a lexicon but not
documented - so the doc cannot silently rot.
"""
from pathlib import Path

from convergence.layers.pattern_detector import ASSERTION_VERBS, AUTHORITY_ROOTS
from convergence.layers.phrase_fragmentation import FORMAL_LEXICON

DOC = (Path(__file__).parent.parent / "FRAGMENTS.md").read_text(encoding="utf-8").lower()


def test_authority_roots_documented():
    assert [t for t in AUTHORITY_ROOTS if t not in DOC] == []


def test_assertion_verbs_documented():
    assert [t for t in ASSERTION_VERBS if t not in DOC] == []


def test_formal_lexicon_documented():
    assert [t for t in FORMAL_LEXICON if t not in DOC] == []
