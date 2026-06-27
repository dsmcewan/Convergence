"""Layer 4 - domain convergence.

Each message carries a topical `domain`. When the same concrete anchor (a
content word or bigram) shows up across two or more *independent* domains, the
domains are converging on one underlying decision or event - the "all roads
lead to the same place" signal. Stopwords and short tokens are excluded so the
anchor is something specific, not connective tissue.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from convergence.text import ngrams, tokens

STOPWORDS = {
    "the", "a", "an", "and", "or", "to", "of", "for", "in", "on", "is", "are",
    "was", "were", "be", "i", "you", "we", "it", "this", "that", "so", "but",
    "not", "my", "your", "our", "with", "have", "has", "had", "will", "can",
    "please", "just", "do", "did", "if", "as", "at", "by", "me", "us", "them",
    # Generic verbs/fillers: common across any topic, so they are not anchors.
    "says", "said", "say", "get", "got", "go", "going", "want", "wants", "know",
    "need", "let", "make", "made", "take", "takes", "see", "thing", "things",
    "today", "really", "one", "back", "now", "then", "here", "there", "up",
    "out", "also", "ok", "yes", "no", "like", "what", "when", "how", "about",
    # Function words + generic fillers that outranked substantive anchors by raw
    # domain count on real corpora (a word in *many* domains is usually
    # generic, not a strong convergence). Topical/temporal anchors that matter in
    # a custody record (weekend, night, exchange, schedule, parenting, ...) are
    # deliberately NOT here.
    "would", "from", "which", "they", "been", "after", "again", "still", "over",
    "soon", "last", "later", "following", "good", "sure", "give", "given",
    "asked", "thank", "i'll",
    # Quantifiers, modals, and inflected forms of generic verbs (do/have/be) — the
    # tail that surfaces once the first batch is removed. Inflection is why a flat
    # word-list leaks: "do" was stopped but "doing" was not.
    "every", "each", "many", "much", "most", "could", "should", "might", "must",
    "doing", "having", "being", "does", "getting",
}


@dataclass(frozen=True)
class Convergence:
    domains: tuple[str, ...]
    seqs: tuple[int, ...]
    anchor: str


def _candidates(toks: list[str]) -> set[str]:
    cands = {t for t in toks if len(t) >= 4 and t not in STOPWORDS}
    for bg in ngrams(toks, 2):
        # Require >=3 chars per bigram word so split contractions ("she s")
        # and other one/two-letter fragments never become anchors.
        if all(len(w) >= 3 and w not in STOPWORDS for w in bg):
            cands.add(" ".join(bg))
    return cands


def find_convergences(messages, min_domains: int = 2):
    occ: dict[str, set[tuple[int, str]]] = defaultdict(set)
    for m in messages:
        # Canonicalize the domain so case-only variants (real corpora:
        # "MEDICAL" vs "medical") count as one domain, not two.
        canon = m.domain.strip().casefold()
        for c in _candidates(tokens(m.body)):
            occ[c].add((m.seq, canon))

    groups: dict[tuple, list[str]] = defaultdict(list)
    for anchor, pairs in occ.items():
        domains = tuple(sorted({d for _, d in pairs}))
        seqs = tuple(sorted({s for s, _ in pairs}))
        if len(domains) >= min_domains and len(seqs) >= 2:
            groups[(domains, seqs)].append(anchor)

    # Collapse anchors that describe the exact same (domains, seqs) to the most
    # specific one (longest), so "extra" and "extra hours" don't both report.
    results = [
        Convergence(domains=key[0], seqs=key[1], anchor=sorted(anchors, key=lambda a: (-len(a), a))[0])
        for key, anchors in groups.items()
    ]
    results.sort(key=lambda c: (c.domains, c.anchor))
    return results
