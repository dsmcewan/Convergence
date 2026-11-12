"""Evidence-conservative review of public corporate statements.

This is an observational adapter, NOT a seventh verdict layer. A cue in a
statement is evidence only of wording appearing, not of intent, negligence,
coordination, or a security-control failure. Text excerpting cannot establish
absence from a full communication. Repetition is not independent corroboration.

The core Convergence engine and its promotion rules remain unchanged.
"""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

CUES = {
    "collective_care_directive": (
        r"\blook out for one another\b",
        r"\btake care of one another\b",
    ),
    "institutional_virtue_claim": (
        r"\bcommunities like citi[’']?s demonstrate\b",
        r"\bciti tampa has always been a tremendous force for good\b",
        r"\bciti has leaders and colleagues who genuinely care\b",
    ),
    "response_recognition": (
        r"\bsecurity team\b.{0,80}\b(?:brave|bravery|professionalism)\b",
        r"\bbrave actions of our security team\b",
    ),
    "proximity_claim": (r"\bprivilege of overseeing this site\b",),
    "named_victim": (r"\bleanne selman\b",),
    "announced_action": (
        r"\bcounseling and other resources available\b",
        r"\badditional security\b",
        r"\b\$250,000 contribution\b",
        r"\b\$250,000\b",
    ),
    "pre_attack_security_description": (r"\bchanging their security posture\b",),
}
COMPILED = {kind: tuple(re.compile(p, re.I) for p in patterns)
            for kind, patterns in CUES.items()}


def _validate(record: dict[str, Any]) -> None:
    for field in ("id", "actor", "date", "source", "text", "coverage"):
        if not isinstance(record.get(field), str) or not record[field].strip():
            raise ValueError(f"statement missing nonempty {field}: {record.get('id')!r}")
    if record["coverage"] not in {"full_screenshot", "excerpt", "reported_quote"}:
        raise ValueError(f"invalid coverage: {record['coverage']!r}")
    for action in record.get("reported_actions", []):
        if not all(action.get(k) for k in ("action_id", "description", "status")):
            raise ValueError(f"incomplete action for statement {record['id']}")
        if action["status"] not in {"announced", "reported", "firsthand_report"}:
            raise ValueError("unknown action evidence status")


def review(statements: list[dict[str, Any]]) -> dict[str, Any]:
    """Deterministic source-traceable wording/action ledger; no motive verdicts."""
    if len({s.get("id") for s in statements}) != len(statements):
        raise ValueError("duplicate statement id")
    for s in statements:
        _validate(s)
    observations: list[dict[str, str]] = []
    action_map: dict[str, dict[str, Any]] = {}
    for s in sorted(statements, key=lambda row: (row["date"], row["id"])):
        for label, patterns in COMPILED.items():
            matched = next((m for pat in patterns if (m := pat.search(s["text"]))), None)
            if matched:
                observations.append({
                    "statement_id": s["id"], "actor": s["actor"],
                    "label": label, "cue": matched.group(0),
                    "source": s["source"], "status": "wording_observed",
                })
        for item in s.get("reported_actions", []):
            aid = item["action_id"]
            if aid not in action_map:
                action_map[aid] = {
                    "action_id": aid, "description": item["description"],
                    "source_statement_ids": [], "statuses": [],
                    "verification": "source_reported_not_independently_audited",
                }
            action_map[aid]["source_statement_ids"].append(s["id"])
            action_map[aid]["statuses"].append(item["status"])
    by_label: dict[str, set[tuple[str, str]]] = defaultdict(set)
    for o in observations:
        by_label[o["label"]].add((o["actor"], o["statement_id"]))
    recurrences = []
    for label, pairs in sorted(by_label.items()):
        if len(pairs) >= 2 and len({actor for actor, _ in pairs}) >= 2:
            recurrences.append({
                "label": label, "statement_ids": sorted({sid for _, sid in pairs}),
                "actor_count": len({actor for actor, _ in pairs}),
                "interpretation": "cross_author_wording_recurrence_only",
            })
    for value in action_map.values():
        value["source_statement_ids"].sort()
        value["statuses"].sort()
    return {
        "statement_count": len(statements),
        "observations": sorted(observations, key=lambda x: (x["statement_id"], x["label"])),
        "recurrences": recurrences,
        "reported_actions": sorted(action_map.values(), key=lambda x: x["action_id"]),
        "verdict": "not_assessed",
        "disclaimers": [
            "A phrase match does not establish motive or manipulation.",
            "Repeated rhetoric does not prove coordinated messaging.",
            "An absent phrase in an excerpt does not establish a missing procedure.",
            "Announced actions are not verified execution or effectiveness.",
            "The existing Convergence evidence-promotion engine was not modified.",
        ],
    }
