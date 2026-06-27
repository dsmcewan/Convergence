"""Layers 7-8 - composition: patterns and campaigns.

Above the engine. find_patterns reads the EngineResult and recognizes (a) named
tactic-chains (templates, the DARVO analog) and (b) a single tactic recurring past
a threshold. find_campaigns attributes elevated findings and patterns to an
ACTOR and a TARGET (via the messages) and emits a campaign only when one actor
sustains >=2 elevated findings against one target over time. Synthetic inputs only.
"""
from convergence.corpus import Message
from convergence.engine import Signal, Finding, EngineResult
from convergence.composition import find_patterns, find_campaigns


def _sig(layer, seqs, kind, detail="d"):
    return Signal(layer=layer, seqs=tuple(seqs), kind=kind, detail=detail)


def _finding(seqs, confidence, signals):
    layers = tuple(sorted({s.layer for s in signals}))
    return Finding(seqs=tuple(seqs), confidence=confidence, layers=layers,
                   signals=tuple(signals), summary="s")


def _result(findings, signals, size=20):
    return EngineResult(findings=tuple(findings), all_signals=tuple(signals), corpus_size=size)


def _msg(seq, sender, domain, ts):
    return Message(seq=seq, thread="T", sender=sender, timestamp=ts, domain=domain, body="b")


# --- patterns: templates ---------------------------------------------------

def test_sanitize_record_template():
    f = _finding([3, 10], "elevated",
                 [_sig("L3", [10], "claim_contradicted"), _sig("L2", [3], "within_thread_omission")])
    pats = find_patterns(_result([f], list(f.signals)))
    assert any(p.name == "sanitize-record" and p.kind == "template" for p in pats)


def test_sanitize_record_template_expands_to_chronological_structure():
    f = _finding([3, 10], "elevated",
                 [_sig("L3", [3, 10], "claim_contradicted"), _sig("L2", [3], "within_thread_omission")])
    signals = [
        *f.signals,
        _sig("L2", [5], "within_thread_omission"),
        _sig("L2", [11], "within_thread_omission"),
    ]

    pattern = next(p for p in find_patterns(_result([f], signals)) if p.name == "sanitize-record")

    assert pattern.seqs == (3, 5, 10, 11)
    assert "reliance" in pattern.detail


def test_sanitize_record_template_uses_domain_structure_when_needed():
    f = _finding([4, 11], "elevated", [
        _sig("L3", [4, 11], "claim_contradicted"),
        _sig("L2", [4], "within_thread_omission"),
        _sig("L4", [1, 4, 10, 11], "domain_convergence", "swap across medical, schedule"),
    ])

    pattern = next(p for p in find_patterns(_result([f], list(f.signals))) if p.name == "sanitize-record")

    assert pattern.seqs == (1, 4, 10, 11)
    assert len(set(pattern.seqs)) >= 4


def test_two_faced_template():
    f = _finding([2], "elevated", [_sig("L6", [2], "cross_channel_divergence")])
    pats = find_patterns(_result([f], list(f.signals)))
    assert any(p.name == "two-faced" for p in pats)


def test_defer_and_deny_template():
    f = _finding([5], "elevated",
                 [_sig("L1", [5], "borrow_authority"), _sig("L3", [5], "claim_contradicted")])
    pats = find_patterns(_result([f], list(f.signals)))
    assert any(p.name == "defer-and-deny" for p in pats)


def test_no_template_when_required_kind_missing():
    f = _finding([5], "elevated", [_sig("L1", [5], "borrow_authority")])
    pats = find_patterns(_result([f], list(f.signals)))
    assert all(p.kind != "template" for p in pats)


# --- patterns: recurrence --------------------------------------------------

def test_recurrence_pattern_at_threshold():
    sigs = [_sig("L1", [s], "borrow_authority") for s in (8, 10, 13)]
    pats = find_patterns(_result([], sigs), recurrence_min=3)
    rec = [p for p in pats if p.kind == "recurrence"]
    assert len(rec) == 1
    assert rec[0].name == "repeated:borrow_authority"
    assert rec[0].seqs == (8, 10, 13)


def test_recurrence_below_threshold_is_silent():
    sigs = [_sig("L1", [s], "borrow_authority") for s in (8, 10)]
    pats = find_patterns(_result([], sigs), recurrence_min=3)
    assert [p for p in pats if p.kind == "recurrence"] == []


def test_recurrence_ignores_contextual_kinds():
    # domain overlap and register shift are ambient context, not repeated *moves*;
    # they must never count as a recurrence pattern even when frequent.
    sigs = ([_sig("L4", [s], "domain_convergence") for s in (1, 2, 3, 4)]
            + [_sig("L5", [s], "register_anomaly") for s in (1, 2, 3)])
    pats = find_patterns(_result([], sigs), recurrence_min=3)
    assert [p for p in pats if p.kind == "recurrence"] == []


