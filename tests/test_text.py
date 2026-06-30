"""Shared deterministic text helpers used by Layers 1, 4, 5."""
from convergence.text import ngrams, normalize, tokens


def test_normalize_lowercases_and_collapses_whitespace():
    assert normalize("  The   PLATFORM\tsays  ") == "the platform says"


def test_tokens_drops_punctuation_keeps_apostrophes():
    assert tokens("I won't, really!") == ["i", "won't", "really"]


def test_tokens_empty_string():
    assert tokens("   ") == []


def test_ngrams_length_and_content():
    assert ngrams(["a", "b", "c"], 2) == [("a", "b"), ("b", "c")]


def test_ngrams_too_short_returns_empty():
    assert ngrams(["a"], 2) == []


def test_curly_apostrophe_keeps_contraction_whole():
    assert tokens("she’s doing") == ["she's", "doing"]
    assert tokens("don’t think") == ["don't", "think"]


def test_straight_apostrophe_unchanged():
    assert tokens("she's doing") == ["she's", "doing"]
