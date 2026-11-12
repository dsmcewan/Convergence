"""Negative tests for response-substitution as a *hypothesis*, not a verdict."""
import json
import unittest

from convergence.corporate_review import review
from convergence.framing_comparison import compare_framing


def statement(sid, text, actions=None):
    return {
        "id": sid, "actor": sid, "date": "2026-11-05",
        "source": f"source:{sid}", "coverage": "excerpt",
        "text": text, "reported_actions": actions or [],
    }


def incident(*, unresolved=True):
    return {
        "case_id": "example", "causation_verdict": "not_determined",
        "control_questions": [{
            "id": "Q1", "assessment": (
                "unresolved_in_reviewed_public_record"
                if unresolved else "affirmative_action_reported"
            ),
        }],
    }


class FramingTests(unittest.TestCase):
    def assess(self, statements, audit=None):
        return compare_framing(statements, review(statements), audit or incident())

    def test_tribute_without_response_cues_is_not_labeled(self):
        result = self.assess([statement("memorial", "We will remember LeAnne Selman.")])
        self.assertEqual(result["response_framing_examples"], [])
        self.assertEqual(result["audience_attention_effect"], "not_measured")

    def test_framing_is_not_proof_of_distraction(self):
        result = self.assess([
            statement("a", "Please continue to take care of one another."),
        ])
        e = result["response_framing_examples"][0]
        self.assertEqual(e["comparison"], "response_foregrounded_in_supplied_text")
        self.assertEqual(result["assessment"], "hypothesis_for_external_validation")
        self.assertEqual(result["intent_or_coordination"], "not_determined")
        self.assertEqual(result["unresolved_pre_attack_gate_ids"], ["Q1"])
        self.assertIn("coverage is partial", e["scope_limit"])

    def test_explicit_prevention_question_is_counterexample(self):
        result = self.assess([
            statement("a", "We look out for one another. "
                      "Why were employee warnings not issued before the breach?"),
        ])
        e = result["response_framing_examples"][0]
        self.assertTrue(e["prevention_discussion_in_supplied_text"])
        self.assertEqual(e["comparison"],
                         "response_and_prevention_discussed_in_supplied_text")

    def test_real_support_is_preserved_with_framing_observation(self):
        action = {"action_id": "counseling", "description": "Offer counseling",
                  "status": "announced"}
        result = self.assess([
            statement("a", "We look out for one another.", [action]),
        ])
        self.assertEqual(result["response_framing_examples"][0]
                         ["institutional_actions_reported"], ["counseling"])

    def test_context_not_manufactured_when_no_open_gates(self):
        result = self.assess([statement("a", "Take care of one another.")],
                             incident(unresolved=False))
        self.assertEqual(result["unresolved_pre_attack_gate_ids"], [])
        self.assertEqual(result["causal_control_failure_by_organization"],
                         "not_determined")

    def test_results_deterministic_and_no_core_promotion(self):
        statements = [
            statement("b", "Please continue to take care of one another."),
            statement("a", "We remember LeAnne Selman."),
        ]
        first = self.assess(statements)
        second = self.assess(list(reversed(statements)))
        self.assertEqual(json.dumps(first, sort_keys=True),
                         json.dumps(second, sort_keys=True))
        self.assertNotIn("elevated", json.dumps(first).lower())

    def test_invalid_causal_verdict_rejected(self):
        statements = [statement("a", "Look out for one another.")]
        with self.assertRaises(ValueError):
            compare_framing(statements, review(statements),
                            {"causation_verdict": "proven", "control_questions": []})


if __name__ == "__main__":
    unittest.main()
