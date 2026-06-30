"""Layer 3 - third-party referencing.

Test factual *claims* made in messages against an external records set and
surface contradictions. The first claim family is the denial-of-agreement
("I never agreed...", "we didn't approve..."). A denial is contradicted only
when a record shows agreement *on the same topic* (the record's predicate
shares a content word with the claim). When no record matches, nothing is
emitted - the engine never invents a contradiction it cannot ground.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from convergence.corpus import Message
from convergence.records import Record
from convergence.text import normalize, tokens

_DENIAL = re.compile(r"\bnever (agreed|approved|consented)\b|\b(didn't|did not) (agree|approve|consent)\b")  # noqa: E501
_PREDICATE_SKIP = {"agreed", "agree", "to", "of", "the"}


@dataclass(frozen=True)
class Contradiction:
    seq: int
    claim: str
    record_id: str | None
    contradicting_seq: int | None
    basis: str


def _predicate_topic(predicate: str) -> set[str]:
    return {p for p in predicate.split("_") if p not in _PREDICATE_SKIP and len(p) > 2}


def check_claims(messages: list[Message], records: list[Record]) -> list[Contradiction]:
    agreement_records = [
        r for r in records
        if (r.value is True or (isinstance(r.value, str) and r.value.strip().lower() == "true"))
        and "agree" in r.predicate
    ]
    out: list[Contradiction] = []
    for m in messages:
        if not _DENIAL.search(normalize(m.body)):
            continue
        claim_toks = set(tokens(m.body))
        for r in sorted(agreement_records, key=lambda r: r.id):
            if _predicate_topic(r.predicate) & claim_toks:
                out.append(
                    Contradiction(
                        seq=m.seq,
                        claim=m.body,
                        record_id=r.id,
                        contradicting_seq=r.source_seq,
                        basis=f"record {r.id}: {r.predicate}={r.value}",
                    )
                )
    out.sort(key=lambda c: (c.seq, c.record_id or ""))
    return out
