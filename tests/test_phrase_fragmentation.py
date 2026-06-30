"""Layer 5 - fragment-level analysis: register anomalies + recurring phrases."""
from convergence.corpus import Message
from convergence.layers.phrase_fragmentation import detect_register_anomalies, recurring_phrases


def _msg(seq, sender, body):
    return Message(seq=seq, thread="T", sender=sender, timestamp="t", domain="d", body=body)


def test_formal_outlier_flagged():
    msgs = [
        _msg(1, "Morgan", "hey can you start it soon"),
        _msg(2, "Morgan", "sounds good thanks"),
        _msg(3, "Morgan", "ok cool see you then"),
        _msg(4, "Morgan", "Pursuant to the policy I am not approving authorization of the review."),
    ]
    res = detect_register_anomalies(msgs)
    assert any(a.seq == 4 for a in res)


def test_consistent_sender_no_anomaly():
    msgs = [_msg(1, "Sam", "hey there"), _msg(2, "Sam", "hey again"), _msg(3, "Sam", "hey once more")]  # noqa: E501
    assert detect_register_anomalies(msgs) == []


def test_single_message_sender_skipped():
    msgs = [_msg(1, "Solo", "Pursuant to the policy authorize the review.")]
    assert detect_register_anomalies(msgs) == []


def test_recurring_bigram_counted():
    msgs = [_msg(1, "A", "extra hours please"), _msg(2, "A", "more extra hours")]
    rp = recurring_phrases(msgs, n=2, min_count=2)
    assert any(p.ngram == ("extra", "hours") and p.count == 2 and set(p.seqs) == {1, 2} for p in rp)


def test_determinism_two_runs_identical():
    msgs = [
        _msg(1, "Morgan", "hey can you start it soon"),
        _msg(2, "Morgan", "sounds good thanks"),
        _msg(3, "Morgan", "Pursuant to the policy I am not approving authorization of the review."),
    ]
    assert detect_register_anomalies(msgs) == detect_register_anomalies(msgs)


def test_identical_messages_do_not_crash_or_flag():
    msgs = [_msg(1, "A", "same words here"), _msg(2, "A", "same words here")]
    assert detect_register_anomalies(msgs) == []
