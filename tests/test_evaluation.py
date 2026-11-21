"""Scored evaluation of the coercion-grammar discriminator.

Turns the pass/fail discrimination tests into metrics: precision, recall, F1,
specificity, accuracy over the labeled dynamics corpora (coercive = positive).
Per the eval posts, the report also surfaces the *hard negative* - high-conflict,
which is hostile (many stage-hits) yet must stay a true negative. Synthetic only.
"""
from convergence.corpus import Message
from convergence.evaluation import classify_coercive, evaluate, format_report, metrics

DATA = __import__("pathlib").Path(__file__).parent.parent / "data"


def _msg(seq, body, thread="t", sender="X"):
    return Message(seq=seq, thread=thread, sender=sender, timestamp="t", domain="d", body=body)


_ENVELOPE = [
    _msg(1, "Can we confirm the schedule like we agreed?"),
    _msg(2, "I don't agree to that."),
    _msg(3, "Let's talk about this later, I'll get back to you."),
    _msg(4, "On what basis are you assuming that?"),
    _msg(5, "I'm only trying to help, and my lawyer says I have a say."),
    _msg(6, "It's already done, there's nothing to discuss."),
]
_BENIGN = [_msg(1, "Pickup at 5, thanks!"), _msg(2, "Sounds good.")]


def test_metrics_perfect():
    m = metrics(tp=1, fp=0, fn=0, tn=4)
    assert m["precision"] == 1.0 and m["recall"] == 1.0 and m["f1"] == 1.0 and m["specificity"] == 1.0  # noqa: E501


def test_metrics_with_errors():
    m = metrics(tp=2, fp=1, fn=1, tn=6)
    assert round(m["precision"], 3) == 0.667
    assert round(m["recall"], 3) == 0.667
    assert round(m["f1"], 3) == 0.667
    assert round(m["specificity"], 3) == round(6 / 7, 3)


def test_classify_detects_envelope_only():
    assert classify_coercive(_ENVELOPE) is True
    assert classify_coercive(_BENIGN) is False


def test_evaluate_confusion_and_metrics():
    r = evaluate([("pos", _ENVELOPE, True), ("neg", _BENIGN, False)])
    assert (r.tp, r.fp, r.fn, r.tn) == (1, 0, 0, 1)
    assert r.metrics["precision"] == 1.0 and r.metrics["recall"] == 1.0


def test_report_mentions_metrics():
    txt = format_report(evaluate([("pos", _ENVELOPE, True), ("neg", _BENIGN, False)]))
    assert "precision" in txt.lower() and "recall" in txt.lower()


def test_real_dynamics_eval_is_perfect_with_hard_negative():
    from convergence.evaluation import evaluate_dynamics
    r = evaluate_dynamics(DATA)
    assert r.metrics["precision"] == 1.0 and r.metrics["recall"] == 1.0 and r.metrics["f1"] == 1.0
    hc = next(c for c in r.per_corpus if c.name == "high_conflict")
    assert hc.stage_hits > 0 and hc.predicted is False  # hostile, correctly negative


def test_documentary_precision_counts_findings_not_messages():
    from convergence.evaluation import documentary_precision
    # Three elevated findings; corroborated set = {10, 99}.
    # f1 [10,11] -> hit (10); f2 [20,21] -> miss; f3 [99] -> hit.
    dp = documentary_precision([(10, 11), (20, 21), (99,)], {10, 99})
    assert dp.elevated == 3
    assert dp.corroborated == 2
    assert dp.precision == 2 / 3
    assert dp.corroboration_pool == 2
    assert dp.uncorroborated_seqs == (20, 21)


def test_documentary_precision_empty_is_zero_not_crash():
    from convergence.evaluation import documentary_precision
    dp = documentary_precision([], {1, 2})
    assert dp.elevated == 0 and dp.precision == 0.0


