"""Layer 6 - cross-channel correlation.

Where Layer 3 tests a claim against a structured *records* set, Layer 6 tests it
against the sender's own words in a *second channel*. People speak differently to
different audiences: the formal, court-facing channel makes favorable claims ("I
have always kept you informed"); the casual channel carries the admission that
contradicts it ("forgot to tell you..."). This layer aligns the two by **sender**
and **predicate** and flags the divergence on the primary-channel message, citing
the cross-channel message that impeaches it.

Like every other layer it is deterministic and refuses to invent: a divergence is
emitted only when the same sender both makes the claim here and admits otherwise
there. It is *substantive* - an actual move - and so can anchor an elevated finding,
but (like all layers) only once a second layer corroborates it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from convergence.corpus import Message
from convergence.text import normalize


@dataclass(frozen=True)
class _CrossRule:
    predicate: str
    claimed: str           # the favorable value asserted in the primary channel
    actual: str            # the value the cross channel evidences
    claim: re.Pattern      # favorable claim, primary channel
    admission: re.Pattern  # contradicting admission, cross channel


# Extensible registry; one rule per predicate. Both patterns run over normalized text.
_CROSS_RULES: list[_CrossRule] = [
    _CrossRule(
        predicate="kept_informed",
        claimed="kept the other parent informed",
        actual="withheld a disclosure",
        claim=re.compile(r"\balways (?:kept|keep) (?:you |him |her |them )?(?:fully )?"
                         r"(?:informed|updated|apprised|in the loop)\b"),
        admission=re.compile(r"\b(?:forgot to (?:tell|mention|inform)|"
                             r"did ?n'?t (?:tell|mention|inform|notify)|never told)\b"),
    ),
    _CrossRule(
        predicate="paid_ontime",
        claimed="paid every expense on time",
        actual="skipped a payment",
        claim=re.compile(r"\balways paid\b"),
        admission=re.compile(r"\b(?:skipped (?:paying|payment|the)|never paid|"
                             r"did ?n'?t pay|forgot to pay)\b"),
    ),
]


@dataclass(frozen=True)
class ChannelDivergence:
    seq: int             # primary-channel message making the claim
    sender: str
    predicate: str
    claimed: str         # value asserted in the primary channel
    actual: str          # value evidenced in the cross channel
    cross_seq: int       # the cross-channel message that contradicts it
    basis: str


def find_cross_channel_divergences(primary: list[Message], cross: list[Message]) -> list[ChannelDivergence]:
    out: list[ChannelDivergence] = []
    for rule in _CROSS_RULES:
        # earliest contradicting admission per sender in the cross channel
        admissions: dict[str, int] = {}
        for m in sorted(cross, key=lambda x: x.seq):
            if rule.admission.search(normalize(m.body)):
                admissions.setdefault(m.sender, m.seq)
        for m in primary:
            if not rule.claim.search(normalize(m.body)):
                continue
            cross_seq = admissions.get(m.sender)
            if cross_seq is None:
                continue
            out.append(ChannelDivergence(
                seq=m.seq,
                sender=m.sender,
                predicate=rule.predicate,
                claimed=rule.claimed,
                actual=rule.actual,
                cross_seq=cross_seq,
                basis=f"{m.sender} claims '{rule.claimed}' here; other channel shows "
                      f"'{rule.actual}' (seq {cross_seq})",
            ))
    out.sort(key=lambda d: (d.seq, d.predicate))
    return out
