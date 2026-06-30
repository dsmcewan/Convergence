"""The convergence engine.

Every layer is reduced to a common `Signal`. Signals are grouped, and a group
is only **elevated** when two or more *independent* layers point at the same
material. A lone signal - one tactic, one omission, one domain overlap - stays
**low**. This is the spine of the whole design: the engine is built to refuse
its own findings unless they survive corroboration. It cannot grade its own
homework.

Grouping detail: L1/L2/L3/L5/L6 are "focal" - they define clusters and may
merge (e.g. an L3 contradiction names the source message an L2 omission
removed, so they bind on that shared seq). L4 (domain convergence) is a
corroborator only: it adds its weight to clusters it overlaps but never merges
two clusters that would otherwise be separate.

Substantive vs. contextual: L1 (tactic), L2 (omission), L3 (contradiction),
and L6 (cross-channel divergence) are *substantive* - they are the actual
moves. L4 (domain overlap) is a pure corroborator - it never forms a finding
on its own. L5 (register shift) is focal-but-contextual - it can bridge
clusters but is not substantive. So a group is elevated only when it carries at
least one substantive layer AND a second layer of any kind. Context-only groups
(L4/L5 with nothing substantive) stay low - which is exactly the "can't grade
its own homework" guarantee.
"""
from __future__ import annotations

from dataclasses import dataclass

from convergence.corpus import Message
from convergence.layers.cross_channel import find_cross_channel_divergences
from convergence.layers.domain_convergence import find_convergences
from convergence.layers.gap_detector import find_omissions
from convergence.layers.pattern_detector import detect_patterns
from convergence.layers.phrase_fragmentation import detect_register_anomalies
from convergence.layers.third_party import check_claims

_BRIDGING = {"L1", "L2", "L3", "L5", "L6"}
_SUBSTANTIVE = {"L1", "L2", "L3", "L6"}
_KIND_PHRASES = {
    "borrow_authority": "a decision deferred to an outside authority",
    "within_thread_omission": "a message cut from inside a continuous thread",
    "claim_contradicted": "a claim contradicted by an external record",
    "domain_convergence": "independent domains converging on one anchor",
    "register_anomaly": "a register shift from the sender's baseline",
    "cross_channel_divergence": "a claim contradicted by the sender's own words in another channel",
}

# Canonical within-finding signal order: substantive layers first (the moves),
# then contextual corroborators, matching the collection order in
# `_collect_signals`. A signal's position must NOT depend on the set/dict
# iteration order of any layer's detector (which can vary across Python
# versions), so findings sort their signals by this total key before freezing.
_LAYER_ORDER = {"L1": 0, "L2": 1, "L3": 2, "L6": 3, "L4": 4, "L5": 5}


def _signal_sort_key(s) -> tuple:
    """Total, version-stable ordering key for a Signal: (layer, seqs, kind, evidence)."""
    return (_LAYER_ORDER.get(s.layer, 99), s.seqs, s.kind, s.evidence)


@dataclass(frozen=True)
class Signal:
    layer: str                  # "L1".."L6"
    kind: str                   # tactic / kind
    anchor: int                 # the single message the move is ABOUT
    actor: str                  # sender of the anchor message
    thread: str                 # thread of the anchor message
    target: str | None          # who the move is aimed at, when determinable; else None
    evidence: str               # the proof/cue string (was `detail`)
    support: tuple[int, ...] = ()  # the move's other seqs (anchor excluded)

    @property
    def seqs(self) -> tuple[int, ...]:
        return tuple(sorted({self.anchor, *self.support}))


@dataclass(frozen=True)
class Finding:
    seqs: tuple[int, ...]
    confidence: str  # "elevated" | "low"
    layers: tuple[str, ...]
    signals: tuple[Signal, ...]
    summary: str


@dataclass(frozen=True)
class EngineResult:
    findings: tuple[Finding, ...]
    all_signals: tuple[Signal, ...]
    corpus_size: int