def test_report_is_reframed_as_corpus_level_with_caveat():
    from convergence.evaluation import format_report
    txt = format_report(evaluate([("pos", _ENVELOPE, True), ("neg", _BENIGN, False)]))
    low = txt.lower()
    # honest framing: corpus-level, explicit count, no-generalization caveat
    assert "corpus" in low
    assert "2/2" in txt  # k/N corpora correctly classified
    assert "no statistical generalization" in low or "not a sampled population" in low
    # diagnostics still present (keys unchanged)
    assert "precision" in low and "recall" in low


def test_tiered_report_names_each_tier():
    from convergence.evaluation import evaluate_tiered, format_tiered_report
    DATA = __import__("pathlib").Path(__file__).parent.parent / "data"
    txt = format_tiered_report(evaluate_tiered(DATA)).lower()
    assert "core" in txt and "adversarial" in txt


# ---- Scoring with real errors. Every earlier test fed the scorer only correct predictions, so the
# false-positive and false-negative branches, the accuracy formula and the report's error markers
# were never exercised.
_ONE_OF_EACH = [("tp", _ENVELOPE, True), ("fn", _BENIGN, True),
                ("fp", _ENVELOPE, False), ("tn", _BENIGN, False)]


def test_evaluate_counts_each_kind_of_error_once():
    r = evaluate(_ONE_OF_EACH)
    assert (r.tp, r.fp, r.fn, r.tn) == (1, 1, 1, 1)
    assert [(c.name, c.label, c.predicted, c.correct) for c in r.per_corpus] == [
        ("tp", True, True, True), ("fn", True, False, False),
        ("fp", False, True, False), ("tn", False, False, True)]
    assert [c.envelopes for c in r.per_corpus] == [1, 0, 1, 0]
    assert r.metrics == {"precision": 0.5, "recall": 0.5, "f1": 0.5,
                         "specificity": 0.5, "accuracy": 0.5}


def test_metrics_exact_values_for_an_asymmetric_confusion():
    m = metrics(tp=3, fp=1, fn=2, tn=4)
    assert m["precision"] == 0.75
    assert m["recall"] == 0.6
    assert round(m["f1"], 6) == round(2 * 0.75 * 0.6 / (0.75 + 0.6), 6)
    assert m["specificity"] == 0.8
    assert m["accuracy"] == 0.7


def test_metrics_with_an_empty_denominator_are_zero_not_an_error():
    zeros = {"precision": 0.0, "recall": 0.0, "f1": 0.0, "specificity": 0.0, "accuracy": 0.0}
    assert metrics(0, 0, 0, 0) == zeros
    only_negatives = metrics(0, 0, 0, 5)
    assert only_negatives["recall"] == 0.0
    assert (only_negatives["specificity"], only_negatives["accuracy"]) == (1.0, 1.0)


def test_report_marks_the_wrong_predictions_and_shows_the_confusion():
    txt = format_report(evaluate(_ONE_OF_EACH))
    assert "2/4 corpora correctly classified" in txt
    assert "confusion:  TP=1  FP=1  FN=1  TN=1" in txt
    names = (["tp"], ["fn"], ["fp"], ["tn"])
    rows = {line.split()[0]: line.split()[1:] for line in txt.splitlines()
            if line.split()[:1] in names}
    assert rows["tp"][:2] == ["coercive", "coercive"] and rows["tp"][-1] == "y"
    assert rows["fn"][:2] == ["coercive", "other"] and rows["fn"][-1] == "N"
    assert rows["fp"][:2] == ["other", "coercive"] and rows["fp"][-1] == "N"
    assert rows["tn"][:2] == ["other", "other"] and rows["tn"][-1] == "y"
    assert ("precision=0.500  recall=0.500  F1=0.500  specificity=0.500  accuracy=0.500"
            in txt)


