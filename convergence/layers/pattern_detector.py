"""Layer 1 - communicative-tactic detection.

Tags a message with the *move* it is making, not just its words. The first
tactic is **borrow-authority / displace-accountability**: presenting a
decision as the dictate of an external authority ("the platform's policy
says...", "my accountant says...", "the doctor recommended...") so the
speaker never has to own it.

The precision that matters is the negative case: merely *mentioning* an
authority is not the tactic. The authority must be bound to an assertion
verb close by. Stating a fact directly and offering the document ("I can
send you the policy section") is the opposite move and must not fire.
"""
from __future__ import annotations

from dataclasses import dataclass

from convergence.corpus import Message
from convergence.text import tokens

AUTHORITY_ROOTS = {
    "platform", "policy", "accountant", "doctor", "lawyer", "attorney",
    "court", "hr", "mediator", "teacher", "pediatrician", "bank",
}
ASSERTION_VERBS = {
    "says", "said", "recommends", "recommended", "requires", "required",
    "advises", "advised", "states", "stated",
}
WINDOW = 3  # tokens between authority and assertion verb


@dataclass(frozen=True)
class PatternHit:
    seq: int
    tactic: str
    cue: str
    authority: str | None


def _root(tok: str) -> str:
    return tok[:-2] if tok.endswith("'s") else tok


def detect_patterns(messages: list[Message]) -> list[PatternHit]:
    hits: list[PatternHit] = []
    for m in messages:
        toks = tokens(m.body)
        authorities = [(i, _root(t)) for i, t in enumerate(toks) if _root(t) in AUTHORITY_ROOTS]
        verbs = [i for i, t in enumerate(toks) if t in ASSERTION_VERBS]

        best = None  # (distance, authority_pos, root, verb_pos)
        for apos, root in authorities:
            for vpos in verbs:
                dist = abs(apos - vpos)
                if dist <= WINDOW:
                    cand = (dist, apos, root, vpos)
                    if best is None or cand < best:
                        best = cand
        if best is not None:
            _, apos, root, vpos = best
            lo, hi = min(apos, vpos), max(apos, vpos)
            cue = " ".join(toks[lo : hi + 1])
            hits.append(PatternHit(seq=m.seq, tactic="borrow_authority", cue=cue, authority=root))

    hits.sort(key=lambda h: (h.seq, h.tactic))
    return hits
