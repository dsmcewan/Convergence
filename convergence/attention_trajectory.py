"""Auditable attention trajectories for explicit communication links.

Frames are supplied with exact text anchors; this deliberately does not guess
a topic from positive adjectives. Measures focus in the observed sample and
topic changes across *explicitly linked* replies. Neither a topic change nor
relative share establishes motive, audience persuasion, or causal impact.

Single posts without accessible replies can be described, but not assigned
downstream effects. No change is made to Convergence's verdict engine.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any

TOPICS = frozenset({
    "memorial", "heroism", "mutual_support", "institutional_virtue",
    "post_event_support", "security_response", "pre_attack_prevention",
    "institutional_responsibility", "other",
})
_RESPONSE_TOPICS = frozenset({
    "heroism", "mutual_support", "institutional_virtue", "post_event_support",
})
_COVERAGES = frozenset({"excerpt", "reported_quote", "complete_post", "complete_thread"})


def _date(raw: str) -> datetime:
    try:
        date = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid timestamp: {raw!r}") from exc
    if date.tzinfo is not None:
        # Never compare aware timestamps with naive timestamps.
        raise ValueError("timestamps must use local ISO date or naive datetime consistently")
    return date


def _validate_units(units: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    ids = [r.get("id") for r in units]
    if len(ids) != len(set(ids)) or any(not isinstance(i, str) or not i for i in ids):
        raise ValueError("unit IDs must be unique, nonempty strings")
    by_id = {u["id"]: u for u in units}
    for u in units:
        required = ("id", "actor", "role", "thread_id", "timestamp",
                    "source", "coverage", "text")
        if any(not isinstance(u.get(key), str) or not u[key] for key in required):
            raise ValueError(f"unit {u['id']} is missing required information")
        _date(u["timestamp"])
        if u["coverage"] not in _COVERAGES:
            raise ValueError(f"invalid coverage for {u['id']}")
        frames = u.get("frames", [])
        if not isinstance(frames, list):
            raise ValueError("frames must be a list of exact, grounded text anchors")
        if len({f.get("topic") for f in frames}) != len(frames):
            raise ValueError(f"duplicate topics in {u['id']}")
        for frame in frames:
            if frame.get("topic") not in TOPICS:
                raise ValueError(f"unknown topic: {frame.get('topic')!r}")
            quote = frame.get("quote")
            if not isinstance(quote, str) or not quote.strip():
                raise ValueError("each frame requires an exact text anchor")
            if quote.casefold() not in u["text"].casefold():
                raise ValueError(f"frame anchor missing from unit {u['id']}: {quote!r}")
        for name in ("asks_issue_ids", "addresses_issue_ids"):
            if not isinstance(u.get(name, []), list):
                raise ValueError(f"{name} must be a list")
            if any(not isinstance(i, str) or not i for i in u.get(name, [])):
                raise ValueError(f"{name} must contain nonempty strings")
        parent = u.get("reply_to")
        if parent is not None:
            if parent not in by_id or parent == u["id"]:
                raise ValueError(f"invalid reply_to: {parent!r}")
            p = by_id[parent]
            if p["thread_id"] != u["thread_id"]:
                raise ValueError("reply chain cannot cross threads")
            if _date(p["timestamp"]) > _date(u["timestamp"]):
                raise ValueError("reply precedes parent")
    # Explicit edges must form a DAG even for equal timestamps.
    for u in units:
        visited = set()
        cursor = u["id"]
        while cursor is not None:
            if cursor in visited:
                raise ValueError(f"reply cycle involving {cursor}")
            visited.add(cursor)
            cursor = by_id[cursor].get("reply_to")
    return by_id


def _focus(units: list[dict[str, Any]]) -> dict[str, Any]:
    # Multiple topics can occur in one unit. Shares do NOT sum to 100%.
    out = []
    for topic in sorted(TOPICS):
        ids = sorted(u["id"] for u in units
                     if any(frame["topic"] == topic for frame in u.get("frames", [])))
        if ids:
            out.append({
                "topic": topic, "units": len(ids), "unit_ids": ids,
                "share_of_units": round(len(ids) / len(units), 4),
            })
    return {
        "units": len(units),
        "multi_label_denominator": "all_units",
        "topics": out,
    }


def analyze_attention(
    units: list[dict[str, Any]],
    actions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Describe foregrounded themes and linked reply shifts, not causal influence.

    A unit is one sourced message/excerpt. Each frame has {topic, quote}; every
    quote must appear verbatim within the supplied text. For a question-reply
    assessment, author coding supplies asks_issue_ids and addresses_issue_ids;
    the tool reports coding, not whether the answer was substantively adequate.
    """
    by_id = _validate_units(units)
    actions = actions or []
    action_ids = [a.get("id") for a in actions]
    if len(action_ids) != len(set(action_ids)):
        raise ValueError("action ids must be unique")

    ordered = sorted(units, key=lambda u: (_date(u["timestamp"]), u["id"]))
    roles = sorted({u["role"] for u in units})
    focus_by_role = {
        role: _focus([u for u in ordered if u["role"] == role])
        for role in roles
    }
    by_day: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for u in ordered:
        by_day[u["timestamp"][:10]].append(u)
    daily = [
        {"date": day, **_focus(by_day[day])}
        for day in sorted(by_day)
    ]

    edges = []
    for u in ordered:
        p = by_id.get(u.get("reply_to"))
        if p is None:
            continue
        parent_topics = {f["topic"] for f in p.get("frames", [])}
        child_topics = {f["topic"] for f in u.get("frames", [])}
        unanswered = sorted(set(p.get("asks_issue_ids", []))
                            - set(u.get("addresses_issue_ids", [])))
        added = sorted(child_topics - parent_topics)
        dropped = sorted(parent_topics - child_topics)
        shift = "not_classified"
        if "pre_attack_prevention" in parent_topics and (
            "pre_attack_prevention" not in child_topics
            and child_topics.intersection(_RESPONSE_TOPICS)
        ):
            shift = "prevention_to_response_in_direct_reply"
        elif "pre_attack_prevention" in child_topics and (
            "pre_attack_prevention" not in parent_topics
        ):
            shift = "toward_prevention_in_direct_reply"
        elif added or dropped:
            shift = "topic_change_in_direct_reply"
        edges.append({
            "parent_id": p["id"], "reply_id": u["id"],
            "parent_actor": p["actor"], "reply_actor": u["actor"],
            "added_topics": added, "dropped_topics": dropped,
            "unaddressed_parent_issue_ids_in_reply": unanswered,
            "explicitly_addressed_parent_issue_ids": sorted(
                set(p.get("asks_issue_ids", []))
                & set(u.get("addresses_issue_ids", []))
            ),
            "shift": shift,
            "interpretation": "observed_explicit_reply_only",
        })

    traces = []
    for action in sorted(actions, key=lambda a: a.get("id", "")):
        if not isinstance(action.get("id"), str) or not action["id"]:
            raise ValueError("invalid action ID")
        root = by_id.get(action.get("unit_id"))
        if root is None:
            raise ValueError(f"action {action['id']} references missing unit")
        replies = [u for u in ordered if u.get("reply_to") == root["id"]]
        downstream = [u for u in replies if u["actor"] != root["actor"]]
        traces.append({
            "action_id": action["id"],
            "source_unit_id": root["id"],
            "action_kind": action.get("kind", "communication"),
            "direct_replies_in_sample": len(replies),
            "other_actor_direct_replies": len(downstream),
            "other_actor_reply_focus": _focus(downstream),
            "observability": (
                "linked_replies_present_not_causal_evidence"
                if downstream else "downstream_effect_not_measurable_from_sample"
            ),
        })
    return {
        "unit_count": len(units),
        "coverage": {
            "complete_post_units": sum(
                u["coverage"] in {"complete_post", "complete_thread"} for u in units
            ),
            "partial_or_quoted_units": sum(
                u["coverage"] in {"excerpt", "reported_quote"} for u in units
            ),
            "sampling": "supplied_nonrandom_communications_only",
        },
        "observed_focus": _focus(ordered),
        "focus_by_role": focus_by_role,
        "daily_focus": daily,
        "direct_reply_transitions": edges,
        "communication_action_traces": traces,
        "measured_audience_attention_change": "not_established",
        "causal_message_effect": "not_established",
        "limitations": [
            "A topic absent in a supplied excerpt may appear in the complete post.",
            "Observed focus is a proportion of coded units, not readership or attention.",
            "Shares may exceed 100% in total because topics are multi-label.",
            "Only explicit reply links support transition descriptions.",
            "A topic shift is not proof of deliberate diversion.",
            "Direct replies are neither all readers nor a representative audience.",
            "Action effects require comparable longitudinal observations and controls.",
            "Actual security control execution cannot be inferred from public rhetoric.",
        ],
    }
