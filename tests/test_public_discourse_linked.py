"""Documented reply shapes that do not erase prevention questions."""
import json
import unittest
from pathlib import Path

from convergence.attention_trajectory import analyze_attention

PATH = (Path(__file__).parent.parent / "examples" / "citi_tampa_2026"
        / "reddit_linked_discussion_20261112.json")


def sample():
    return json.loads(PATH.read_text(encoding="utf-8"))["units"]


class LinkedForumTests(unittest.TestCase):
    def test_links_are_documented_only_within_two_forum_threads(self):
        r = analyze_attention(sample())
        self.assertEqual(r["unit_count"], 6)
        self.assertEqual(len(r["direct_reply_transitions"]), 4)
        self.assertEqual(r["measured_audience_attention_change"], "not_established")

    def test_memo_discussion_moves_toward_prevention(self):
        edges = analyze_attention(sample())["direct_reply_transitions"]
        e = next(x for x in edges if x["reply_id"] == "memo_response")
        self.assertEqual(e["shift"], "toward_prevention_in_direct_reply")
        self.assertEqual(e["explicitly_addressed_parent_issue_ids"],
                         ["memo_specificity"])

    def test_reply_retains_prevention_question_and_adds_aftercare(self):
        edges = analyze_attention(sample())["direct_reply_transitions"]
        e = next(x for x in edges if x["reply_id"] == "prevention_response")
        self.assertEqual(e["shift"], "topic_change_in_direct_reply")
        self.assertEqual(e["unaddressed_parent_issue_ids_in_reply"], [
            "citi_first_receipt", "pre_attack_measures", "threat_assessment",
        ])
        self.assertEqual(e["added_topics"], ["post_event_support"])
        self.assertNotIn("pre_attack_prevention", e["dropped_topics"])

    def test_no_artificial_prevention_to_response_displacement(self):
        edges = analyze_attention(sample())["direct_reply_transitions"]
        self.assertFalse(any(
            e["shift"] == "prevention_to_response_in_direct_reply"
            for e in edges
        ))

    def test_code_rejects_fabricated_quote(self):
        u = sample()
        u[0]["frames"][0]["quote"] = "an independent security audit was published"
        with self.assertRaisesRegex(ValueError, "anchor missing"):
            analyze_attention(u)

    def test_determinism(self):
        u = sample()
        self.assertEqual(json.dumps(analyze_attention(u), sort_keys=True),
                         json.dumps(analyze_attention(list(reversed(u))), sort_keys=True))


if __name__ == "__main__":
    unittest.main()
