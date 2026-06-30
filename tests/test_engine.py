"""The convergence verdict: elevate only on >=2 independent layers."""
import json
from pathlib import Path

from convergence.corpus import Message, load_corpus
from convergence.engine import Signal, _signal_sort_key, run_engine
from convergence.records import load_records

DATA = Path(__file__).parent.parent / "data"


def _msg(seq, sender, domain, body):
    return Message(seq=seq, thread="T", sender=sender, timestamp="t", domain=domain, body=body)


def test_empty_corpus_returns_no_findings():
    assert run_engine([]).findings == ()


def test_no_signals_empty():
    msgs = [_msg(1, "A", "d", "hello there friend"), _msg(2, "A", "d", "hi again friend")]
    assert run_engine(msgs).findings == ()


def test_single_layer_stays_low():
    # Only L1 fires (one message, one sender -> no L5; single domain -> no L4).
    msgs = [_msg(1, "A", "d", "my accountant says I owe less")]
    res = run_engine(msgs)
    f = next(f for f in res.findings if 1 in f.seqs)
    assert f.confidence == "low"
    assert f.layers == ("L1",)


def test_two_layers_elevated():
    # seq 2 fires L1 (accountant says) AND L5 (formal vs casual baseline).
    msgs = [
        _msg(1, "M", "d", "hey start it soon thanks"),
        _msg(2, "M", "d", "my accountant says I am not approving the authorization pursuant to policy"),  # noqa: E501
    ]
    res = run_engine(msgs)
    f = next(f for f in res.findings if 2 in f.seqs)
    assert f.confidence == "elevated"
    assert "L1" in f.layers and "L5" in f.layers


def test_cross_channel_divergence_is_substantive():
    # A lone L6 divergence (claim here vs admission in the other channel) is
    # substantive but uncorroborated -> low, exactly like a lone L1/L2/L3.
    primary = [_msg(2, "A", "d", "I have always kept you fully informed of every appointment.")]
    cross = [_msg(7, "A", "d", "honestly I forgot to tell you about the dentist.")]
    res = run_engine(primary, cross_channel=cross)
    f = next(f for f in res.findings if 2 in f.seqs)
    assert f.layers == ("L6",)
    assert f.confidence == "low"


def test_cross_channel_divergence_elevates_with_corroboration():
    # Same L6 divergence, now the claim message also converges two domains on its
    # anchor (L4) -> substantive + a second layer -> elevated.
    primary = [
        _msg(2, "A", "medical", "I have always kept you informed about every appointment with the dentist."),  # noqa: E501
        _msg(3, "A", "schedule", "the appointment scheduling has always been shared in advance."),
    ]
    cross = [_msg(7, "A", "d", "honestly I forgot to tell you about the dentist.")]
    res = run_engine(primary, cross_channel=cross)
    f = next(f for f in res.findings if 2 in f.seqs)
    assert f.confidence == "elevated"
    assert "L6" in f.layers


def test_findings_sorted_elevated_first():
    msgs = [
        _msg(1, "M", "d", "hey start it soon thanks"),
        _msg(2, "M", "d", "my accountant says I am not approving the authorization pursuant to policy"),  # noqa: E501
        _msg(3, "Z", "d", "my lawyer says no"),  # single message sender -> L1 only -> low
    ]
    res = run_engine(msgs)
    assert res.findings[0].confidence == "elevated"


def test_integration_headline_and_self_disqualification():
    full = load_corpus(DATA / "sample_full.json")
    included = json.loads((DATA / "sample_exhibit.json").read_text(encoding="utf-8"))["included_seqs"]  # noqa: E501
    records = load_records(DATA / "sample_records.json")
    res = run_engine(full, included_seqs=included, records=records)

    # Headline: the claim at seq 10 is contradicted by the record whose proof
    # (seq 3) was cut from the exhibit -> L2 + L3 converge -> elevated.
    head = next(f for f in res.findings if 10 in f.seqs)
    assert head.confidence == "elevated"
    assert 3 in head.seqs
    assert {"L2", "L3"} <= set(head.layers)

    # seq 5 finding is elevated (borrow-authority corroborated).
    five = next(f for f in res.findings if f.seqs == (5,))
    assert five.confidence == "elevated"
    assert "L1" in five.layers

    # Self-disqualification: at least one lone-layer finding stays low.
    assert any(f.confidence == "low" and len(f.layers) == 1 for f in res.findings)

    # Every elevated finding carries a substantive layer; context-only is never elevated.
    for f in res.findings:
        if f.confidence == "elevated":
            assert any(layer in {"L1", "L2", "L3", "L6"} for layer in f.layers)
        if set(f.layers) <= {"L4", "L5"}:
            assert f.confidence == "low"


def test_signal_order_is_canonical_and_input_independent():
    # Multiple L4 corroborators on one anchor: their emission order from
    # find_convergences can vary with set/dict iteration (and thus across Python
    # versions), so a finding must impose a total, version-stable signal order.
    a = Signal("L4", "domain_convergence", 8, "Sam", "T", None, "weekend across medical, schedule")
    b = Signal("L4", "domain_convergence", 8, "Sam", "T", None, "agreed across medical, schedule")
    c = Signal("L4", "domain_convergence", 8, "Sam", "T", None, "swap across medical, schedule")
    forward = sorted([a, b, c], key=_signal_sort_key)
    reverse = sorted([c, b, a], key=_signal_sort_key)
    assert forward == reverse  # final order does not depend on input order
    # canonical: ascending by evidence within the same layer + seqs
    assert [s.evidence for s in forward] == sorted(s.evidence for s in (a, b, c))
    # substantive layers sort before contextual ones regardless of input order
    sub = Signal("L1", "borrow_authority", 8, "Sam", "T", None, "lawyer says")
    assert sorted([a, sub], key=_signal_sort_key)[0] is sub


def test_engine_emits_signals_in_canonical_order():
    # Over a real multi-L4 corpus, every finding's signals come out canonically
    # sorted — so the serialized narration is reproducible across Python versions.
    full = load_corpus(DATA / "coparenting_full.json")
    included = json.loads((DATA / "coparenting_exhibit.json").read_text(encoding="utf-8"))["included_seqs"]  # noqa: E501
    records = load_records(DATA / "coparenting_records.json")
    result = run_engine(full, included_seqs=included, records=records)
    assert result.findings  # corpus does produce findings
    for f in result.findings:
        assert list(f.signals) == sorted(f.signals, key=_signal_sort_key)
