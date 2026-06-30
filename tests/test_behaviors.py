"""Verified behavior detectors - the families that survived the investigator.

triangulation (child as messenger/informant) and derogation (contempt via
attribution) shipped because they fired on their target dynamic types without
false-firing on the benign corpora. access_gatekeeping did NOT ship, so it is
absent here. Synthetic only.
"""
from convergence.behaviors import tag_behaviors
from convergence.corpus import Message


def _msg(seq, body):
    return Message(seq=seq, thread="t", sender="X", timestamp="t", domain="d", body=body)


def test_detects_triangulation():
    hits = tag_behaviors([_msg(1, "Sofia told me you were out late.")])
    assert any(h.behavior == "triangulation" for h in hits)


def test_detects_derogation():
    hits = tag_behaviors([_msg(1, "As usual, you forgot the inhaler.")])
    assert any(h.behavior == "derogation" for h in hits)


def test_detects_isolation():
    hits = tag_behaviors([_msg(1, "This is exactly the alienation I've been telling everyone about.")])  # noqa: E501
    assert any(h.behavior == "isolation" for h in hits)


def test_detects_surveillance_framing():
    hits = tag_behaviors([_msg(1, "Where were you Saturday night?")])
    assert any(h.behavior == "surveillance_framing" for h in hits)


def test_silent_on_benign():
    assert tag_behaviors([_msg(1, "Pickup at 5, thanks!"), _msg(2, "Sounds good.")]) == []


def test_rejected_family_absent():
    from convergence.behaviors import _SHIPPED
    names = {n for n, _ in _SHIPPED}
    assert "triangulation" in names and "derogation" in names
    assert "access_gatekeeping" not in names  # verifier rejected it


def test_sorted_by_seq():
    hits = tag_behaviors([_msg(3, "typical."), _msg(1, "she told me you lied.")])
    assert [h.seq for h in hits] == [1, 3]
