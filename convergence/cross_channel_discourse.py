"""Summarize a deliberately selected cross-channel communications evidence sample.

This is a source/coverage audit, not an inferential model. A researcher codes
brief summaries and topics with source URLs; the tool reports topic incidence
in the selected material and explicit references to another communication.
It never treats reaction-feed mirrors as authenticated original post permalinks
and never treats distinct channels as a common audience or a causal timeline.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

CHANNELS = frozenset({"institutional", "individual_posts", "public_forum"})
TOPICS = frozenset({
    "memorial", "personal_tribute", "personal_experience", "response_praise",
    "post_event_commitment", "mutual_support", "institutional_virtue",
    "training_context", "internal_comms_review", "prevention_question",
    "workplace_policy",
})


def compare_public_discourse(units: list[dict[str, Any]]) -> dict[str, Any]:
    """Return within-sample descriptive incidence, not an attention-shift verdict."""
    ids = [u.get("id") for u in units]
    if len(ids) != len(set(ids)) or not all(isinstance(i, str) and i for i in ids):
        raise ValueError("unique nonempty unit ids required")
    known = set(ids)
    for u in units:
        if u.get("channel") not in CHANNELS:
            raise ValueError(f"invalid channel for {u.get('id')}")
        if not isinstance(u.get("topics"), list) or not u["topics"]:
            raise ValueError(f"topics absent for {u.get('id')}")
        if any(t not in TOPICS for t in u["topics"]):
            raise ValueError(f"unknown topics for {u.get('id')}")
        if len(u["topics"]) != len(set(u["topics"])):
            raise ValueError(f"duplicate topic for {u.get('id')}")
        if not isinstance(u.get("source_url"), str) or not u["source_url"]:
            raise ValueError(f"missing source for {u.get('id')}")
        if u.get("original_post_url") is not None and not isinstance(
            u["original_post_url"], str
        ):
            raise ValueError("original post URL must be a string or null")
        if not isinstance(u.get("referenced_communication_ids", []), list):
            raise ValueError("references must be a list")
        for ref in u.get("referenced_communication_ids", []):
            if ref not in known:
                raise ValueError(f"unknown referenced communication {ref}")

    groups = []
    for channel in sorted(CHANNELS):
        members = [u for u in units if u["channel"] == channel]
        counts = Counter(t for u in members for t in u["topics"])
        groups.append({
            "channel": channel,
            "selected_unit_count": len(members),
            "distinct_discovery_source_count": len({
                u["source_url"] for u in members
            }),
            "topic_incidence": [
                {"topic": t, "selected_units": n,
                 "selected_unit_share": round(n / len(members), 4)}
                for t, n in sorted(counts.items())
            ] if members else [],
            "notice": "nonrandom_selected_sample_not_platform_prevalence",
        })

    references = sorted([
        {"unit_id": u["id"], "referenced_id": ref,
         "link_type": u.get("reference_kind")
         or "descriptive_cross_reference_not_verified_direct_reply"}
        for u in units for ref in u.get("referenced_communication_ids", [])
    ], key=lambda r: (r["referenced_id"], r["unit_id"]))
    authenticated_original_urls = sorted({
        u["original_post_url"] for u in units if u["original_post_url"]
    })
    return {
        "selected_unit_count": len(units),
        "channels": groups,
        "cross_communication_references": references,
        "authenticated_original_post_urls": authenticated_original_urls,
        "authenticated_direct_linkedin_replies": sum(
            bool(u.get("direct_replies_to_linkedin_verified")) for u in units
        ),
        "observed_claim": "different_topics_in_selected_channels",
        "population_attention_shift": "not_established",
        "corporate_message_causation": "not_established",
        "coordinated_publication": "not_established",
        "limitations": [
            "No original LinkedIn post permalink or full comment archive has been authenticated.",
            "An indexed reaction feed is not a new original post.",
            "Public forum users' employee status cannot be established from self-reports.",
            "Forum discussion about a CEO memo is not a direct reply to a LinkedIn post.",
            "Sources were purposively selected and may overrepresent prevention questions.",
            "Different platform audiences and moderation regimes are not controlled.",
            "No authenticated posting times support a pre/post or causal analysis.",
            "Single-source repetitions do not provide independent corroboration.",
        ],
    }