def _collect_signals(full, included_seqs, records, cross_channel) -> list[Signal]:
    by_seq = {m.seq: m for m in full}

    def prov(anchor: int) -> tuple[str, str]:
        m = by_seq.get(anchor)
        return (m.sender, m.thread) if m else ("", "")

    signals: list[Signal] = []
    for h in detect_patterns(full):
        actor, thread = prov(h.seq)
        signals.append(Signal("L1", h.tactic, h.seq, actor, thread, None, h.cue))
    if included_seqs is not None:
        for g in find_omissions(full, included_seqs):
            if g.within_thread:
                actor, thread = prov(g.seq)
                signals.append(Signal(
                    "L2", "within_thread_omission", g.seq, actor, thread, None,
                    f"cut between shown {g.prev_seq} and {g.next_seq}"))
    if records is not None:
        for c in check_claims(full, records):
            actor, thread = prov(c.seq)
            support = (c.contradicting_seq,) if c.contradicting_seq is not None else ()
            signals.append(Signal(
                "L3", "claim_contradicted", c.seq, actor, thread, None, c.basis, support))
    if cross_channel is not None:
        # L6 anchors only on the primary seq (support stays empty) so it never
        # collides with an unrelated primary message — exactly as before.
        for d in find_cross_channel_divergences(full, cross_channel):
            actor, thread = prov(d.seq)
            signals.append(Signal(
                "L6", "cross_channel_divergence", d.seq, actor, thread, None, d.basis))
    for cv in find_convergences(full):
        anchor = min(cv.seqs)
        support = tuple(s for s in sorted(cv.seqs) if s != anchor)
        actor, thread = prov(anchor)
        signals.append(Signal(
            "L4", "domain_convergence", anchor, actor, thread, None,
            f"{cv.anchor} across {', '.join(cv.domains)}", support))
    for a in detect_register_anomalies(full):
        actor, thread = prov(a.seq)
        signals.append(Signal(
            "L5", "register_anomaly", a.seq, actor, thread, None, a.reason))
    return signals


def _summary(sigs, confidence: str) -> str:
    kinds = sorted({s.kind for s in sigs})
    phrases = [_KIND_PHRASES.get(k, k) for k in kinds]
    if confidence == "elevated":
        return "Elevated - " + " + ".join(phrases) + " independently agree."
    return "Low - " + ", ".join(phrases) + " (single layer; not corroborated)."


def run_engine(full: list[Message], included_seqs=None, records=None, cross_channel=None) -> EngineResult:  # noqa: E501
    signals = _collect_signals(full, included_seqs, records, cross_channel)
    focal = [s for s in signals if s.layer in _BRIDGING]
    corroborators = [s for s in signals if s.layer not in _BRIDGING]

    groups: list[dict] = []
    for s in focal:
        sset = set(s.seqs)
        touching = [g for g in groups if g["seqs"] & sset]
        if not touching:
            groups.append({"seqs": sset, "sigs": [s]})
        else:
            merged = {"seqs": set(sset), "sigs": [s]}
            for g in touching:
                merged["seqs"] |= g["seqs"]
                merged["sigs"] += g["sigs"]
                groups.remove(g)
            groups.append(merged)

    for s in corroborators:
        touching = [g for g in groups if g["seqs"] & set(s.seqs)]
        if touching:
            for g in touching:
                g["sigs"].append(s)  # corroborate, do not merge or expand seqs
        else:
            groups.append({"seqs": set(s.seqs), "sigs": [s]})

    findings = []
    for g in groups:
        layers = tuple(sorted({s.layer for s in g["sigs"]}))
        has_substantive = any(layer in _SUBSTANTIVE for layer in layers)
        confidence = "elevated" if (has_substantive and len(layers) >= 2) else "low"
        findings.append(Finding(
            seqs=tuple(sorted(g["seqs"])),
            confidence=confidence,
            layers=layers,
            signals=tuple(sorted(g["sigs"], key=_signal_sort_key)),
            summary=_summary(g["sigs"], confidence),
        ))
    findings.sort(key=lambda f: (f.confidence != "elevated", f.seqs))
    return EngineResult(findings=tuple(findings), all_signals=tuple(signals), corpus_size=len(full))
