"""Verified behavior detectors.

These fragment families were PROPOSED by the investigator and SHIPPED only after
the deterministic verifier (`investigator.verify`) confirmed each fires on its
target dynamic type(s) without false-firing on the benign corpora (cooperative,
parallel). The agent proposes; the verifier decides; only survivors live here.

Provenance:
  * seed proposals -> shipped: triangulation, derogation; rejected: access_gatekeeping.
  * multi-agent proposals (6) -> shipped: isolation, surveillance_framing; rejected:
    conditional_threat (fired 0 in reality despite the agent self-certifying it),
    financial_leverage, love_bombing, stonewalling (each below the evidence bar).

Deterministic.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from convergence.text import normalize


@dataclass(frozen=True)
class BehaviorHit:
    seq: int
    behavior: str
    cue: str


# (name, compiled pattern) — verified survivors only. See investigator.propose_seed
# for the proposals and verify() for the adversarial gate each one cleared.
_SHIPPED = [
    ("triangulation", re.compile(
        r"\b(said|told me|mentioned|says) (you|that you)\b|"
        r"\bask(?:ing|ed)? (?:her|him|sofia|lily|the kids?) about\b|"
        r"\bthrough (?:a|our|the) (?:child|kid|daughter|son|\d+-year-old)\b")),
    ("derogation", re.compile(
        r"\b(as usual|as always|typical|clearly|the way you always|like you always)\b")),
    # --- shipped from the multi-agent proposer (independently verified) ---
    ("isolation", re.compile(
        r"(?:you can see (?:her|him|them) after|withholding (?:her|him|them)\b|"
        r"the alienation i(?:'|’)?ve been telling|telling everyone about|"
        r"aligning\b.{0,30}\bagainst|turn(?:ing|ed)? (?:her|him|them|the kids?|the child) against (?:you|me)|"  # noqa: E501
        r"won(?:'|’)?t (?:let|allow) (?:you|her|him) (?:see|visit)|not allowed to (?:see|visit)|"  # noqa: E501
        r"you don(?:'|’)?t need to see)")),
    ("surveillance_framing", re.compile(
        r"(?:who(?:'s| is| are| were)\s+(?:you|she|he|they)\s+(?:with|seeing|dating|texting|talking to))|"  # noqa: E501
        r"(?:where\s+(?:were|are|was)\s+you\s+(?:last night|saturday night|friday night|that night|all night|really|over the weekend))|"  # noqa: E501
        r"(?:who(?:'s| is| was)\s+(?:this )?(?:new )?(?:guy|man|woman|boyfriend|girlfriend|person)\b)|"  # noqa: E501
        r"(?:are you (?:seeing|dating|sleeping with|living with)\s+(?:someone|anyone))|"
        r"(?:(?:she|he|the kids?|sofia|lily)\s+(?:said|told me|mentioned|says)\s+(?:you|there)\b[^.?!]{0,40}\b"  # noqa: E501
        r"(?:at your place|over|sleepover|new |a man|a woman|drinking|wine|texting|out late|dropped (?:her|him|them) (?:at|off)))|"  # noqa: E501
        r"(?:i(?:'m| am)?\s*(?:always|just)?\s*(?:watching out for|keeping an eye on|looking out for)\s+(?:her|him|them|the kids?))|"  # noqa: E501
        r"(?:stop asking (?:her|him|them|the kids?|sofia|lily)\s+about my (?:personal life|whereabouts|dating|private life))")),  # noqa: E501
]


def tag_behaviors(messages) -> list[BehaviorHit]:
    out: list[BehaviorHit] = []
    for m in messages:
        t = normalize(m.body)
        for name, rx in _SHIPPED:
            hit = rx.search(t)
            if hit:
                out.append(BehaviorHit(m.seq, name, hit.group(0)))
    out.sort(key=lambda h: (h.seq, h.behavior))
    return out
