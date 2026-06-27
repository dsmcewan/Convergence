"""Deterministic text helpers shared by the analytical layers.

Stdlib only. No language model, no randomness, no I/O — the same input always
produces the same tokens. Detection in this engine must be reproducible byte for
byte, so every layer that touches raw text routes through here.
"""
from __future__ import annotations

import re

_WORD = re.compile(r"[a-z0-9']+")
_WS = re.compile(r"\s+")
# Curly/typographic apostrophes fold to a straight ' so contractions stay one
# token (real corpora — email, app exports — use U+2019; the synthetic data uses ').
_APOSTROPHES = str.maketrans({"‘": "'", "’": "'", "ʼ": "'"})


def normalize(text: str) -> str:
    return _WS.sub(" ", text.translate(_APOSTROPHES).lower()).strip()


def tokens(text: str) -> list[str]:
    return _WORD.findall(normalize(text))


def ngrams(toks: list[str], n: int) -> list[tuple[str, ...]]:
    if n <= 0 or len(toks) < n:
        return []
    return [tuple(toks[i : i + n]) for i in range(len(toks) - n + 1)]
