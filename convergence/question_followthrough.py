"""Public-question follow-through: ask -> relevant response -> verification gap.

This is an evidence ledger, not a court finding, an audit of Citi systems, or a
claim that an official replied to a specific forum commenter. The provenance
and analyst-coded relevance of each record remain visible. "Not located" means
not found within the **enumerated searched sources**, never that no response
exists. An anonymous employee's clock-time claim is not a notification log.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

_ANSWER_KINDS = {
    "documented_fact", "reported_operational_action", "specific_commitment",
    "general_assurance", "anonymous_experience", "request_for_review",
}
_QUALITIES = {"official_primary", "attributed_executive", "news_reporting",
              "unverified_forum", "verified_records"}
_LINK_TYPES = {"topic_related_public_statement", "direct_reply_verified",
               "independent_incident_evidence", "third_party_comment"}


def audit_followthrough(case: dict[str, Any]) -> dict[str, Any]:
    """Build transparent issue-level status for a closed, specified evidence sample."""
    sources = case["sources"]
    questions = case["questions"]
    responses = case["responses"]
    if not case.get("as_of") or not case.get("sampling_limit"):
        raise ValueError("as_of and sampling_limit required")
    for label, rows in (("source", sources), ("question", questions),
                        ("response", responses)):
        ids = [r.get("id") for r in rows]
        if len(ids) != len(set(ids)) or any(
            not isinstance(i, str) or not i for i in ids
        ):
            raise ValueError(f"invalid or duplicated {label} id")
    source_by_id = {s["id"]: s for s in sources}
    question_by_id = {q["id"]: q for q in questions}
    for s in sources:
        if not all(isinstance(s.get(k), str) and s[k] for k in
                   ("id", "url", "origin", "quality")):
            raise ValueError("all sources require URL, origin and quality")
        if s["quality"] not in _QUALITIES:
            raise ValueError("invalid source quality")
    for q in questions:
        if q.get("question_source") not in source_by_id:
            raise ValueError(f"question {q['id']} requires verified source id")
        if not all(isinstance(q.get(k), str) and q[k] for k in
                   ("text", "required_evidence", "domain")):
            raise ValueError("question lacks descriptive inputs")

    replies: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in responses:
        if r.get("source_id") not in source_by_id:
            raise ValueError("response source missing or unknown")
        if r.get("kind") not in _ANSWER_KINDS:
            raise ValueError("response kind missing or invalid")
        if r.get("link_type") not in _LINK_TYPES:
            raise ValueError("response link_type invalid")
        if not isinstance(r.get("summary"), str) or not r["summary"]:
            raise ValueError("response summary required")
        if not isinstance(r.get("question_ids"), list):
            raise ValueError("response question_ids must be a list")
        if not r["question_ids"]:
            raise ValueError("response must relate to at least one question")
        for qid in r["question_ids"]:
            if qid not in question_by_id:
                raise ValueError(f"orphan question reference: {qid}")
            replies[qid].append(r)

    issues = []
    for q in sorted(questions, key=lambda x: x["id"]):
        arr = sorted(replies[q["id"]], key=lambda x: x["id"])
        attributed = [r for r in arr if source_by_id[r["source_id"]]["quality"]
                      not in {"unverified_forum"}]
        official = [r for r in arr if source_by_id[r["source_id"]]["quality"]
                    in {"official_primary", "attributed_executive", "verified_records"}]
        verified = [r for r in arr if source_by_id[r["source_id"]]["quality"]
                    in {"official_primary", "verified_records"}
                    and r["kind"] == "documented_fact"]
        claims = [r for r in arr if r["kind"] == "anonymous_experience"]
        commitments = [r for r in official if r["kind"] == "specific_commitment"]
        specific_actions = [r for r in official
                            if r["kind"] == "reported_operational_action"]
        all_official_are_direct = bool(official) and all(
            r["link_type"] == "direct_reply_verified" for r in official
        )
        if verified:
            state = "independent_public_fact_on_aspect"
        elif commitments:
            state = "specific_commitment_publicly_reported"
        elif specific_actions:
            state = "official_operational_description_partial"
        elif official:
            state = "official_general_assurance_only"
        elif attributed:
            state = "journalistic_report_on_aspect_only"
        elif claims:
            state = "unverified_firsthand_claims_only"
        else:
            state = "no_relevant_response_in_selected_public_material"
        # This deliberately does not infer a verified outcome or that a
        # historical commenter obtained a direct answer.
        issues.append({
            "id": q["id"], "domain": q["domain"], "question": q["text"],
            "source_id": q["question_source"],
            "required_for_full_answer": q["required_evidence"],
            "status": state, "scope": "selected_public_material",
            "response_ids": [r["id"] for r in arr],
            "official_or_primary_response_ids": [r["id"] for r in official],
            "anonymous_employee_claim_ids": [r["id"] for r in claims],
            "verified_incident_fact_ids": [r["id"] for r in verified],
            "all_official_responses_are_direct_to_original_question":
                all_official_are_direct,
            "full_answer_independently_verified_in_selected_sources": False,
            "external_investigation_completion": "not_established_in_selected_sources",
        })
    by_source_origin = defaultdict(set)
    for s in sources:
        by_source_origin[s["origin"]].add(s["id"])
    return {
        "case_id": case.get("case_id", ""),
        "as_of": case["as_of"], "sampling_limit": case["sampling_limit"],
        "question_count": len(questions), "response_record_count": len(responses),
        "source_count": len(sources), "underlying_source_origin_count":
            len(by_source_origin),
        "issues": issues,
        "inferences": {
            "all_questions_fully_answered_in_selected_sources": False,
            "public_questions_suppressed": "not_established",
            "institutional_neglect": "not_determined",
            "communications_caused_distraction": "not_established",
            "independent_audit_performed": "not_established",
        },
        "limitations": [
            "No source search can prove that a message or procedure does not exist.",
            "Answers to a general public topic are not verified direct replies.",
            "One sheriff briefing repeated in multiple articles remains one origin.",
            "A reported operational action need not demonstrate effective prevention.",
            "An announced employee benefit is not verified delivery or sufficiency.",
            "Anonymous claims about alert times must be compared to notification logs.",
            "Nothing here establishes motive, negligence, or causal diversion.",
        ],
    }
