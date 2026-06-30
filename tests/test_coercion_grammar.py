"""The coercion grammar: 1 Action -> [(2 objection <-> 3 obstruction) <->
(4 question <-> 5 justify)]^n -> 6 fait accompli.

Two products. tag_stages labels each message with the coercion stage(s) it
expresses. match_grammar recognizes the *envelope* within a thread: a legitimate
action, met with sustained refusal/legitimacy cycles, terminating in a fait
accompli. Synthetic inputs only.
"""
from pathlib import Path

from convergence.coercion_grammar import STAGES, match_grammar, tag_stages
from convergence.corpus import Message

_ROOT = Path(__file__).parent.parent


def _msg(seq, body, sender="Sam", thread="swap"):
    return Message(seq=seq, thread=thread, sender=sender, timestamp="t", domain="d", body=body)


# --- stage tagging ---------------------------------------------------------

def test_action_stage():
    hits = tag_stages([_msg(1, "Can we confirm I'm taking her this weekend like we agreed?")])
    assert any(h.stage == 1 and h.name == "action" for h in hits)


def test_objection_stage():
    assert any(h.stage == 2 for h in tag_stages([_msg(1, "I don't agree that this weekend works.")]))  # noqa: E501


def test_obstruction_stage():
    assert any(h.stage == 3 for h in tag_stages([_msg(1, "Let's just talk about this later, I'll get back to you.")]))  # noqa: E501


def test_question_stage():
    assert any(h.stage == 4 for h in tag_stages([_msg(1, "On what basis are you assuming you get this weekend?")]))  # noqa: E501


def test_justify_stage():
    assert any(h.stage == 5 for h in tag_stages([_msg(1, "I'm only trying to protect her, and my lawyer says the schedule stands.")]))  # noqa: E501


def test_fait_accompli_stage():
    assert any(h.stage == 6 for h in tag_stages([_msg(1, "It's already done, there's nothing to discuss.")]))  # noqa: E501


def test_neutral_message_has_no_stage():
    assert tag_stages([_msg(1, "Thanks, see you Saturday at five.")]) == []


def test_plain_question_is_not_stage_4():
    # an ordinary logistics question is not the interrogation/doubt move
    assert all(h.stage != 4 for h in tag_stages([_msg(1, "What time is pickup on Saturday?")]))


def test_tag_stages_carries_sender():
    hits = tag_stages([_msg(1, "I don't agree that this weekend works.", sender="Victor")])
    assert hits and all(h.sender == "Victor" for h in hits)


# --- the envelope matcher --------------------------------------------------

def _full_thread():
    return [
        _msg(1, "Can we confirm I'm taking her this weekend like we agreed?", sender="Alex"),
        _msg(2, "I don't agree that this weekend works."),
        _msg(3, "Let's just talk about this later, I'll get back to you."),
        _msg(4, "On what basis are you assuming you get this weekend?"),
        _msg(5, "I'm only trying to protect her, and my lawyer says the schedule stands."),
        _msg(6, "I still don't agree to the swap."),
        _msg(7, "Per the agreement, weekdays are mine."),
        _msg(8, "It's already done - she's staying with me, there's nothing to discuss."),
    ]


def test_complete_envelope_detected():
    m = match_grammar(_full_thread())
    assert len(m) == 1
    assert m[0].complete
    assert m[0].has_action and m[0].has_fait_accompli


def test_cycles_counted():
    # ordered refuse->legitimize rounds: refuse@2->legit@4 (round 1), refuse@6->legit@7 (round 2)
    # refusal@3 and legit@5 are absorbed (no-ops within their states); was min-count 3
    m = match_grammar(_full_thread())
    assert m[0].cycles == 2  # ordered refuse->legitimize rounds (was min-count 3)


def test_fait_accompli_sets_the_status_quo():
    # the war runs *until* step 6; the fait accompli terminates it and marks the
    # seq at which the new status quo is set
    m = match_grammar(_full_thread())
    assert m[0].status_quo_seq == 8


def test_cycles_counted_only_before_the_fait_accompli():
    # cover moves after the status quo is set are not part of the war that produced it
    msgs = _full_thread() + [_msg(9, "And I don't agree to discuss it further.")]
    m = match_grammar(msgs)
    assert m[0].status_quo_seq == 8
    assert m[0].cycles == 2  # seq 9 (after the fait accompli) does not add a cycle


def test_incomplete_without_fait_accompli():
    msgs = [x for x in _full_thread() if x.seq != 8]  # drop the fait accompli
    m = match_grammar(msgs)
    assert m[0].cycles >= 1
    assert not m[0].complete


def test_fait_accompli_alone_is_not_complete():
    m = match_grammar([_msg(1, "It's already done, there's nothing to discuss.")])
    assert len(m) == 1
    assert m[0].has_fait_accompli
    assert not m[0].complete  # no action, no cover cycle


def test_grouped_by_thread():
    msgs = _full_thread() + [
        _msg(20, "Can we confirm the holiday plan?", sender="Alex", thread="holiday"),
        _msg(21, "It's already settled, nothing to discuss.", thread="holiday"),
    ]
    threads = {m.thread for m in match_grammar(msgs)}
    assert threads == {"swap", "holiday"}


