"""Guards for the public-record Citi cross-channel discovery sample."""
import copy
import json
import unittest
from pathlib import Path

from convergence.cross_channel_discourse import compare_public_discourse

PATH = (Path(__file__).parent.parent / "examples" / "citi_tampa_2026"
        / "public_discourse_discovery_20261112.json")


def sample():
    return json.loads(PATH.read_text(encoding="utf-8"))["units"]


class CrossChannelTests(unittest.TestCase):
    def test_sample_structure(self):
        r = compare_public_discourse(sample())
        self.assertEqual(r["selected_unit_count"], 17)
        counts = {g["channel"]: g["selected_unit_count"] for g in r["channels"]}
        self.assertEqual(counts, {
            "institutional": 3, "individual_posts": 6, "public_forum": 8,
        })

    def test_discussion_difference_is_descriptive_not_a_diversion_verdict(self):
        r = compare_public_discourse(sample())
        groups = {g["channel"]: g for g in r["channels"]}
        forum = {x["topic"]: x["selected_units"]
                 for x in groups["public_forum"]["topic_incidence"]}
        institutional = {x["topic"]: x["selected_units"]
                         for x in groups["institutional"]["topic_incidence"]}
        self.assertEqual(forum["prevention_question"], 6)
        self.assertNotIn("prevention_question", institutional)
        self.assertEqual(r["population_attention_shift"], "not_established")
        self.assertEqual(r["corporate_message_causation"], "not_established")

    def test_references_to_memo_are_not_linkedin_replies(self):
        r = compare_public_discourse(sample())
        self.assertEqual(len(r["cross_communication_references"]), 3)
        self.assertTrue(all(
            p["referenced_id"] == "fraser_memo"
            and p["link_type"] == "cross_platform_discussion_about_memo_not_direct_reply"
            for p in r["cross_communication_references"]
        ))
        self.assertEqual(r["authenticated_direct_linkedin_replies"], 0)
        self.assertEqual(r["authenticated_original_post_urls"], [])

    def test_mirrored_activity_is_not_counted_as_independent_sources(self):
        r = compare_public_discourse(sample())
        groups = {g["channel"]: g for g in r["channels"]}
        self.assertEqual(groups["individual_posts"]["selected_unit_count"], 6)
        self.assertEqual(groups["individual_posts"]["distinct_discovery_source_count"], 5)

    def test_determinism_and_no_count_inflation(self):
        u = sample()
        self.assertEqual(
            json.dumps(compare_public_discourse(u), sort_keys=True),
            json.dumps(compare_public_discourse(list(reversed(u))), sort_keys=True),
        )
        with self.assertRaisesRegex(ValueError, "unique nonempty"):
            compare_public_discourse(u + [u[0]])

    def test_unknown_topics_and_orphan_references_rejected(self):
        u = sample()
        bad = copy.deepcopy(u)
        bad[0]["topics"] = ["proven_negligence"]
        with self.assertRaisesRegex(ValueError, "unknown topics"):
            compare_public_discourse(bad)
        bad = copy.deepcopy(u)
        bad[0]["referenced_communication_ids"] = ["nonexistent"]
        with self.assertRaisesRegex(ValueError, "unknown referenced"):
            compare_public_discourse(bad)


if __name__ == "__main__":
    unittest.main()
