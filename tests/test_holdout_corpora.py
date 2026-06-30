"""Blind holdout: a frozen, fresh-subagent-authored set scored on a separate
generalization line. We assert the holdout LOADS and SCORES deterministically and
that the tiered report includes it. We deliberately do NOT assert a holdout
pass-rate or per-corpus correctness — asserting that would re-introduce a tuning
signal and defeat the blindness. The number is reported, not chased.
"""
from pathlib import Path

from convergence.corpus import load_corpus
from convergence.evaluation import (
    HOLDOUT_LABELS,
    classify_coercive,
    evaluate_tiered,
    format_tiered_report,
)

DATA = Path(__file__).parent.parent / "data"
HOLDOUT = DATA / "holdout"


def test_holdout_set_is_three_labeled_corpora():
    assert set(HOLDOUT_LABELS) == {
        "hold_coercive.json", "hold_cooperative.json", "hold_hostile.json"
    }
    assert HOLDOUT_LABELS["hold_coercive.json"] is True
    assert HOLDOUT_LABELS["hold_cooperative.json"] is False
    assert HOLDOUT_LABELS["hold_hostile.json"] is False


def test_holdout_corpora_load_and_classify_deterministically():
    for fname in HOLDOUT_LABELS:
        msgs = load_corpus(HOLDOUT / fname)
        assert msgs, f"{fname} is empty"
        first = classify_coercive(msgs)
        second = classify_coercive(msgs)
        assert first == second  # deterministic; value itself is NOT asserted to a target


def test_tiered_report_includes_holdout_line():
    t = evaluate_tiered(DATA)
    assert t.holdout is not None
    assert "holdout" in format_tiered_report(t).lower()
