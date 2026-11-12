"""Public-record incident/control-question ledger, supplementary to Convergence.

Missing public evidence remains an unresolved question, never proof of nonperformance.
Journalism quoting one briefing does not become independent corroboration.
No negligence, intent or counterfactual casualty verdict is emitted.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any


def _unique_ids(rows: list[dict[str, Any]], label: str) -> None:
    ids = [r.get("id") for r in rows]
    if any(not isinstance(i, str) or not i for i in ids):
        raise ValueError(f"{label} contains an empty/invalid id")
    if len(ids) != len(set(ids)):
        raise ValueError(f"duplicate {label} id")


def audit_causal_chain(case: dict[str, Any]) -> dict[str, Any]:
    """Compare publicly reported events to independently answerable controls.

    Requires sources[{id,origin,url}], events[{id,seq,kind,text,source_ids,
    signals}], questions[{id,title,positive_signals,negative_signals,
    exposure_signals,required_evidence,limit}].
    """
    sources, events, questions = case["sources"], case["events"], case["questions"]
    for label, rows in (("source", sources), ("event", events), ("question", questions)):
        _unique_ids(rows, label)
    source_map = {s["id"]: s for s in sources}
    if not all(s.get("origin") and s.get("url") for s in sources):
        raise ValueError("sources require origin and URL")
    if len({e["seq"] for e in events}) != len(events):
        raise ValueError("duplicate event sequence")

    signal_map: dict[str, list[dict[str, Any]]] = defaultdict(list)
    chronology = []
    for ev in sorted(events, key=lambda r: (r["seq"], r["id"])):
        if not ev.get("source_ids") or not all(s in source_map for s in ev["source_ids"]):
            raise ValueError(f"event {ev['id']} has missing/unknown source")
        for signal in ev.get("signals", []):
            signal_map[signal].append(ev)
        chronology.append({
            "id": ev["id"], "sequence": ev["seq"],
            "reported_time": ev.get("time", "unspecified"),
            "description": ev["text"], "kind": ev["kind"],
            "source_ids": sorted(set(ev["source_ids"])),
            "origin_groups": sorted({source_map[s]["origin"] for s in ev["source_ids"]}),
            "evidence_level": ev.get("evidence_level", "reported"),
        })

    gate_results = []
    for q in sorted(questions, key=lambda r: r["id"]):
        positive = sorted({e["id"] for tag in q["positive_signals"] for e in signal_map[tag]})
        negative = sorted({e["id"] for tag in q["negative_signals"] for e in signal_map[tag]})
        exposure = sorted({e["id"] for tag in q.get("exposure_signals", [])
                           for e in signal_map[tag]})
        if positive and negative:
            status = "conflicting_evidence_requires_review"
        elif positive:
            status = "affirmative_action_reported"
        elif negative:
            status = "adverse_outcome_or_nonaction_reported"
        else:
            status = "unresolved_in_reviewed_public_record"
        gate_results.append({
            "id": q["id"], "title": q["title"], "assessment": status,
            "positive_event_ids": positive, "negative_event_ids": negative,
            "exposure_event_ids": exposure,
            "required_evidence": q["required_evidence"],
            "interpretive_limit": q["limit"],
        })

    return {
        "case_id": case["case_id"], "as_of": case["as_of"],
        "source_count": len(sources),
        "distinct_origin_count": len({s["origin"] for s in sources}),
        "chronology": chronology, "control_questions": gate_results,
        "summary": {
            "unresolved": sum(g["assessment"] == "unresolved_in_reviewed_public_record"
                              for g in gate_results),
            "reported_affirmative": sum(g["assessment"] == "affirmative_action_reported"
                                        for g in gate_results),
            "reported_adverse": sum(g["assessment"] == "adverse_outcome_or_nonaction_reported"
                                    for g in gate_results),
        },
        "causation_verdict": "not_determined",
        "intent_verdict": "not_determined",
        "limitations": [
            "Known threat to a third party is not equivalent to Citi knowing at the same time.",
            "A breached fence does not alone prove its design requirement was inadequate.",
            "Missing public documentation is not proof that warning or lockdown did not occur.",
            "One source repeated by multiple outlets is one underlying account.",
            "Post-event support cannot resolve pre-event control questions.",
            "A tribute is not expected to serve as an operational postmortem.",
            "No inference of coordinated messaging, negligence, or intent is authorized.",
        ],
    }
