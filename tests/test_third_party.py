"""Layer 3 - claims tested against external records."""
from convergence.corpus import Message
from convergence.layers.third_party import check_claims
from convergence.records import Record


def _msg(seq, body):
    return Message(seq=seq, thread="T", sender="x", timestamp="t", domain="d", body=body)


def _rec(rid, predicate, value, source_seq):
    return Record(id=rid, subject="s", predicate=predicate, value=value, source_seq=source_seq, note="n")  # noqa: E501


def test_denial_contradicted_by_record_points_to_source():
    msgs = [_msg(10, "I never agreed to extra hours.")]
    recs = [_rec("R1", "agreed_to_extra_hours", True, 3)]
    c = check_claims(msgs, recs)
    assert len(c) == 1
    assert c[0].seq == 10
    assert c[0].record_id == "R1"
    assert c[0].contradicting_seq == 3


def test_no_matching_record_emits_nothing():
    msgs = [_msg(10, "I never agreed to extra hours.")]
    recs = [_rec("R9", "agreed_to_weekend_swap", True, 3)]  # different topic
    assert check_claims(msgs, recs) == []


def test_record_consistent_with_claim_emits_nothing():
    msgs = [_msg(10, "I never agreed to extra hours.")]
    recs = [_rec("R1", "agreed_to_extra_hours", False, 3)]  # record agrees they didn't agree
    assert check_claims(msgs, recs) == []


def test_non_claim_message_ignored():
    msgs = [_msg(2, "Full-width works, adds about 3 hours.")]
    recs = [_rec("R1", "agreed_to_extra_hours", True, 3)]
    assert check_claims(msgs, recs) == []


def test_sorted_by_seq():
    msgs = [_msg(10, "I never agreed to extra hours."), _msg(8, "I never agreed to extra hours.")]
    recs = [_rec("R1", "agreed_to_extra_hours", True, 3)]
    assert [x.seq for x in check_claims(msgs, recs)] == [8, 10]
