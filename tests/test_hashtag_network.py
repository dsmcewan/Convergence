"""Hashtag-network tests: independently authored posts versus reaction mirrors."""
import json
import unittest

from convergence.hashtag_network import analyze_post_network, hashtags


def post(pid, author, body, kind="original", parent=None, date="2026-11-11"):
    row = {
        "id": pid, "author": author, "published_at": date, "source": f"source:{pid}",
        "text": body, "type": kind, "evidence": "verified_public",
    }
    if parent is not None:
        row["parent_post_id"] = parent
    return row


class HashtagNetworkTests(unittest.TestCase):
    def test_canonical_tags_ignore_case_and_duplicate_use(self):
        self.assertEqual(
            hashtags("#CitiStrong #citistrong #CitiTampa! #CitiProud"),
            ("citiproud", "citistrong", "cititampa"),
        )

    def test_distinct_authors_with_shared_tags_form_observed_link(self):
        result = analyze_post_network([
            post("a", "Executive A", "I remember her. #CitiStrong #CitiTampa"),
            post("b", "Executive B", "We mourn. #CitiStrong #cititampa"),
        ])
        self.assertEqual(result["original_post_count"], 2)
        self.assertEqual(result["shared_tag_link_count"], 1)
        self.assertEqual(result["shared_tag_links"][0]["shared_tags"],
                         ["citistrong", "cititampa"])
        self.assertEqual(result["coordination"], "not_established")

    def test_reaction_and_repost_are_not_new_authored_statements(self):
        result = analyze_post_network([
            post("a", "Citi", "Memorial #CitiStrong #CitiTampa"),
            post("mirror1", "Employee 1", "Citi repost preview #CitiStrong #CitiTampa",
                 "repost", "a"),
            post("mirror2", "Employee 2", "Liked: #CitiStrong #CitiTampa",
                 "reaction", "a"),
        ])
        self.assertEqual(result["original_post_count"], 1)
        self.assertEqual(result["repost_or_reaction_count"], 2)
        self.assertEqual(result["shared_tag_link_count"], 0)
        self.assertEqual(result["mirror_target_counts"][0]
                         ["observed_repost_or_reaction_count"], 2)

    def test_same_author_posting_twice_is_not_cross_author_convergence(self):
        result = analyze_post_network([
            post("a", "Leader", "One #CitiStrong #CitiProud"),
            post("b", "Leader", "Two #CitiStrong #CitiProud"),
        ])
        self.assertEqual(result["original_post_count"], 2)
        self.assertEqual(result["shared_tag_link_count"], 0)

    def test_common_one_tag_only_not_cluster_with_two_tag_threshold(self):
        result = analyze_post_network([
            post("a", "A", "Help #CitiStrong"),
            post("b", "B", "News #CitiStrong"),
        ])
        self.assertEqual(result["shared_tag_link_count"], 0)

    def test_missing_parent_preserved_without_fake_original(self):
        result = analyze_post_network([
            post("mirror", "Employee", "I reacted", "reaction", "unknown-post"),
        ])
        self.assertEqual(result["original_post_count"], 0)
        self.assertEqual(result["unresolved_mirror_parents"], ["unknown-post"])

    def test_no_motive_or_effect_predicted_from_cluster(self):
        result = analyze_post_network([
            post("a", "A", "People #CitiStrong #CitiProud"),
            post("b", "B", "People #CitiStrong #CitiProud"),
        ])
        self.assertEqual(result["audience_exposure"], "not_measured")
        self.assertEqual(result["audience_attention_displacement"], "not_measured")
        self.assertEqual(result["assessment"], "observable_authored_post_overlap_only")

    def test_reject_unattributed_or_invalid_event(self):
        with self.assertRaisesRegex(ValueError, "author"):
            analyze_post_network([post("a", "", "Memorial #CitiStrong")])
        with self.assertRaisesRegex(ValueError, "parent_post_id"):
            analyze_post_network([post("a", "A", "Liked post", "reaction")])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            a = post("a", "A", "Text")
            analyze_post_network([a, a])

    def test_determinism_under_reversed_input(self):
        sample = [
            post("a", "A", "A #CitiStrong #CitiTampa"),
            post("b", "B", "B #CitiStrong #CitiTampa"),
            post("c", "C", "C", "reaction", "a"),
        ]
        self.assertEqual(
            json.dumps(analyze_post_network(sample), sort_keys=True),
            json.dumps(analyze_post_network(list(reversed(sample))), sort_keys=True),
        )


if __name__ == "__main__":
    unittest.main()
