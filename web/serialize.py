"""Serialize deterministic convergence results for the browser UI.

This module is the single seam between the engine and the web demo. It imports
the engine, composition, narration, and evaluation layers, then emits plain
JSON-able dictionaries. The engine package does not import this module.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from convergence.composition import find_campaigns, find_patterns
from convergence.coercion_grammar import match_grammar, tag_stages
from convergence.corpus import Message, load_corpus
from convergence.engine import EngineResult, Finding, Signal, run_engine
from convergence.evaluation import evaluate_dynamics
from convergence.narration import BlancNarrator, TemplateNarrator, narrate_composition
from convergence.records import load_records

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

CORPORA = {
    "contractor": ("sample_full.json", "sample_exhibit.json", "sample_records.json"),
    "coparenting": ("coparenting_full.json", "coparenting_exhibit.json", "coparenting_records.json"),
}
CHANNELS = {
    "channels": ("channels_formal.json", "channels_casual.json"),
}
DYNAMICS = {
    "cooperative": "dyn_cooperative.json",
    "parallel": "dyn_parallel.json",
    "conflicted": "dyn_conflicted.json",
    "high_conflict": "dyn_high_conflict.json",
    "coercive": "dyn_coercive.json",
}

CORPUS_LABELS = {
    "contractor": "Contractor record",
    "coparenting": "Coparenting record",
    "channels": "Two-channel record",
}


def corpus_names() -> list[str]:
    return [*CORPORA.keys(), *CHANNELS.keys()]


def load_analysis(name: str) -> tuple[list[Message], EngineResult, dict[str, Any]]:
    """Load one named demo corpus and return messages, result, and metadata."""
    if name in CORPORA:
        full_file, exhibit_file, records_file = CORPORA[name]
        messages = load_corpus(DATA / full_file)
        exhibit = json.loads((DATA / exhibit_file).read_text(encoding="utf-8"))
        records = load_records(DATA / records_file)
        result = run_engine(messages, included_seqs=set(exhibit["included_seqs"]), records=records)
        return messages, result, {
            "name": name,
            "label": CORPUS_LABELS[name],
            "mode": "exhibit-vs-full-record",
            "exhibit_label": exhibit.get("label", ""),
            "exhibit_note": exhibit.get("note", ""),
        }

    if name in CHANNELS:
        primary_file, cross_file = CHANNELS[name]
        messages = load_corpus(DATA / primary_file)
        cross_channel = load_corpus(DATA / cross_file)
        result = run_engine(messages, cross_channel=cross_channel)
        return messages, result, {
            "name": name,
            "label": CORPUS_LABELS[name],
            "mode": "cross-channel",
            "exhibit_label": "Formal channel checked against the casual channel",
            "exhibit_note": "Layer 6 compares a sender's formal claim against the same sender's own words elsewhere.",
        }

    raise KeyError(f"unknown corpus: {name}")


def serialize_corpus(name: str) -> dict[str, Any]:
    messages, result, meta = load_analysis(name)
    patterns = find_patterns(result)
    campaigns = find_campaigns(result, messages)

    return {
        "corpus": {
            **meta,
            "message_count": len(messages),
            "finding_count": len(result.findings),
            "elevated_count": sum(1 for f in result.findings if f.confidence == "elevated"),
            "low_count": sum(1 for f in result.findings if f.confidence == "low"),
        },
        "messages": [_message(m) for m in messages],
        "findings": [_finding(f, messages) for f in result.findings],
        "patterns": [_pattern(p) for p in patterns],
        "campaigns": [_campaign(c) for c in campaigns],
        "narration": {
            "plain": TemplateNarrator().narrate(result),
            "blanc": BlancNarrator(messages).narrate(result),
        },
        "composition_narration": {
            "plain": narrate_composition(patterns, campaigns, voice="plain"),
            "blanc": narrate_composition(patterns, campaigns, voice="blanc"),
        },
    }


def serialize_dynamics() -> dict[str, Any]:
    rows = []
    for name, filename in DYNAMICS.items():
        messages = load_corpus(DATA / filename)
        stage_hits = tag_stages(messages)
        matches = match_grammar(messages)
        complete = [m for m in matches if m.complete]
        rows.append({
            "name": name,
            "message_count": len(messages),
            "stage_hits": len(stage_hits),
            "complete_envelopes": len(complete),
            "coercive": name == "coercive",
            "matches": [_grammar_match(m) for m in matches],
        })

    evaluation = evaluate_dynamics(DATA)
    return {
        "rows": rows,
        "scorecard": {
            "tp": evaluation.tp,
            "fp": evaluation.fp,
            "fn": evaluation.fn,
            "tn": evaluation.tn,
            **{k: round(v, 3) for k, v in evaluation.metrics.items()},
        },
        "per_corpus": [
            {
                "name": c.name,
                "label": "coercive" if c.label else "other",
                "predicted": "coercive" if c.predicted else "other",
                "stage_hits": c.stage_hits,
                "complete_envelopes": c.envelopes,
                "correct": c.correct,
            }
            for c in evaluation.per_corpus
        ],
        "hard_negative": _hard_negative(evaluation.per_corpus),
    }


def serialize_index() -> dict[str, Any]:
    return {
        "title": "convergence",
        "tagline": "A deterministic communication-forensics engine.",
        "corpora": [
            {"name": name, "label": CORPUS_LABELS[name]}
            for name in corpus_names()
        ],
        "default_corpus": "contractor",
    }


def _message(m: Message) -> dict[str, Any]:
    return {
        "seq": m.seq,
        "thread": m.thread,
        "sender": m.sender,
        "timestamp": m.timestamp,
        "domain": m.domain,
        "body": m.body,
    }


def _signal(s: Signal) -> dict[str, Any]:
    return {
        "layer": s.layer,
        "seqs": list(s.seqs),
        "kind": s.kind,
        "detail": s.detail,
    }


def _finding(f: Finding, messages: list[Message]) -> dict[str, Any]:
    by_seq = {m.seq: m for m in messages}
    cited = [by_seq[s] for s in f.seqs if s in by_seq]
    return {
        "seqs": list(f.seqs),
        "confidence": f.confidence,
        "layers": list(f.layers),
        "summary": f.summary,
        "signals": [_signal(s) for s in f.signals],
        "messages": [_message(m) for m in cited],
        "narration": {
            "plain": _finding_narration(f),
            "blanc": _finding_blanc_narration(f),
        },
    }


def _finding_narration(f: Finding) -> str:
    layers = ", ".join(f.layers)
    return f"{f.confidence.title()} finding at seqs {list(f.seqs)} ({layers}). {f.summary}"


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


def _pattern(p) -> dict[str, Any]:
    return {
        "name": p.name,
        "kind": p.kind,
        "seqs": list(p.seqs),
        "detail": p.detail,
    }


def _campaign(c) -> dict[str, Any]:
    return {
        "actor": c.actor,
        "target": c.target,
        "patterns": list(c.patterns),
        "findings": [list(f) for f in c.findings],
        "seqs": list(c.seqs),
        "span": list(c.span),
        "summary": c.summary,
    }


def _grammar_match(match) -> dict[str, Any]:
    return {
        "thread": match.thread,
        "seqs": list(match.seqs),
        "stages_present": list(match.stages_present),
        "has_action": match.has_action,
        "has_fait_accompli": match.has_fait_accompli,
        "cycles": match.cycles,
        "status_quo_seq": match.status_quo_seq,
        "complete": match.complete,
        "summary": match.summary,
    }


def _hard_negative(rows) -> dict[str, Any] | None:
    negatives = [c for c in rows if not c.label]
    if not negatives:
        return None
    hard = max(negatives, key=lambda c: c.stage_hits)
    return {
        "name": hard.name,
        "stage_hits": hard.stage_hits,
        "complete_envelopes": hard.envelopes,
        "summary": (
            f"{hard.name} fired {hard.stage_hits} hostile stage-hits but "
            f"{hard.envelopes} false envelopes."
        ),
    }

