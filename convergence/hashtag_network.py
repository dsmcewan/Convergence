"""Audit hashtag-connected publication clusters, excluding reaction/repost mirrors.

Hashtags are discovery links. Their reuse may be spontaneous, habitual,
encouraged, or coordinated. Shared tags, near-simultaneous posting and aligned
language do not prove managerial direction or deliberate attention diversion.

Only distinct author-generated 'original' / 'quote_post' records participate in
the authorship graph. Reposts/reactions are dissemination events, not new
independent author statements. Unattributed visual evidence is excluded.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import datetime
from itertools import combinations
from typing import Any

_TAG = re.compile(r"(?<![\w])#([A-Za-z][A-Za-z0-9_]*)")
_ORIGINAL_TYPES = {"original", "quote_post"}
_ACTIVITY_TYPES = _ORIGINAL_TYPES | {"repost", "reaction"}
_EVIDENCE = {"verified_public", "user_screenshot", "search_snippet"}
_COMMON = {
    "citi", "citiproud", "citistrong", "cititampa", "citijacksonville",
    "tampa", "jacksonville",
}


def hashtags(text: str) -> tuple[str, ...]:
    """Case-normalized, deduplicated tags in deterministic order."""
    return tuple(sorted({m.group(1).casefold() for m in _TAG.finditer(text)}))


def _date(value: str) -> datetime:
    try:
        dt = datetime.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid date: {value!r}") from exc
    if dt.tzinfo is not None:
        raise ValueError("use consistently timezone-local timestamps in this dataset")
    return dt


def analyze_post_network(
    posts: list[dict[str, Any]],
    min_shared_tags: int = 2,
) -> dict[str, Any]:
    """Grounded post/tag network; never emit author-intent or coordination verdicts."""
    if min_shared_tags < 1:
        raise ValueError("min_shared_tags must be >=1")
    if len({p.get("id") for p in posts}) != len(posts):
        raise ValueError("duplicate post IDs")
    known = {p.get("id") for p in posts}
    for p in posts:
        for key in ("id", "author", "published_at", "source", "text", "type",
                    "evidence"):
            if not isinstance(p.get(key), str) or not p[key].strip():
                raise ValueError(f"{key} must be nonempty for post {p.get('id')}")
        if p["type"] not in _ACTIVITY_TYPES:
            raise ValueError(f"unknown activity type: {p['type']}")
        if p["evidence"] not in _EVIDENCE:
            raise ValueError(f"unknown evidence status: {p['evidence']}")
        _date(p["published_at"])
        parent = p.get("parent_post_id")
        if p["type"] in {"repost", "reaction"} and not isinstance(parent, str):
            raise ValueError("non-original event requires parent_post_id")
        if parent == p["id"]:
            raise ValueError("self-referential parent")
        # The original may not be in a partial dataset, so a missing parent is
        # retained as unknown instead of inventing an original.
    originals = sorted(
        (p for p in posts if p["type"] in _ORIGINAL_TYPES),
        key=lambda x: (x["published_at"], x["id"]),
    )
    mirrors = sorted(
        (p for p in posts if p["type"] not in _ORIGINAL_TYPES),
        key=lambda x: (x["published_at"], x["id"]),
    )
    indexed = []
    for p in originals:
        indexed.append({
            "id": p["id"], "author": p["author"], "type": p["type"],
            "source": p["source"], "evidence": p["evidence"],
            "published_at": p["published_at"], "tags": hashtags(p["text"]),
            "common_corporate_tags": tuple(
                t for t in hashtags(p["text"]) if t in _COMMON
            ),
        })
    pair_links = []
    for a, b in combinations(indexed, 2):
        if a["author"] == b["author"]:
            continue
        overlap = sorted(set(a["tags"]) & set(b["tags"]))
        if len(overlap) < min_shared_tags:
            continue
        elapsed_h = round(abs((_date(a["published_at"])
                               - _date(b["published_at"])).total_seconds()) / 3600, 3)
        pair_links.append({
            "post_ids": [a["id"], b["id"]],
            "authors": [a["author"], b["author"]],
            "shared_tags": overlap, "shared_tag_count": len(overlap),
            "hours_between": elapsed_h,
            "interpretation": "shared_hashtag_discovery_link_not_coordination",
        })
    tag_to_posts: dict[str, set[str]] = defaultdict(set)
    tag_to_authors: dict[str, set[str]] = defaultdict(set)
    for row in indexed:
        for tag in row["tags"]:
            tag_to_posts[tag].add(row["id"])
            tag_to_authors[tag].add(row["author"])
    tag_ledger = [
        {"tag": tag, "original_post_count": len(ids),
         "author_count": len(tag_to_authors[tag]), "post_ids": sorted(ids)}
        for tag, ids in sorted(tag_to_posts.items())
    ]
    mirror_targets = Counter(p["parent_post_id"] for p in mirrors)
    return {
        "original_post_count": len(originals),
        "distinct_original_author_count": len({p["author"] for p in originals}),
        "repost_or_reaction_count": len(mirrors),
        "unresolved_mirror_parents": sorted(
            parent for parent in mirror_targets if parent not in known
        ),
        "mirror_target_counts": [
            {"parent_post_id": k, "observed_repost_or_reaction_count": n}
            for k, n in sorted(mirror_targets.items())
        ],
        "posts": indexed, "tags": tag_ledger,
        "shared_tag_links": sorted(pair_links, key=lambda row: row["post_ids"]),
        "shared_tag_link_count": len(pair_links),
        "assessment": "observable_authored_post_overlap_only",
        "coordination": "not_established",
        "audience_exposure": "not_measured",
        "audience_attention_displacement": "not_measured",
        "limitations": [
            "Search snippets and reactions can expose the same original post repeatedly.",
            "Tags indicate intended discoverability, not actual audience impressions.",
            "Shared tags and close timing do not establish central direction.",
            "Pre-existing corporate tags may recur without event-specific coordination.",
            "Distinct original content and attributed authorship require source verification.",
            "No attention effect can be inferred without audience replies or reach data.",
            "An unattributed screenshot cannot ground a separate authored post.",
        ],
    }