def _coercion_thread(coercer="Victor", proposer="Rosa", thread="t"):
    # proposer's action opens it; the coercer runs refuse->legitimize x2 then faits.
    return [
        _msg(1, "Can we decide on preschool together like we agreed?", sender=proposer, thread=thread),  # noqa: E501
        _msg(2, "I don't agree to the ones you picked.", sender=coercer, thread=thread),  # noqa: E501
        _msg(3, "On what basis are you choosing without consulting me?", sender=coercer, thread=thread),  # noqa: E501
        _msg(4, "I still don't agree to your list.", sender=coercer, thread=thread),  # refusal (2)
        _msg(5, "Per the agreement, I have decision-making too.", sender=coercer, thread=thread),  # legitimacy (5)  # noqa: E501
        _msg(6, "It's already done - I enrolled her at Oakwood.", sender=coercer, thread=thread),  # fait (6)  # noqa: E501
    ]


def test_single_coercer_envelope_completes():
    m = match_grammar(_coercion_thread())
    assert len(m) == 1
    assert m[0].complete and m[0].coercer == "Victor"
    assert m[0].cycles >= 1
    assert m[0].has_action and m[0].has_fait_accompli


def test_envelope_split_across_two_senders_does_not_complete():
    # The refusals come from one sender, the legitimacy+fait from another:
    # no single sender owns the ordered refuse->legitimize->fait war.
    msgs = [
        _msg(1, "Can we decide on preschool together like we agreed?", sender="Rosa", thread="t"),  # noqa: E501
        _msg(2, "I don't agree to the ones you picked.", sender="Pat", thread="t"),  # noqa: E501
        _msg(3, "On what basis are you choosing without consulting me?", sender="Victor", thread="t"),  # noqa: E501
        _msg(4, "It's already done - I enrolled her at Oakwood.", sender="Victor", thread="t"),  # fait by Victor  # noqa: E501
    ]
    assert [x for x in match_grammar(msgs) if x.complete] == []


def test_reverse_seq_order_does_not_complete():
    # The same single-coercer cues, but the fait precedes the war precedes the action.
    base = _coercion_thread()
    reversed_seqs = [
        _msg(7 - m.seq, m.body, sender=m.sender, thread=m.thread) for m in base
    ]
    assert [x for x in match_grammar(reversed_seqs) if x.complete] == []


def test_bilateral_hostility_is_not_a_single_coercer_envelope():
    # Both parties refuse and justify; neither runs a lone ordered action->war->fait.
    msgs = [
        _msg(1, "Can we confirm the schedule like we agreed?", sender="Rosa", thread="t"),
        _msg(2, "I don't agree.", sender="Victor", thread="t"),
        _msg(3, "On what basis do you decide?", sender="Rosa", thread="t"),
        _msg(4, "I'm only protecting her, the order stands.", sender="Victor", thread="t"),
        _msg(5, "That's not acceptable.", sender="Rosa", thread="t"),
    ]
    assert [x for x in match_grammar(msgs) if x.complete] == []


# --- doc sync: every stage is documented in all three specs ----------------

def test_every_stage_documented_in_all_specs():
    for doc in ("FRAGMENTS.md", "INTENT.md", "HIERARCHY.md"):
        text = (_ROOT / doc).read_text(encoding="utf-8").lower()
        missing = [s.name for s in STAGES if s.name.replace("_", " ") not in text and s.name not in text]  # noqa: E501
        assert missing == [], f"{doc} missing stages: {missing}"


# --- vocabulary broadening (recall fix) ------------------------------------

def test_bare_first_person_fait_tags_stage6():
    assert any(h.stage == 6 for h in tag_stages([_msg(1, "I enrolled Mia at Bright Beginnings this morning. She starts September 4th.")]))  # noqa: E501


def test_negated_enrolling_does_not_tag_stage6():
    # "I'm not enrolling" (present-continuous, negated) is NOT a fait accompli
    assert all(h.stage != 6 for h in tag_stages([_msg(1, "I'm not enrolling her without you. I'm trying to include you.")]))  # noqa: E501


def test_future_intent_does_not_tag_stage6():
    assert all(h.stage != 6 for h in tag_stages([_msg(1, "I'm going to look at Bright Beginnings this week.")]))  # noqa: E501


def test_per_the_parenting_plan_tags_stage5():
    assert any(h.stage == 5 for h in tag_stages([_msg(1, "Per the parenting plan, major decisions require my agreement.")]))  # noqa: E501


def test_de_adjacent_authority_tags_stage5():
    assert any(h.stage == 5 for h in tag_stages([_msg(1, "I talked to my attorney and she said this is my call.")]))  # noqa: E501


def test_i_dont_think_x_is_right_tags_stage2():
    assert any(h.stage == 2 for h in tag_stages([_msg(1, "I don't think Montessori is the right approach for Mia.")]))  # noqa: E501


def test_scoped_soft_doubt_tags_stage2():
    assert any(h.stage == 2 for h in tag_stages([_msg(1, "I'm not really sure about that place. I don't know anything about it.")]))  # noqa: E501


def test_bare_dont_know_does_not_tag_stage2():
    # bare uncertainty is benign and must NOT be an objection
    assert all(h.stage != 2 for h in tag_stages([_msg(1, "I don't know. Let me check and get back to you.")]))  # noqa: E501


def test_bare_not_sure_does_not_tag_stage2():
    assert all(h.stage != 2 for h in tag_stages([_msg(1, "I'm not sure. Either day works for me though.")]))  # noqa: E501
