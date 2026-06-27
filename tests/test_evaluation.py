"""Scored evaluation of the coercion-grammar discriminator.

Turns the pass/fail discrimination tests into metrics: precision, recall, F1,
specificity, accuracy over the labeled dynamics corpora (coercive = positive).
Per the eval posts, the report also surfaces the *hard negative* - high-conflict,
which is hostile (many stage-hits) yet must stay a true negative. Synthetic only.
"""
from convergence.corpus import Message
from convergence.evaluation import classify_coercive, metrics, evaluate, format_report

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
    assert m["precision"] == 1.0 and m["recall"] == 1.0 and m["f1"] == 1.0 and m["specificity"] == 1.0


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