def test_report_names_the_hardest_negative_and_its_false_envelopes():
    txt = format_report(evaluate(_ONE_OF_EACH))
    # Of the two negatives, "fp" fires the envelope (and the most stage hits); "tn" fires none.
    assert "hard negative: 'fp' fired" in txt
    assert "but 1 false envelopes" in txt
    only_positive = format_report(evaluate([("pos", _ENVELOPE, True)]))
    assert "hard negative" not in only_positive


def test_corpus_label_strips_only_the_known_tier_prefixes():
    from convergence.evaluation import _corpus_label
    assert _corpus_label("dyn_coercive.json") == "coercive"
    assert _corpus_label("adv_mixed_senders.json") == "mixed_senders"
    assert _corpus_label("hold_hostile.json") == "hostile"
    # The regression tier is not stripped: its files keep their prefix.
    assert _corpus_label("reg_coercive.json") == "reg_coercive"
    assert _corpus_label("plain.json") == "plain"


def test_tiered_report_includes_the_optional_tiers_only_when_present():
    from convergence.evaluation import TieredEval, format_tiered_report
    tier = evaluate([("pos", _ENVELOPE, True), ("neg", _BENIGN, False)])
    full = format_tiered_report(
        TieredEval(core=tier, adversarial=tier, regression=tier, holdout=tier))
    assert full.count("2/2 corpora correctly classified") == 4
    assert "REGRESSION (known; asserted" in full and "HOLDOUT (blind" in full
    bare = format_tiered_report(
        TieredEval(core=tier, adversarial=tier, regression=None, holdout=None))
    assert bare.count("2/2 corpora correctly classified") == 2
    assert "REGRESSION" not in bare and "HOLDOUT" not in bare


def test_documentary_precision_report_states_its_numbers_and_claims_no_recall():
    from convergence.evaluation import documentary_precision, format_documentary_precision
    dp = documentary_precision([(10, 11), (20, 21), (99,)], {10, 99})
    txt = format_documentary_precision(dp, "a corpus")
    assert "elevated findings examined : 3" in txt
    assert "independently corroborated : 2" in txt
    assert "documentary anchor pool    : 2 messages" in txt
    assert "PRECISION (corroborated/elevated) = 0.667" in txt
    assert "NO\n  recall is claimed" in txt


def test_accuracy_is_defined_whenever_any_corpus_was_scored():
    # Each of these has a non-empty confusion matrix whose naive partial sums can cancel to zero.
    assert metrics(1, 0, 0, 1)["accuracy"] == 1.0
    assert metrics(1, 0, 1, 0)["accuracy"] == 0.5
    assert metrics(0, 1, 1, 0)["accuracy"] == 0.0
    assert metrics(2, 1, 0, 3)["accuracy"] == 5 / 6
    assert metrics(1, 1, 0, 0)["accuracy"] == 0.5


def test_documentary_precision_counts_a_finding_once_if_any_of_its_messages_is_anchored():
    from convergence.evaluation import documentary_precision
    dp = documentary_precision([(10, 11), (20, 21), (99,), (30,)], {10, 99})
    assert (dp.elevated, dp.corroborated) == (4, 2)
    assert dp.precision == 0.5
    assert dp.uncorroborated_seqs == (20, 21, 30)


def test_scores_and_results_are_immutable_records():
    import dataclasses

    import pytest
    r = evaluate([("pos", _ENVELOPE, True)])
    with pytest.raises(dataclasses.FrozenInstanceError):
        r.tp = 9  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        r.per_corpus[0].correct = False  # type: ignore[misc]
    from convergence.evaluation import TieredEval, documentary_precision
    tiered = TieredEval(core=r, adversarial=r, regression=None, holdout=None)
    with pytest.raises(dataclasses.FrozenInstanceError):
        tiered.core = None  # type: ignore[misc,assignment]
    with pytest.raises(dataclasses.FrozenInstanceError):
        documentary_precision([(1,)], {1}).elevated = 0  # type: ignore[misc]