def test_patterns_are_deterministic():
    f = _finding([3, 10], "elevated",
                 [_sig("L3", [10], "claim_contradicted"), _sig("L2", [3], "within_thread_omission")])
    r = _result([f], list(f.signals))
    assert find_patterns(r) == find_patterns(r)


# --- campaigns -------------------------------------------------------------

def _coparenting_like():
    # Sam drives two elevated borrow-authority findings in the medical domain.
    msgs = [
        _msg(8, "Sam", "medical", "2025-04-11T09:03"),
        _msg(10, "Sam", "medical", "2025-04-11T09:31"),
        _msg(13, "Sam", "schedule", "2025-04-11T10:05"),
    ]
    f8 = _finding([8], "elevated", [_sig("L1", [8], "borrow_authority"), _sig("L5", [8], "register_anomaly")])
    f10 = _finding([10], "elevated", [_sig("L1", [10], "borrow_authority"), _sig("L5", [10], "register_anomaly")])
    sigs = [_sig("L1", [s], "borrow_authority") for s in (8, 10, 13)]
    return _result([f8, f10], sigs), msgs


def test_campaign_actor_target_over_time():
    result, msgs = _coparenting_like()
    camps = find_campaigns(result, msgs)
    assert len(camps) == 1
    c = camps[0]
    assert c.actor == "Sam"
    assert c.target == "medical"
    assert c.span == ("2025-04-11T09:03", "2025-04-11T09:31")


def test_campaign_span_is_chronological_not_lexicographic():
    # Non-ISO timestamps where string order != time order: "12/01/2024" sorts
    # AFTER "01/05/2025" as a string, but is chronologically EARLIER. The span
    # must reflect real time, parsed, not raw string sort.
    msgs = [_msg(8, "Sam", "medical", "12/01/2024 09:00"),
            _msg(10, "Sam", "medical", "01/05/2025 09:00")]
    f8 = _finding([8], "elevated", [_sig("L1", [8], "borrow_authority"), _sig("L5", [8], "register_anomaly")])
    f10 = _finding([10], "elevated", [_sig("L1", [10], "borrow_authority"), _sig("L5", [10], "register_anomaly")])
    c = find_campaigns(_result([f8, f10], []), msgs)[0]
    assert c.span == ("12/01/2024 09:00", "01/05/2025 09:00")   # earliest .. latest by time


def test_single_elevated_finding_is_not_a_campaign():
    msgs = [_msg(8, "Sam", "medical", "2025-04-11T09:03")]
    f8 = _finding([8], "elevated", [_sig("L1", [8], "borrow_authority"), _sig("L5", [8], "register_anomaly")])
    assert find_campaigns(_result([f8], list(f8.signals)), msgs) == []


def test_two_findings_on_different_targets_is_not_a_campaign():
    msgs = [_msg(8, "Sam", "medical", "2025-04-11T09:03"),
            _msg(11, "Sam", "schedule", "2025-04-11T09:40")]
    f8 = _finding([8], "elevated", [_sig("L1", [8], "borrow_authority"), _sig("L5", [8], "register_anomaly")])
    f11 = _finding([11], "elevated", [_sig("L1", [11], "borrow_authority"), _sig("L5", [11], "register_anomaly")])
    assert find_campaigns(_result([f8, f11], []), msgs) == []


def test_recurrence_pattern_attached_to_campaign():
    result, msgs = _coparenting_like()
    c = find_campaigns(result, msgs)[0]
    assert "repeated:borrow_authority" in c.patterns


def test_campaign_attributes_modal_sender():
    # a finding spanning multiple senders is attributed to the majority sender
    msgs = [_msg(8, "Sam", "medical", "2025-04-11T09:03"),
            _msg(9, "Alex", "medical", "2025-04-11T09:12"),
            _msg(10, "Sam", "medical", "2025-04-11T09:31"),
            _msg(12, "Sam", "medical", "2025-04-11T09:50")]
    # f1 spans Sam, Alex, Sam -> Sam is the majority
    f1 = _finding([8, 9, 10], "elevated",
                  [_sig("L1", [8], "borrow_authority"), _sig("L2", [9], "within_thread_omission"),
                   _sig("L3", [10], "claim_contradicted")])
    f2 = _finding([12], "elevated", [_sig("L1", [12], "borrow_authority"), _sig("L5", [12], "register_anomaly")])
    camps = find_campaigns(_result([f1, f2], []), msgs)
    assert len(camps) == 1
    assert camps[0].actor == "Sam"
