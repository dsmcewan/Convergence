"""Curated Benoit-Blanc lecture layer over the generic engine output.

This is the ONLY web module that imports the Blanc narrator. The generic engine
serialization (web/serialize.py) does not depend on this module; the lecture demo
composes the generic core with the curated section here.
"""
from __future__ import annotations

from typing import Any

from convergence.composition import find_campaigns, find_patterns
from convergence.engine import Finding
from convergence.narration import BlancNarrator, narrate_composition
from web.serialize import load_analysis, serialize_engine


def _finding_blanc_narration(f: Finding) -> str:
    if f.confidence == "elevated":
        return (
            f"Here the threads meet: seqs {list(f.seqs)}, layers {', '.join(f.layers)}. "
            "Not a hunch, but corroboration."
        )
    return (
        f"Seqs {list(f.seqs)} remain low. Suggestive, perhaps, but the method refuses "
        "to elevate a lone thread."
    )


def serialize_curated(name: str) -> dict[str, Any]:
    messages, result, _ = load_analysis(name)
    patterns = find_patterns(result)
    campaigns = find_campaigns(result, messages)
    return {
        "narration_blanc": BlancNarrator(messages).narrate(result),
        "composition_blanc": narrate_composition(patterns, campaigns, voice="blanc"),
        "finding_blanc": [_finding_blanc_narration(f) for f in result.findings],
    }


def serialize_corpus(name: str) -> dict[str, Any]:
    """The full demo payload: generic engine core + the curated Blanc section."""
    return {**serialize_engine(name), "curated": serialize_curated(name)}
