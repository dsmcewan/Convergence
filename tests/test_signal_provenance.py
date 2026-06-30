"""Phase 1: Signal carries correct provenance, derived from the anchor message."""
import json
from pathlib import Path

from convergence.corpus import Message, load_corpus
from convergence.engine import run_engine
from convergence.records import load_records

DATA = Path(__file__).parent.parent / "data"


def _msg(seq, sender, domain, body, thread="T"):
    return Message(seq=seq, thread=thread, sender=sender, timestamp="t", domain=domain, body=body)


def _coparenting():
    full = load_corpus(DATA / "coparenting_full.json")
    included = json.loads(  # noqa: E501
        (DATA / "coparenting_exhibit.json").read_text(encoding="utf-8"))["included_seqs"]
    records = load_records(DATA / "coparenting_records.json")
    return run_engine(full, included_seqs=included, records=records), {m.seq: m for m in full}


def test_actor_and_thread_derive_from_the_anchor_message():
    result, by_seq = _coparenting()
    assert result.all_signals  # the corpus fires several layers
    for s in result.all_signals:
        anchor_msg = by_seq[s.anchor]
        assert s.actor == anchor_msg.sender
        assert s.thread == anchor_msg.thread


def test_seqs_property_is_anchor_union_support_sorted():
    result, _ = _coparenting()
    for s in result.all_signals:
        assert s.anchor in s.seqs
        assert s.seqs == tuple(sorted({s.anchor, *s.support}))
        assert s.anchor not in s.support  # anchor is excluded from support


def test_l3_contradiction_carries_the_contradicting_seq_in_support():
    result, _ = _coparenting()
    l3 = [s for s in result.all_signals if s.layer == "L3"]
    assert l3, "coparenting corpus should produce an L3 contradiction"
    # an L3 signal spanning two messages keeps the contradicting seq in support
    multi = [s for s in l3 if len(s.seqs) > 1]
    assert multi, "expected at least one two-seq L3 contradiction"
    for s in multi:
        assert len(s.support) == 1 and s.support[0] != s.anchor


def test_l1_pattern_anchor_actor_evidence():
    # A lone borrow-authority message: anchor=its seq, actor=its sender, evidence=the cue.
    msgs = [_msg(1, "Mara", "scope", "my accountant says I am not approving the authorization")]
    result = run_engine(msgs)
    l1 = [s for s in result.all_signals if s.layer == "L1"]
    assert l1
    s = l1[0]
    assert s.anchor == 1 and s.actor == "Mara" and s.thread == "T"
    assert s.support == () and s.target is None
    assert "accountant" in s.evidence


def test_target_defaults_to_none_in_phase1_layers():
    result, _ = _coparenting()
    assert all(s.target is None for s in result.all_signals)
