"""Layer 6 - cross-channel correlation.

A *claim* made by a sender in the primary channel is tested against that same
sender's *recorded admissions* in a second channel. When the favorable claim
("I always kept you informed") diverges from the sender's own words in the other
channel ("forgot to tell you..."), the divergence is flagged on the primary-channel
message and points back at the contradicting cross-channel message. Alignment is
by sender AND predicate; a divergence is never invented when the cross channel is
silent or consistent. Synthetic inputs only.
"""
from convergence.corpus import Message
from convergence.layers.cross_channel import find_cross_channel_divergences


def _msg(seq, sender, body, domain="d", thread="T"):
    return Message(seq=seq, thread=thread, sender=sender, timestamp="t", domain=domain, body=body)


def test_claim_contradicted_by_other_channel_points_to_cross_seq():
    primary = [_msg(2, "A", "I have always kept you fully informed of every appointment.")]
    cross = [_msg(7, "A", "honestly I forgot to tell you about the dentist.")]
    d = find_cross_channel_divergences(primary, cross)
    assert len(d) == 1
    assert d[0].seq == 2
    assert d[0].cross_seq == 7
    assert d[0].sender == "A"
    assert d[0].predicate == "kept_informed"


def test_different_sender_in_cross_channel_does_not_diverge():
    # alignment is by sender: B's admission cannot impeach A's claim
    primary = [_msg(2, "A", "I have always kept you fully informed of every appointment.")]
    cross = [_msg(7, "B", "honestly I forgot to tell you about the dentist.")]
    assert find_cross_channel_divergences(primary, cross) == []


def test_silent_or_consistent_cross_channel_emits_nothing():
    primary = [_msg(2, "A", "I have always kept you fully informed of every appointment.")]
    cross = [_msg(7, "A", "thanks for confirming, see you saturday.")]
    assert find_cross_channel_divergences(primary, cross) == []


def test_non_claim_primary_message_ignored():
    primary = [_msg(2, "A", "pickup is at five on saturday.")]
    cross = [_msg(7, "A", "honestly I forgot to tell you about the dentist.")]
    assert find_cross_channel_divergences(primary, cross) == []


def test_second_predicate_payment():
    primary = [_msg(4, "A", "I have always paid every expense on time.")]
    cross = [_msg(9, "A", "yeah I skipped paying the copay last month.")]
    d = find_cross_channel_divergences(primary, cross)
    assert len(d) == 1
    assert d[0].predicate == "paid_ontime"
    assert d[0].seq == 4 and d[0].cross_seq == 9


def test_sorted_by_seq_then_predicate():
    primary = [
        _msg(4, "A", "I have always paid every expense on time."),
        _msg(2, "A", "I have always kept you fully informed of every appointment."),
    ]
    cross = [
        _msg(7, "A", "honestly I forgot to tell you about the dentist."),
        _msg(9, "A", "yeah I skipped paying the copay last month."),
    ]
    d = find_cross_channel_divergences(primary, cross)
    assert [x.seq for x in d] == [2, 4]


def test_first_matching_cross_message_is_cited():
    primary = [_msg(2, "A", "I have always kept you fully informed of every appointment.")]
    cross = [
        _msg(9, "A", "didn't tell you about the new doctor."),
        _msg(7, "A", "honestly I forgot to tell you about the dentist."),
    ]
    d = find_cross_channel_divergences(primary, cross)
    assert len(d) == 1
    assert d[0].cross_seq == 7  # earliest cross-channel admission by that sender
