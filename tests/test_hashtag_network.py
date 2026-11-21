"""Hashtag-network tests: independently authored posts versus reaction mirrors."""
import itertools
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


def rich_sample():
    """Three authors sharing tags at different hours, a quote post, and mirrors (one unresolved)."""
    return [
        post("a", "Ann", "One #A1 #B2 #C3", date="2026-11-11T09:00:00"),
        post("b", "Bob", "Two #b2 #a1", date="2026-11-11T10:30:00"),
        post("c", "Cy", "Three #a1 #c3 #b2 #zed", date="2026-11-11T12:15:00"),
        post("d", "Dee", "Four #zed #solo", "quote_post", date="2026-11-11T13:00:00"),
        post("m1", "Eve", "x", "reaction", "a", date="2026-11-11T09:05:00"),
        post("m2", "Fay", "x", "repost", "a", date="2026-11-11T09:06:00"),
        post("m3", "Gus", "x", "reaction", "c", date="2026-11-11T12:20:00"),
        post("m4", "Hal", "x", "reaction", "ghost", date="2026-11-11T14:00:00"),
        post("m5", "Ivy", "x", "repost", "ghost", date="2026-11-11T14:01:00"),
    ]


class HashtagNetworkOutputTests(unittest.TestCase):
    def test_links_carry_exact_overlap_and_elapsed_hours_in_post_id_order(self):
        r = analyze_post_network(rich_sample())
        links = [(x["post_ids"], x["shared_tags"], x["hours_between"])
                 for x in r["shared_tag_links"]]
        self.assertEqual(links, [
            (["a", "b"], ["a1", "b2"], 1.5),
            (["a", "c"], ["a1", "b2", "c3"], 3.25),
            (["b", "c"], ["a1", "b2"], 1.75),
        ])
        self.assertEqual(r["shared_tag_link_count"], 3)
        self.assertEqual([x["shared_tag_count"] for x in r["shared_tag_links"]], [2, 3, 2])
        self.assertTrue(all(x["interpretation"] == "shared_hashtag_discovery_link_not_coordination"
                            for x in r["shared_tag_links"]))

    def test_elapsed_hours_are_rounded_to_three_places_and_are_never_negative(self):
        early = post("e", "Ann", "#t1 #t2", date="2026-11-11T09:00:00")
        late = post("l", "Bob", "#t1 #t2", date="2026-11-11T09:20:00")
        for ordered in ([early, late], [late, early]):
            link = analyze_post_network(ordered)["shared_tag_links"][0]
            self.assertEqual(link["hours_between"], 0.333)

    def test_a_quote_post_is_an_original_and_mirrors_are_not(self):
        r = analyze_post_network(rich_sample())
        self.assertEqual(r["original_post_count"], 4)
        self.assertEqual(r["distinct_original_author_count"], 4)
        self.assertEqual(r["repost_or_reaction_count"], 5)
        self.assertEqual([p["id"] for p in r["posts"]], ["a", "b", "c", "d"])
        self.assertEqual(next(p for p in r["posts"] if p["id"] == "d")["type"], "quote_post")

    def test_mirror_targets_are_counted_sorted_and_unknown_parents_listed(self):
        r = analyze_post_network(rich_sample())
        self.assertEqual(r["mirror_target_counts"], [
            {"parent_post_id": "a", "observed_repost_or_reaction_count": 2},
            {"parent_post_id": "c", "observed_repost_or_reaction_count": 1},
            {"parent_post_id": "ghost", "observed_repost_or_reaction_count": 2},
        ])
        self.assertEqual(r["unresolved_mirror_parents"], ["ghost"])

    def test_tag_ledger_is_sorted_and_counts_authors_and_posts(self):
        r = analyze_post_network(rich_sample())
        ledger = {row["tag"]: (row["original_post_count"], row["author_count"], row["post_ids"])
                  for row in r["tags"]}
        self.assertEqual([row["tag"] for row in r["tags"]], sorted(ledger))
        self.assertEqual(ledger["a1"], (3, 3, ["a", "b", "c"]))
        self.assertEqual(ledger["zed"], (2, 2, ["c", "d"]))
        self.assertEqual(ledger["solo"], (1, 1, ["d"]))

    def test_the_shared_tag_threshold_is_a_parameter(self):
        def links(posts, n):
            return analyze_post_network(posts, min_shared_tags=n)["shared_tag_link_count"]

        sample = [post("a", "Ann", "#t1 #t2 #t3"), post("b", "Bob", "#t1 #t2 #t3")]
        self.assertEqual(links(sample, 3), 1)
        self.assertEqual(links(sample, 4), 0)
        one_tag = [post("a", "Ann", "#t1"), post("b", "Bob", "#t1")]
        self.assertEqual(links(one_tag, 1), 1)

    def test_common_tags_are_supplied_by_the_caller_and_flagged_per_post(self):
        sample = [post("a", "Ann", "#Brand #Event"), post("b", "Bob", "#brand #Other")]
        none_supplied = analyze_post_network(sample)
        self.assertEqual([p["common_corporate_tags"] for p in none_supplied["posts"]],
                         [(), ()])
        flagged = analyze_post_network(sample, common_tags={"brand"})
        self.assertEqual([p["common_corporate_tags"] for p in flagged["posts"]],
                         [("brand",), ("brand",)])
        # Flagging a tag as common does not remove it from the network.
        self.assertEqual([p["tags"] for p in flagged["posts"]],
                         [("brand", "event"), ("brand", "other")])

    def test_every_input_order_gives_the_same_output(self):
        base = rich_sample()[:6]  # 720 orders: enough to move every sort in the module
        expected = json.dumps(analyze_post_network(base), sort_keys=True)
        for order in itertools.permutations(base):
            got = json.dumps(analyze_post_network(list(order)), sort_keys=True)
            self.assertEqual(got, expected)

    def test_each_kind_of_invalid_input_is_refused_with_its_own_reason(self):
        ok = post("a", "A", "#x")
        cases = [
            (post("a", "A", "#x", date="11/11/2026"), "invalid date"),
            (post("a", "A", "#x", date="2026-11-11T09:00:00+00:00"), "timezone"),
            (post("a", "A", "#x", kind="comment"), "unknown activity type"),
            ({**ok, "evidence": "hearsay"}, "unknown evidence status"),
            (post("a", "A", "#x", "reaction", "a"), "self-referential parent"),
            ({**ok, "published_at": ""}, "published_at must be nonempty"),
            ({**ok, "text": 5}, "text must be nonempty"),
        ]
        for bad, reason in cases:
            with self.assertRaisesRegex(ValueError, reason):
                analyze_post_network([bad])
        with self.assertRaisesRegex(ValueError, r"min_shared_tags must be >=1"):
            analyze_post_network([ok], min_shared_tags=0)


