"""Tests for grounded focus measurement and explicit reply transitions."""
import json
import unittest
from pathlib import Path

from convergence.attention_trajectory import analyze_attention

ROOT = Path(__file__).parent.parent / "examples" / "citi_tampa_2026"


def unit(uid, text, frames, *, actor=None, reply_to=None, asked=None,
         addressed=None, date="2026-11-05"):
    return {
        "id": uid, "actor": actor or uid, "role": "public",
        "thread_id": "discussion", "timestamp": date,
        "source": f"source:{uid}", "coverage": "excerpt",
        "text": text,
        "frames": [{"topic": topic, "quote": quote} for topic, quote in frames],
        "reply_to": reply_to, "asks_issue_ids": asked or [],
        "addresses_issue_ids": addressed or [],
    }


class AttentionTests(unittest.TestCase):
    def test_observed_shift_when_direct_reply_reframes_prevention(self):
        question = unit(
            "q", "Why was no employee warning given before the attack?",
            [("pre_attack_prevention", "employee warning")],
            asked=["warning"],
        )
        response = unit(
            "r", "Our security team showed extraordinary bravery.",
            [("heroism", "extraordinary bravery")],
            reply_to="q",
        )
        res = analyze_attention([question, response], [
            {"id": "question", "unit_id": "q", "kind": "question"},
        ])
        edge = res["direct_reply_transitions"][0]
        self.assertEqual(edge["shift"], "prevention_to_response_in_direct_reply")
        self.assertEqual(edge["unaddressed_parent_issue_ids_in_reply"], ["warning"])
        self.assertEqual(res["communication_action_traces"][0]["other_actor_direct_replies"], 1)
        self.assertEqual(res["causal_message_effect"], "not_established")

    def test_prevention_answer_is_not_redirection(self):
        question = unit(
            "q", "Why no lockdown?", [("pre_attack_prevention", "lockdown")],
            asked=["lockdown"],
        )
        response = unit(
            "r", "We activated lockdown at noon, according to our log.",
            [("pre_attack_prevention", "lockdown")], reply_to="q",
            addressed=["lockdown"],
        )
        result = analyze_attention([question, response])
        edge = result["direct_reply_transitions"][0]
        self.assertEqual(edge["shift"], "not_classified")
        self.assertEqual(edge["explicitly_addressed_parent_issue_ids"], ["lockdown"])
        self.assertEqual(edge["unaddressed_parent_issue_ids_in_reply"], [])
        # The code only records the claimed answer, not whether the log is authentic.
        self.assertEqual(result["causal_message_effect"], "not_established")

    def test_unlinked_statements_have_no_measured_effect(self):
        a = unit("a", "Take care of one another.",
                 [("mutual_support", "Take care of one another")])
        b = unit("b", "Discuss the employee warning.",
                 [("pre_attack_prevention", "employee warning")])
        result = analyze_attention([a, b], [{"id": "post", "unit_id": "a"}])
        trace = result["communication_action_traces"][0]
        self.assertEqual(trace["observability"],
                         "downstream_effect_not_measurable_from_sample")
        self.assertEqual(result["direct_reply_transitions"], [])
        self.assertEqual(result["measured_audience_attention_change"], "not_established")

    def test_multiple_topics_do_not_force_100_percent_total(self):
        a = unit("a", "Grief for LeAnne and care for each other.",
                 [("memorial", "Grief for LeAnne"),
                  ("mutual_support", "care for each other")])
        result = analyze_attention([a])["observed_focus"]
        self.assertEqual(sum(item["share_of_units"] for item in result["topics"]), 2.0)
        self.assertEqual(result["multi_label_denominator"], "all_units")

    def test_frames_must_be_anchored_in_text(self):
        with self.assertRaisesRegex(ValueError, "anchor missing"):
            analyze_attention([unit("x", "Ordinary condolences.",
                                    [("heroism", "heroic response")])])

    def test_reply_cycle_and_invalid_reference_rejected(self):
        a = unit("a", "care for each other",
                 [("mutual_support", "care for each other")], reply_to="b")
        b = unit("b", "hope", [], reply_to="a")
        with self.assertRaisesRegex(ValueError, "cycle"):
            analyze_attention([a, b])
        with self.assertRaisesRegex(ValueError, "missing unit"):
            analyze_attention([unit("a", "hi", [])],
                              [{"id": "a", "unit_id": "not_there"}])

    def test_actual_excerpt_sample_is_noncausal_and_grounded(self):
        sample = json.loads((ROOT / "attention_units.json").read_text(encoding="utf-8"))
        result = analyze_attention(sample["units"], sample["actions"])
        self.assertEqual(result["unit_count"], 7)
        self.assertEqual(result["coverage"]["partial_or_quoted_units"], 7)
        self.assertEqual(result["direct_reply_transitions"], [])
        self.assertEqual(result["measured_audience_attention_change"], "not_established")
        self.assertTrue(all(
            trace["observability"] == "downstream_effect_not_measurable_from_sample"
            for trace in result["communication_action_traces"]
        ))

    def test_deterministic_input_order(self):
        a = unit("a", "Focus on the response.",
                 [("security_response", "response")])
        b = unit("b", "We should examine prevention.",
                 [("pre_attack_prevention", "prevention")], reply_to="a")
        left = analyze_attention([a, b])
        right = analyze_attention([b, a])
        self.assertEqual(json.dumps(left, sort_keys=True),
                         json.dumps(right, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
