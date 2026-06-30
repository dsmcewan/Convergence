"""Deterministic narration of engine findings."""
from convergence.composition import Campaign, Pattern
from convergence.corpus import Message
from convergence.engine import run_engine
from convergence.narration import TemplateNarrator, narrate, narrate_composition


def _msg(seq, sender, body):
    return Message(seq=seq, thread="T", sender=sender, timestamp="t", domain="d", body=body)


_TWO_LAYER = [
    _msg(1, "M", "hey start it soon thanks"),
    _msg(2, "M", "my accountant says I am not approving the authorization pursuant to policy"),
]


def test_narrates_elevated_with_seqs_and_layers():
    text = narrate(run_engine(_TWO_LAYER))
    assert "ELEVATED" in text
    assert "L1" in text and "2" in text


def test_low_marked_not_corroborated():
    res = run_engine([_msg(1, "A", "my accountant says I owe less")])
    assert "not corroborated" in narrate(res)


def test_empty_says_no_findings():
    res = run_engine([_msg(1, "A", "hello there friend"), _msg(2, "A", "hi again friend")])
    assert "No findings" in narrate(res)


def test_deterministic_across_runs():
    res = run_engine(_TWO_LAYER)
    assert narrate(res) == narrate(res)


def test_default_narrator_is_template():
    res = run_engine([_msg(1, "A", "my accountant says I owe less")])
    assert narrate(res) == TemplateNarrator().narrate(res)


# --- composition narration (patterns + campaigns) --------------------------

def test_composition_narration_lists_patterns_and_campaigns():
    pats = [
        Pattern("sanitize-record", "template", (3, 10), "contradiction + omission combine"),
        Pattern("repeated:borrow_authority", "recurrence", (8, 10, 13), "borrow_authority recurs across 3 messages"),  # noqa: E501
    ]
    camps = [Campaign("Sam", "medical", ("repeated:borrow_authority",), ((8,), (10,)),
                      (8, 10), ("t1", "t2"), "Sam sustains 2 elevated findings against 'medical'")]
    text = narrate_composition(pats, camps)
    assert "sanitize-record" in text
    assert "repeated:borrow_authority" in text
    assert "Sam sustains 2 elevated findings" in text


def test_composition_narration_empty():
    assert "No patterns" in narrate_composition([], [])


# --- the Benoit Blanc voice (presentation only; never moves a verdict) ------

def test_blanc_is_grounded_and_voiced():
    from convergence.narration import BlancNarrator
    text = BlancNarrator().narrate(run_engine(_TWO_LAYER))
    assert "2" in text                       # grounded: the seq
    assert "L1" in text                      # grounded: the layer
    assert "converge" in text.lower() or "hunch" in text.lower()  # the voice


def test_blanc_preserves_the_verdict():
    # voice is presentation: the elevated seqs Blanc reports must equal the engine's
    res = run_engine(_TWO_LAYER)
    blanc = __import__("convergence.narration", fromlist=["BlancNarrator"]).BlancNarrator().narrate(res)  # noqa: E501
    for f in res.findings:
        if f.confidence == "elevated":
            assert str(list(f.seqs)) in blanc


def test_blanc_explains_what_it_is_and_does():
    from convergence.narration import BlancNarrator
    txt = BlancNarrator().explain()
    low = txt.lower()
    assert "converge" in low                       # the core rule
    assert "footprint" in low                      # footprints, not the foot
    assert "campaign" in low and "fait accompli" in low  # the shapes it knows
    assert "donut" in low                          # nah, what we got here... is a donut
    assert BlancNarrator().explain() == BlancNarrator().explain()  # deterministic


def test_blanc_quotes_the_fragment_when_given_messages():
    from convergence.narration import BlancNarrator
    msgs = _TWO_LAYER
    text = BlancNarrator(msgs).narrate(run_engine(msgs))
    assert '"' in text                                   # a line is quoted
    assert "approving the authorization" in text         # the actual message body, quoted
    assert "*accountant says*" in text                   # the NLP fragment, highlighted


