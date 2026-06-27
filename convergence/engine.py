"""The convergence engine.

Every layer is reduced to a common `Signal`. Signals are grouped, and a group
is only **elevated** when two or more *independent* layers point at the same
material. A lone signal - one tactic, one omission, one domain overlap - stays
**low**. This is the spine of the whole design: the engine is built to refuse
its own findings unless they survive corroboration. It cannot grade its own
homework.

Grouping detail: L1/L2/L3/L5 are "focal" - they define clusters and may merge
(e.g. an L3 contradiction names the source message an L2 omission removed, so
they bind on that shared seq). L4 (domain convergence) is a corroborator only:
it adds its weight to clusters it overlaps but never merges two clusters that
would otherwise be separate.

Substantive vs. contextual: L1 (a tactic), L2 (an omission) and L3 (a
contradiction) are *substantive* - they are the actual moves. L4 (domain
overlap) and L5 (register shift) are *contextual* - they strengthen a
substantive finding but cannot, on their own, make one. So a group is elevated
only when it carries at least one substantive layer AND a second layer of any
kind. Context-only groups (L4/L5 with nothing substantive) stay low - which is
exactly the "can't grade its own homework" guarantee.
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


@dataclass(frozen=True)
class Signal:
    layer: str
    seqs: tuple[int, ...]
    kind: str
    detail: str


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
    signals: list[Signal] = []
    for h in detect_patterns(full):
        signals.append(Signal("L1", (h.seq,), h.tactic, h.cue))
    if included_seqs is not None:
        for g in find_omissions(full, included_seqs):
            if g.within_thread:
                signals.append(Signal("L2", (g.seq,), "within_thread_omission",
                                      f"cut between shown {g.prev_seq} and {g.next_seq}"))
    if records is not None:
        for c in check_claims(full, records):
            seqs = tuple(sorted({c.seq} | ({c.contradicting_seq} if c.contradicting_seq is not None else set())))
            signals.append(Signal("L3", seqs, "claim_contradicted", c.basis))
    if cross_channel is not None:
        # L6 cites a seq in the *other* channel; the signal anchors only on the
        # primary seq so it never collides with an unrelated primary message.
        for d in find_cross_channel_divergences(full, cross_channel):
            signals.append(Signal("L6", (d.seq,), "cross_channel_divergence", d.basis))
    for cv in find_convergences(full):
        signals.append(Signal("L4", cv.seqs, "domain_convergence", f"{cv.anchor} across {', '.join(cv.domains)}"))
    for a in detect_register_anomalies(full):
        signals.append(Signal("L5", (a.seq,), "register_anomaly", a.reason))
    return signals


def _summary(sigs, confidence: str) -> str:
    kinds = sorted({s.kind for s in sigs})
    phrases = [_KIND_PHRASES.get(k, k) for k in kinds]
    if confidence == "elevated":
        return "Elevated - " + " + ".join(phrases) + " independently agree."
    return "Low - " + ", ".join(phrases) + " (single layer; not corroborated)."


def run_engine(full: list[Message], included_seqs=None, records=None, cross_channel=None) -> EngineResult:
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
            signals=tuple(g["sigs"]),
            summary=_summary(g["sigs"], confidence),
        ))
    findings.sort(key=lambda f: (f.confidence != "elevated", f.seqs))
    return EngineResult(findings=tuple(findings), all_signals=tuple(signals), corpus_size=len(full))
