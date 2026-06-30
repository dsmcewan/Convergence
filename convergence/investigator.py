"""The investigator — propose new fragment families, then adversarially verify.

The detector has known blind spots (triangulation-through-child, derogation-via-
attribution) that the conflicted/covert corpora exhibit but no current fragment
family catches. Closing them is open-ended research, so it is the one place an
*agent* is justified: parallel agents PROPOSE candidate fragment families; this
module's deterministic verifier DECIDES which ship.

The split is the whole point (cf. "Building effective agents"): the LLM proposes,
deterministic code judges. An agent never grades its own homework — a candidate
ships only if it fires on its target type(s) and does not over-fire on the clearly-
benign corpora (cooperative, parallel). `propose_seed()` is the pluggable proposer
(swap in a multi-agent Workflow); `verify()` is the judge and the tool the agents call.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from convergence.corpus import load_corpus
from convergence.text import normalize

# corpora considered unambiguously benign — a real family must stay quiet here
BENIGN_TYPES = ("cooperative", "parallel")
_MIN_TARGET = 2     # must fire on at least this many target-corpus messages
_MAX_FALSE = 0      # must not fire on any benign-corpus message


@dataclass(frozen=True)
class Candidate:
    name: str
    target_types: tuple          # which corpus types it should fire on
    pattern: str                 # proposed regex (string)
    rationale: str = ""          # the proposer's reasoning (agent-supplied)


@dataclass(frozen=True)
class Verdict:
    candidate: Candidate
    per_corpus: dict             # corpus name -> match count
    fires_on_target: int
    false_positives: int
    ship: bool
    detail: str = ""


def _count(pattern: re.Pattern, messages) -> int:
    return sum(1 for m in messages if pattern.search(normalize(m.body)))


def verify(candidate: Candidate, corpora: dict) -> Verdict:
    """corpora: {type_name: [Message, ...]}. Deterministic adversarial check.

    Agent-proposed patterns are untrusted: an uncompilable regex auto-rejects
    rather than crashing the verifier."""
    try:
        rx = re.compile(candidate.pattern)
    except re.error as exc:
        return Verdict(candidate, {}, 0, 0, False, f"rejected: invalid regex ({exc})")
    per = {name: _count(rx, msgs) for name, msgs in corpora.items()}
    fires = sum(per[t] for t in candidate.target_types if t in per)
    false_pos = sum(per[t] for t in BENIGN_TYPES if t in per)
    ship = fires >= _MIN_TARGET and false_pos <= _MAX_FALSE
    why = ("ships: fires on target, quiet on benign" if ship
           else "rejected: " + ("silent on target" if fires < _MIN_TARGET else "over-fires on benign"))  # noqa: E501
    return Verdict(candidate, per, fires, false_pos, ship, why)


def propose_seed() -> list:
    """Seed proposals for the known gaps. This is the pluggable proposer step —
    a multi-agent Workflow can replace it, each agent returning one Candidate."""
    return [
        Candidate("triangulation", ("conflicted", "coercive"),
                  r"\b(said|told me|mentioned|says) (you|that you)\b|"
                  r"\bask(?:ing|ed)? (?:her|him|sofia|lily|the kids?) about\b|"
                  r"\bthrough (?:a|our|the) (?:child|kid|daughter|son|\d+-year-old)\b",
                  "child used as messenger/informant"),
        Candidate("derogation", ("conflicted", "high_conflict"),
                  r"\b(as usual|as always|typical|clearly|the way you always|like you always)\b",
                  "contempt leaking through attribution"),
        Candidate("access_gatekeeping", ("coercive",),
                  r"\b(doesn't want to (?:come|go|see you)|is staying with me|"
                  r"keeping (?:her|him)|not (?:sending|bringing) (?:her|him))\b",
                  "blocking the other parent's access"),
    ]


def investigate(data_dir) -> list:
    """Run the full propose -> verify pass over the dynamics corpora."""
    data_dir = Path(data_dir)
    corpora = {}
    for t in ("cooperative", "parallel", "conflicted", "high_conflict", "coercive"):
        corpora[t] = load_corpus(data_dir / f"dyn_{t}.json")
    return [verify(c, corpora) for c in propose_seed()]
