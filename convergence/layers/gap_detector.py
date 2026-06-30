"""Layer 2 — record-vs-exhibit reconstruction ("frog DNA").

Given the complete record and a *subset* of it put forward as an exhibit,
reconstruct what was removed. Excerpting is normal; the signal is *where* the cuts fall. A
message removed from the middle of one continuous conversation — its nearest
shown neighbors on both sides share its thread — is a **within-thread omission**,
the kind that can change meaning. Cuts at a thread boundary are ordinary trims.

You cannot see a splice by looking at the splice. You rebuild the whole sequence
and watch which interior pieces are gone.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from convergence.corpus import Message


@dataclass(frozen=True)
class Gap:
    seq: int                 # the omitted sequence number
    prev_seq: int | None     # nearest shown message before it
    next_seq: int | None     # nearest shown message after it
    within_thread: bool      # True => cut from inside one continuous conversation


def find_omissions(full: list[Message], included_seqs: Iterable[int]) -> list[Gap]:
    included = set(included_seqs)
    ordered = sorted(full, key=lambda m: m.seq)
    by_seq = {m.seq: m for m in ordered}
    shown_seqs = [m.seq for m in ordered if m.seq in included]

    gaps: list[Gap] = []
    for m in ordered:
        if m.seq in included:
            continue
        prev = max((s for s in shown_seqs if s < m.seq), default=None)
        nxt = min((s for s in shown_seqs if s > m.seq), default=None)
        within = (
            prev is not None
            and nxt is not None
            and by_seq[prev].thread == m.thread
            and by_seq[nxt].thread == m.thread
        )
        gaps.append(Gap(seq=m.seq, prev_seq=prev, next_seq=nxt, within_thread=within))
    return gaps
