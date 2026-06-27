"""Layer 5 - fragment-level analysis.

Two products. `recurring_phrases` surfaces repeated n-grams. `detect_register_
anomalies` flags a message whose *register* departs from its own sender's
baseline - a normally-casual author suddenly writing in formal/legalistic
register. The baseline for each message is the mean of the sender's *other*
messages (leave-one-out), so a single outlier can't pull its own baseline
toward itself. Everything is rounded before comparison so runs are identical.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from convergence.text import ngrams, tokens

FORMAL_LEXICON = {
    "pursuant", "policy", "approving", "authorization", "authorize", "review",
    "accordance", "consent", "provision", "hereby", "basis", "stated",
    "require", "required", "custody", "order", "aforementioned", "herein",
}
_THRESHOLD = 0.15
_ROUND = 4


@dataclass(frozen=True)
class RegisterAnomaly:
    seq: int
    sender: str
    score: float
    reason: str


@dataclass(frozen=True)
class RecurringPhrase:
    ngram: tuple[str, ...]
    count: int
    seqs: tuple[int, ...]


def _features(body: str) -> tuple[float, float, float]:
    toks = tokens(body)
    if not toks:
        return (0.0, 0.0, 0.0)
    avg_len = sum(len(t) for t in toks) / len(toks) / 10.0
    formal_share = sum(1 for t in toks if t in FORMAL_LEXICON) / len(toks)
    ttr = len(set(toks)) / len(toks)
    return (avg_len, formal_share, ttr)


def detect_register_anomalies(messages, threshold: float = _THRESHOLD) -> list[RegisterAnomaly]:
    by_sender: dict[str, list] = defaultdict(list)
    for m in messages:
        by_sender[m.sender].append(m)

    out: list[RegisterAnomaly] = []
    for sender, msgs in by_sender.items():
        if len(msgs) < 2:
            continue  # no baseline without at least one other message
        feats = {m.seq: _features(m.body) for m in msgs}
        for m in msgs:
            others = [feats[o.seq] for o in msgs if o.seq != m.seq]
            base = tuple(sum(f[i] for f in others) / len(others) for i in range(3))
            score = round(sum(abs(feats[m.seq][i] - base[i]) for i in range(3)), _ROUND)
            if score >= threshold:
                out.append(RegisterAnomaly(
                    seq=m.seq, sender=sender, score=score,
                    reason=f"register deviates from {sender}'s baseline (score {score})",
                ))
    out.sort(key=lambda a: (-a.score, a.seq))
    return out


def recurring_phrases(messages, n: int = 2, min_count: int = 2) -> list[RecurringPhrase]:
    counts: dict[tuple, int] = defaultdict(int)
    seqs: dict[tuple, set] = defaultdict(set)
    for m in messages:
        for g in ngrams(tokens(m.body), n):
            counts[g] += 1
            seqs[g].add(m.seq)
    out = [
        RecurringPhrase(ngram=g, count=counts[g], seqs=tuple(sorted(seqs[g])))
        for g in counts if counts[g] >= min_count
    ]
    out.sort(key=lambda p: (-p.count, p.ngram))
    return out
