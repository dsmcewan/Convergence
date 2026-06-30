"""Layer 1 - communicative-tactic detection (borrow-authority / displace-accountability)."""
from convergence.corpus import Message
from convergence.layers.pattern_detector import detect_patterns


def _msg(seq, body):
    return Message(seq=seq, thread="T", sender="x", timestamp="t", domain="d", body=body)


def test_platform_policy_says_fires():
    hits = detect_patterns([_msg(5, "The platform's billing policy says revisions are included, so I won't be approving extra hours.")])  # noqa: E501
    assert len(hits) == 1
    assert hits[0].tactic == "borrow_authority"
    assert hits[0].seq == 5
    assert hits[0].authority is not None


def test_accountant_says_fires():
    hits = detect_patterns([_msg(12, "My accountant says I only owe the original quote.")])
    assert [h.tactic for h in hits] == ["borrow_authority"]


def test_direct_factual_statement_does_not_fire():
    # Mentions 'policy' but asserts the fact directly and offers the document;
    # no authority bound to an assertion verb. This boundary must hold.
    hits = detect_patterns([_msg(6, "Revisions are included; new scope isn't. I can send you the policy section if helpful.")])  # noqa: E501
    assert hits == []


def test_neutral_message_no_hit():
    hits = detect_patterns([_msg(1, "Can we make the homepage hero full-width? The client loves the mockup.")])  # noqa: E501
    assert hits == []


def test_one_hit_per_message_per_tactic():
    hits = detect_patterns([_msg(5, "The platform policy says X and the accountant says Y.")])
    assert len([h for h in hits if h.seq == 5 and h.tactic == "borrow_authority"]) == 1


def test_sorted_by_seq():
    hits = detect_patterns([
        _msg(12, "My accountant says I owe less."),
        _msg(5, "The policy says no."),
    ])
    assert [h.seq for h in hits] == [5, 12]
