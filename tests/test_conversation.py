"""Conversational seam: detection stays deterministic; the model only explains."""
from convergence.conversation import Conversation, to_prompt
from convergence.corpus import Message
from convergence.engine import run_engine


def _msg(seq, sender, body):
    return Message(seq=seq, thread="T", sender=sender, timestamp="t", domain="d", body=body)


_TWO_LAYER = [
    _msg(1, "M", "hey start it soon thanks"),
    _msg(2, "M", "my accountant says I am not approving the authorization pursuant to policy"),
]


def test_ask_routes_through_injected_complete():
    conv = Conversation(run_engine(_TWO_LAYER), complete=lambda p: "STUB:" + str(len(p)))
    assert conv.ask("why is seq 2 flagged?").startswith("STUB:")


def test_prompt_is_grounded_in_findings():
    captured = {}
    conv = Conversation(run_engine(_TWO_LAYER), complete=lambda p: captured.setdefault("p", p) or "ok")  # noqa: E501
    conv.ask("explain seq 2")
    p = captured["p"]
    assert "ELEVATED" in p          # the fixed verdict is in the prompt
    assert "L1" in p                # the contributing layers
    assert "explain seq 2" in p     # the question is appended


def test_to_prompt_lists_confidence():
    res = run_engine([_msg(1, "A", "my accountant says I owe less")])
    assert "LOW" in to_prompt(res)


def test_blanc_persona_rides_on_top_of_grounding():
    from convergence.conversation import BLANC_PERSONA
    captured = {}
    conv = Conversation(run_engine(_TWO_LAYER),
                        complete=lambda p: captured.setdefault("p", p) or "ok",
                        persona=BLANC_PERSONA)
    conv.ask("who is the controlling party?")
    p = captured["p"]
    assert "Benoit Blanc" in p                 # the voice is requested
    assert "never change a finding's confidence" in p  # grounding still dominates
    assert "ELEVATED" in p                     # the fixed verdict is still present


def test_no_persona_by_default():
    captured = {}
    Conversation(run_engine(_TWO_LAYER),
                 complete=lambda p: captured.setdefault("p", p) or "ok").ask("q")
    assert "Benoit Blanc" not in captured["p"]
