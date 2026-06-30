"""Layers 7-8 - composition: patterns and campaigns.

The engine answers a per-event question: "is this one finding corroborated?".
Composition sits above it and answers two structural ones:

  * PATTERN (L7) - is there a recognizable *structure* in how the moves combine?
      - template: a named tactic-chain (the corpus-agnostic analog of DARVO),
        matched when a finding carries all of a template's required signal kinds;
      - recurrence: a single tactic repeated past a threshold (a habit, not an
        incident).
  * CAMPAIGN (L8) - is this a *sustained course of conduct*? One actor (sender)
    driving >=2 elevated findings against one target (topical domain) over time.

No engine changes: composition only *reads* the EngineResult (and, for campaigns,
the messages, to attribute an actor and target). The verdicts are the engine's;
this layer narrates their higher-order shape.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime

from convergence.corpus import Message
from convergence.engine import EngineResult

# Tolerant timestamp formats for chronology. ISO (fromisoformat) covers typical exports and
# the synthetic corpora; the rest catch common real-world variants. Order matters
# only for ambiguous strings, which these formats avoid.
_TS_FORMATS = ("%m/%d/%Y %H:%M:%S", "%m/%d/%Y %H:%M", "%m/%d/%Y",
               "%m/%d/%y %H:%M", "%m/%d/%y")


def _parse_ts(s):
    """Tolerant timestamp parse -> datetime, or None when unparseable.

    The seam that lets chronology be real time, not lexicographic string order:
    "12/01/2024" precedes "01/05/2025" in time but follows it as a string.
    """
    if not isinstance(s, str) or not s.strip():
        return None
    try:
        s2 = s.strip()
        if s2.endswith("Z"):
            s2 = s2[:-1] + "+00:00"
        return datetime.fromisoformat(s2)
    except ValueError:
        pass
    for fmt in _TS_FORMATS:
        try:
            return datetime.strptime(s.strip(), fmt)
        except ValueError:
            continue
    return None


def _ts_sort_key(ts: str):
    """Deterministic chronological key: parseable times first (by time), then
    unparseable values by raw string — so ordering never throws and is stable."""
    dt = _parse_ts(ts)
    return (0, dt.isoformat()) if dt else (1, ts)


# --- patterns --------------------------------------------------------------

@dataclass(frozen=True)
class _Template:
    name: str
    required: frozenset  # signal kinds that must all be present in one finding


# The substantive moves (cf. the engine's L1/L2/L3/L6). Recurrence counts only
# these - a repeated *tactic* is a habit; repeated domain overlap or register
# shift is ambient context, not a move, and would only add noise.
_SUBSTANTIVE_KINDS = frozenset({
    "borrow_authority", "within_thread_omission", "claim_contradicted", "cross_channel_divergence",
})

# Extensible registry. A template fires when a single finding carries every
# required kind - the moves are corroborated AND combine into a known chain.
_TEMPLATES = (
    _Template("sanitize-record", frozenset({"claim_contradicted", "within_thread_omission"})),
    _Template("defer-and-deny", frozenset({"borrow_authority", "claim_contradicted"})),
    _Template("two-faced", frozenset({"cross_channel_divergence"})),
)


@dataclass(frozen=True)
class Pattern:
    name: str
    kind: str                  # "template" | "recurrence"
    seqs: tuple[int, ...]
    detail: str


def find_patterns(result: EngineResult, recurrence_min: int = 3) -> list[Pattern]:
    out: list[Pattern] = []

    # templates: a named chain present within one finding
    for f in result.findings:
        if f.confidence != "elevated":
            continue
        kinds = {s.kind for s in f.signals}
        for t in _TEMPLATES:
            if t.required <= kinds:
                seqs = _template_seqs(t, f, result)
                out.append(Pattern(
                    name=t.name, kind="template", seqs=seqs,
                    detail=_template_detail(t, seqs),
                ))

    # recurrence: one tactic repeated across >= recurrence_min distinct messages
    seqs_by_kind: dict[str, set[int]] = defaultdict(set)
    for s in result.all_signals:
        if s.kind in _SUBSTANTIVE_KINDS:
            seqs_by_kind[s.kind].update(s.seqs)
    for kind, seqs in seqs_by_kind.items():
        if len(seqs) >= recurrence_min:
            ordered = tuple(sorted(seqs))
            out.append(Pattern(
                name=f"repeated:{kind}", kind="recurrence", seqs=ordered,
                detail=f"{kind} recurs across {len(ordered)} messages",
            ))

    out.sort(key=lambda p: (p.kind, p.name, p.seqs))
    return out


def _template_seqs(template: _Template, finding, result: EngineResult) -> tuple[int, ...]:
    seqs = set(finding.seqs)
    if template.name == "sanitize-record":
        for signal in result.all_signals:
            if signal.kind in template.required:
                seqs.update(signal.seqs)
        if len(seqs) < 4:
            local = set(finding.seqs)
            candidates = [
                signal for signal in finding.signals
                if signal.kind == "domain_convergence" and local.intersection(signal.seqs)
            ]
            candidates.sort(key=lambda signal: (-len(local.intersection(signal.seqs)), len(signal.seqs), signal.seqs))
            for signal in candidates:
                expanded = seqs.union(signal.seqs)
                if len(expanded) >= 4:
                    seqs = expanded
                    break
    return tuple(sorted(seqs))


def _template_detail(template: _Template, seqs: tuple[int, ...]) -> str:
    if template.name == "sanitize-record" and len(set(seqs)) >= 4:
        return "reliance, authority shift, denial, and record pressure repeat the sanitize-record structure"
    return f"{' + '.join(sorted(template.required))} => {template.name}"


# --- campaigns -------------------------------------------------------------

@dataclass(frozen=True)
class Campaign:
    actor: str
    target: str
    patterns: tuple[str, ...]
    findings: tuple[tuple[int, ...], ...]
    seqs: tuple[int, ...]
    span: tuple[str, str]
    summary: str


def _modal(values: list[str]) -> str | None:
    if not values:
        return None
    counts = Counter(values)
    # highest count; ties resolved lexicographically for determinism
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]


def _attribute(seqs, by_seq: dict[int, Message]) -> tuple[str | None, str | None]:
    present = [by_seq[s] for s in seqs if s in by_seq]
    return _modal([m.sender for m in present]), _modal([m.domain for m in present])


def find_campaigns(result: EngineResult, messages: list[Message],
                   min_findings: int = 2) -> list[Campaign]:
    by_seq = {m.seq: m for m in messages}
    patterns = find_patterns(result)

    # group elevated findings by (actor, target)
    finding_groups: dict[tuple[str, str], list[tuple[int, ...]]] = defaultdict(list)
    for f in result.findings:
        if f.confidence != "elevated":
            continue
        actor, target = _attribute(f.seqs, by_seq)
        if actor is None or target is None:
            continue
        finding_groups[(actor, target)].append(f.seqs)

    # attribute patterns to the same (actor, target) space
    pattern_groups: dict[tuple[str, str], list[Pattern]] = defaultdict(list)
    for p in patterns:
        actor, target = _attribute(p.seqs, by_seq)
        if actor is not None and target is not None:
            pattern_groups[(actor, target)].append(p)

    out: list[Campaign] = []
    for (actor, target), finding_seqs in finding_groups.items():
        if len(finding_seqs) < min_findings:
            continue
        pats = pattern_groups.get((actor, target), [])
        # the campaign's span is defined by its corroborated elevated findings,
        # not by attached patterns (which may reach adjacent material).
        seqs = sorted({s for fs in finding_seqs for s in fs})
        timestamps = sorted((by_seq[s].timestamp for s in seqs if s in by_seq),
                            key=_ts_sort_key)
        span = (timestamps[0], timestamps[-1]) if timestamps else ("", "")
        pat_names = tuple(sorted({p.name for p in pats}))
        out.append(Campaign(
            actor=actor, target=target, patterns=pat_names,
            findings=tuple(sorted(finding_seqs)), seqs=tuple(seqs), span=span,
            summary=f"{actor} sustains {len(finding_seqs)} elevated findings "
                    f"against '{target}' ({span[0]} .. {span[1]})"
                    + (f"; patterns: {', '.join(pat_names)}" if pat_names else ""),
        ))
    out.sort(key=lambda c: (c.actor, c.target))
    return out