def test_blanc_dates_a_self_contradiction():
    from convergence.engine import EngineResult, Finding, Signal
    from convergence.narration import BlancNarrator
    msgs = [
        Message(seq=1, thread="T", sender="Sam", timestamp="2025-04-07T08:41", domain="d",
                body="ok, you can swap this weekend for next, that works"),
        Message(seq=2, thread="T", sender="Sam", timestamp="2025-04-11T09:40", domain="d",
                body="we never agreed to swap weekends"),
    ]
    sig = Signal("L3", "claim_contradicted", 1, "Sam", "T", None,  # noqa: E501
                 "record R1: agreed_to_swap=True", (2,))
    res = EngineResult((Finding((1, 2), "elevated", ("L3",), (sig,), "contradiction"),), (sig,), 2)
    txt = BlancNarrator(msgs).narrate(res)
    assert "Date 1 (2025-04-07)" in txt                  # the earlier word
    assert "Date 2 (2025-04-11)" in txt                  # the later, opposite word
    assert "But lo and behold" in txt
    assert "Must be nice" in txt
    assert "we never agreed to swap weekends" in txt     # the contradicting quote


def test_blanc_walks_the_coercion_grammar():
    from pathlib import Path

    from convergence.coercion_grammar import match_grammar, tag_stages
    from convergence.corpus import load_corpus
    from convergence.narration import BlancNarrator
    msgs = load_corpus(Path(__file__).parent.parent / "data" / "coercion_grammar_thread.json")
    txt = BlancNarrator(msgs).narrate_grammar(tag_stages(msgs), match_grammar(msgs))
    low = txt.lower()
    assert "fait accompli" in low and "status quo" in low
    assert "can we confirm" in low                       # the action, quoted
    assert "it's already done" in low                    # the fait accompli, quoted


def test_blanc_explains_the_magic_trick():
    from convergence.narration import BlancNarrator
    txt = BlancNarrator().magic_trick().lower()
    assert "trick" in txt
    assert "never decide" in txt or "do not decide" in txt or "do not read minds" in txt
    assert "hole" in txt                                  # the trick is the hole, not the donut
    assert BlancNarrator().magic_trick() == BlancNarrator().magic_trick()  # deterministic


def test_blanc_deterministic_and_handles_empty():
    from convergence.narration import BlancNarrator
    empty = run_engine([_msg(1, "A", "hello there"), _msg(2, "A", "hi again")])
    assert BlancNarrator().narrate(empty) == BlancNarrator().narrate(empty)
    assert BlancNarrator().narrate(empty)  # non-empty string even with no findings


def test_l4_lines_are_capped_with_remainder_note():
    from convergence.engine import EngineResult, Finding, Signal
    from convergence.narration import MAX_L4_LINES, TemplateNarrator

    def _l4(n_domains):
        doms = ", ".join(f"d{i}" for i in range(n_domains))
        return Signal("L4", "domain_convergence", 1, "", "T", None, f"anchor across {doms}", (2,))

    sigs = (Signal("L1", "borrow_authority", 1, "", "T", None, "policy says"),) + tuple(
        _l4(n) for n in range(2, 12)   # 10 L4 signals
    )
    f = Finding(seqs=(1,), confidence="elevated", layers=("L1", "L4"),
                signals=sigs, summary="s")
    res = EngineResult(findings=(f,), all_signals=sigs, corpus_size=2)
    out = TemplateNarrator().narrate(res)
    assert out.count("[L4]") == MAX_L4_LINES          # capped
    assert "[L1] policy says" in out                  # non-L4 untouched
    assert f"(+{10 - MAX_L4_LINES} weaker convergences)" in out


def test_l4_cap_keeps_specific_anchors_over_generic_high_count():
    from convergence.engine import EngineResult, Finding, Signal
    from convergence.narration import TemplateNarrator

    def _l4(anchor, n_domains):
        doms = ", ".join(f"d{i}" for i in range(n_domains))
        return Signal("L4", "domain_convergence", 1, "", "T", None, f"{anchor} across {doms}", (2,))

    # Generic short words ride MANY domains; substantive anchors span few. The cap
    # must keep the substantive ones (specificity), not the high-count noise.
    sigs = (
        _l4("schedule change", 2),   # substantive bigram
        _l4("pediatrician", 2),      # substantive long unigram
        _l4("parenting time", 2),    # substantive bigram
        _l4("time", 9),              # generic short, high count
        _l4("been", 8),              # generic short, high count
    )
    f = Finding(seqs=(1,), confidence="elevated", layers=("L4",),
                signals=sigs, summary="s")
    out = TemplateNarrator().narrate(EngineResult(findings=(f,), all_signals=sigs, corpus_size=2))
    assert "[L4] schedule change across" in out
    assert "[L4] pediatrician across" in out
    assert "[L4] parenting time across" in out
    assert "[L4] time across" not in out     # generic high-count dropped
    assert "[L4] been across" not in out

