"""Layer 2 — cross-corpus reconstruction ("frog DNA").

The signal is not that messages are missing (excerpting is normal) but *where*:
a message cut from the middle of one continuous conversation is a within-thread
omission — the kind that changes meaning — versus an ordinary boundary trim.
"""
from convergence.corpus import Message
from convergence.layers.gap_detector import find_omissions


def _msg(seq, thread):
    return Message(seq=seq, thread=thread, sender="x", timestamp="t", domain="d", body="b")


def test_finds_omitted_sequence_numbers():
    full = [_msg(1, "A"), _msg(2, "A"), _msg(3, "A"), _msg(4, "A")]
    gaps = find_omissions(full, included_seqs=[1, 2, 4])
    assert [g.seq for g in gaps] == [3]


def test_flags_within_thread_cut_with_neighbors():
    full = [_msg(1, "A"), _msg(2, "A"), _msg(3, "A"), _msg(4, "A")]
    gap = find_omissions(full, [1, 2, 4])[0]
    assert gap.within_thread is True
    assert gap.prev_seq == 2
    assert gap.next_seq == 4


def test_boundary_cut_is_not_flagged():
    # seq 3 (thread A) omitted; nearest shown before is 2 (A), after is 4 (B).
    full = [_msg(1, "A"), _msg(2, "A"), _msg(3, "A"), _msg(4, "B")]
    gap = find_omissions(full, [1, 2, 4])[0]
    assert gap.within_thread is False


def test_no_omissions_returns_empty():
    full = [_msg(1, "A"), _msg(2, "A")]
    assert find_omissions(full, [1, 2]) == []
