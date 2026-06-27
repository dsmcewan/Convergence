"""The investigator's deterministic verifier.

An agent (or a seed list) PROPOSES a candidate fragment family; this verifier
DECIDES whether it ships - by adversarially testing it against the labeled corpora.
A candidate ships only if it fires on its target type(s) and does NOT over-fire on
the clearly-benign corpora. The agent never grades its own homework. Synthetic only.
"""
from convergence.corpus import Message
from convergence.investigator import Candidate, verify


def _msg(seq, body, sender="X"):
    return Message(seq=seq, thread="t", sender=sender, timestamp="t", domain="d", body=body)


_TARGET = {  # the type the candidate should fire on
    "conflicted": [_msg(1, "As usual he forgot her inhaler."),
                   _msg(2, "Typical, you didn't tell me about the dentist."),
                   _msg(3, "Lily said you were out late.")],
}
_BENIGN = {
    "cooperative": [_msg(1, "Pickup at 5, thanks!"), _msg(2, "Sounds good, see you then.")],
    "parallel": [_msg(1, "Confirmed."), _msg(2, "Noted.")],
}


def test_ships_a_good_candidate():
    c = Candidate(name="derogation", target_types=("conflicted",),
                  pattern=r"\b(as usual|as always|typical|clearly)\b")
    v = verify(c, {**_TARGET, **_BENIGN})
    assert v.fires_on_target >= 1
    assert v.false_positives == 0
    assert v.ship is True


def test_rejects_overfiring_candidate():
    # matches common words -> fires everywhere, including benign -> reject
    c = Candidate(name="greedy", target_types=("conflicted",), pattern=r"\b(you|the|her)\b")
    v = verify(c, {**_TARGET, **_BENIGN})
    assert v.false_positives > 0
    assert v.ship is False


def test_rejects_silent_candidate():
    # never fires on the target -> nothing to ship
    c = Candidate(name="silent", target_types=("conflicted",), pattern=r"\bzxqv-never-matches\b")
    v = verify(c, {**_TARGET, **_BENIGN})
    assert v.fires_on_target == 0
    assert v.ship is False


def test_verdict_reports_per_corpus_counts():
    c = Candidate(name="triangulation", target_types=("conflicted",),
                  pattern=r"\b(said|told me) you\b")
    v = verify(c, {**_TARGET, **_BENIGN})
    assert "conflicted" in v.per_corpus
    assert v.per_corpus["cooperative"] == 0