class HashtagNetworkOrderingTests(unittest.TestCase):
    """Fixtures where date order, id order and first-seen order disagree, so each sort is needed."""

    def test_links_are_sorted_by_post_ids_not_by_the_date_order_pairs_are_found_in(self):
        sample = [post("z1", "Ann", "#t1 #t2", date="2026-11-11T09:00:00"),
                  post("m1", "Bob", "#t1 #t2", date="2026-11-11T10:00:00"),
                  post("a1", "Cy", "#t1 #t2", date="2026-11-11T11:00:00")]
        r = analyze_post_network(sample)
        self.assertEqual([x["post_ids"] for x in r["shared_tag_links"]],
                         [["m1", "a1"], ["z1", "a1"], ["z1", "m1"]])
        self.assertEqual([p["id"] for p in r["posts"]], ["z1", "m1", "a1"])  # originals: by date

    def test_unresolved_parents_and_mirror_counts_are_sorted_by_id_not_by_arrival(self):
        sample = [post("q1", "Ann", "x", "reaction", "q", date="2026-11-11T12:00:00"),
                  post("b1", "Bob", "x", "reaction", "b", date="2026-11-11T13:00:00"),
                  post("y1", "Cy", "x", "repost", "y", date="2026-11-11T14:00:00"),
                  post("x1", "Dee", "x", "repost", "x", date="2026-11-11T15:00:00")]
        r = analyze_post_network(sample)
        self.assertEqual(r["unresolved_mirror_parents"], ["b", "q", "x", "y"])
        self.assertEqual([m["parent_post_id"] for m in r["mirror_target_counts"]],
                         ["b", "q", "x", "y"])


if __name__ == "__main__":
    unittest.main()
