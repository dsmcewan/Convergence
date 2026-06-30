"""Adversarial corpora: engineered to fool a stage-COUNTER but not the Phase-2
ordered, sender-aware machine. Three negatives must stay true negatives (no false
envelope); two robustness positives must stay true positives (a genuine envelope
survives interleaving and off-subject noise). Plus the core-tier regression guard:
the five dynamics corpora must still classify perfectly. Synthetic only.
"""
from pathlib import Path

from convergence.corpus import load_corpus
from convergence.evaluation import (
    ADVERSARIAL_LABELS,
    classify_coercive,
    evaluate_tiered,
)

DATA = Path(__file__).parent.parent / "data"

# ground truth, mirrored from the spec's adversarial table
EXPECTED = {
    "adv_mixed_senders.json": False,
    "adv_reversed_chronology.json": False,
    "adv_unrelated_contamination.json": False,
    "adv_interleaved_threads.json": True,
    "adv_subject_mismatch.json": True,
}


def test_labels_match_spec():
    assert ADVERSARIAL_LABELS == EXPECTED


def test_each_adversarial_corpus_classifies_correctly():
    for fname, expected in EXPECTED.items():
        msgs = load_corpus(DATA / fname)
        assert classify_coercive(msgs) is expected, f"{fname} misclassified"


def test_interleaved_positive_fires_on_its_own_thread_only():
    # the genuine envelope is in 'school'; stray cues live in other threads and
    # must NOT be stitched into a cross-thread envelope
    from convergence.coercion_grammar import match_grammar
    msgs = load_corpus(DATA / "adv_interleaved_threads.json")
    complete = [m for m in match_grammar(msgs) if m.complete]
    assert [m.thread for m in complete] == ["school"]
    assert all(m.coercer == "Victor" for m in complete)


def test_tiered_eval_core_is_perfect_and_adversarial_scores():
    t = evaluate_tiered(DATA)
    # core tier: the behavior-preservation guard — all 5 dynamics corpora correct
    assert t.core.fp == 0 and t.core.fn == 0
    assert t.core.metrics["precision"] == 1.0 and t.core.metrics["recall"] == 1.0
    # adversarial tier: 2 positives, 3 negatives, all correct -> no FP, no FN
    assert (t.adversarial.tp, t.adversarial.fp, t.adversarial.fn, t.adversarial.tn) == (2, 0, 0, 3)
    # holdout not wired until T3
    assert t.holdout is None
