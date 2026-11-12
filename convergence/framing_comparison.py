"""Compare crisis-response framing with independently documented control questions.

The mechanism being tested is response-substitution: attention to courage,
solidarity, and aftercare can coexist with unanswered prevention questions.
This module DOES NOT conclude that audience attention actually changed, that
a speaker intended a diversion, or that a specific control was negligent.

Crucially, omissions are assessed across separate institutional evidence, not
inferred from any one short condolence excerpt.
"""
from __future__ import annotations

import re
from typing import Any

_RESPONSE_LABELS = frozenset({
    "response_recognition", "collective_care_directive",
    "institutional_virtue_claim",
})
# This only detects an *express* preventive-control discussion in supplied
# text. It does not detect the presence/absence of actual controls.
_PREVENTION_DISCUSSION = re.compile(
    r"\b(?:preventive controls?|prevention|before the (?:attack|breach|first shot)|"
    r"employee (?:warning|notification)|lockdown|shelter.in.place|"
    r"perimeter (?:design|security|protection)|threat escalation)\b",
    re.IGNORECASE,
)


def compare_framing(
    statements: list[dict[str, Any]],
    wording_review: dict[str, Any],
    causal_review: dict[str, Any],
) -> dict[str, Any]:
    """Return a hypothesis ledger; do not promote or invent a verdict."""
    if wording_review.get("verdict") != "not_assessed":
        raise ValueError("wording review must remain non-adjudicative")
    if causal_review.get("causation_verdict") != "not_determined":
        raise ValueError("causal audit must not supply an inferred verdict")
    observed = wording_review.get("observations", [])
    labels_by_id: dict[str, set[str]] = {}
    for item in observed:
        labels_by_id.setdefault(item["statement_id"], set()).add(item["label"])

    gates = causal_review.get("control_questions", [])
    open_gates = sorted(
        g["id"] for g in gates
        if g["assessment"] == "unresolved_in_reviewed_public_record"
    )
    known_adverse = sorted(
        g["id"] for g in gates
        if g["assessment"] == "adverse_outcome_or_nonaction_reported"
    )
    entries = []
    for statement in sorted(statements, key=lambda s: (s["date"], s["id"])):
        sid = statement["id"]
        cues = sorted(labels_by_id.get(sid, set()) & _RESPONSE_LABELS)
        prevention_mention = bool(_PREVENTION_DISCUSSION.search(statement["text"]))
        if cues:
            entries.append({
                "statement_id": sid,
                "actor": statement["actor"],
                "source": statement["source"],
                "coverage": statement["coverage"],
                "observed_response_cues": cues,
                "prevention_discussion_in_supplied_text": prevention_mention,
                "comparison": (
                    "response_and_prevention_discussed_in_supplied_text"
                    if prevention_mention
                    else "response_foregrounded_in_supplied_text"
                ),
                "institutional_actions_reported": sorted(
                    a["action_id"] for a in statement.get("reported_actions", [])
                ),
                "scope_limit": (
                    "No claim of omission from the complete post: coverage is partial."
                    if statement["coverage"] != "full_screenshot"
                    else "Screenshot coverage does not establish other institutional disclosures."
                ),
            })
    # This is NOT a count of distractive statements. Some may foreground
    # prevention and some may acknowledge real support.
    return {
        "case_id": causal_review.get("case_id", ""),
        "comparison_type": "response_substitution_hypothesis",
        "question": (
            "Does repeated emphasis on bravery, mutual support, and organizational "
            "virtue displace public examination of independently unresolved "
            "pre-attack protective-control questions?"
        ),
        "response_framing_examples": entries,
        "unresolved_pre_attack_gate_ids": open_gates,
        "reported_adverse_gate_ids": known_adverse,
        "assessment": "hypothesis_for_external_validation",
        "audience_attention_effect": "not_measured",
        "intent_or_coordination": "not_determined",
        "causal_control_failure_by_organization": "not_determined",
        "validation_needed": [
            "Complete original posts and full executive/corporate statement corpus",
            "Sequence of releases, media coverage and subsequent public response",
            "Independent evidence of audience emphasis, if claiming actual diversion",
            "Internal threat intake, escalation, warning and perimeter design records",
            "Counterexamples identifying concrete prevention commitments or scrutiny",
        ],
        "limits": [
            "Memorialization is appropriate and not itself evidence of evasion.",
            "A heroic response does not establish adequate upstream prevention.",
            "Documented perimeter penetration is not itself proof of negligence.",
            "Repetition of language is not proof of coordinated messaging.",
            "No prevention phrase in an excerpt is not proof of deliberate omission.",
            "Observed framing is not proof it actually shifted audience attention.",
        ],
    }
