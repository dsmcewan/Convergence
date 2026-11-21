"""Negative controls for evidence-conservative corporate wording review."""
import json
import unittest
from pathlib import Path

from convergence.corporate_review import DEFAULT_CUES, merge_cues, review

EXAMPLE = Path(__file__).parent.parent / "examples" / "citi_tampa_2026"


def citi_cues():
    """The wording one case adds to the generic cues; it lives with that case, not the package."""
    extra = json.loads((EXAMPLE / "cues.json").read_text(encoding="utf-8"))
    return merge_cues(DEFAULT_CUES, extra)


def statement(sid, actor, text, actions=None, coverage="excerpt"):
    return {"id": sid, "actor": actor, "date": "2026-11-04",
            "source": f"source:{sid}", "text": text,
            "coverage": coverage, "reported_actions": actions or []}


class ReviewTests(unittest.TestCase):
    def test_ordinary_condolence_is_not_a_manipulation_finding(self):
        result = review([statement("a", "A", "I am sorry for your loss.")])
        self.assertEqual(result["observations"], [])
        self.assertEqual(result["verdict"], "not_assessed")

    def test_cross_author_directive_is_recurrence_not_coordination(self):
        result = review([
            statement("a", "A", "Please continue to take care of one another."),
            statement("b", "B", "I ask that we all look out for one another."),
        ])
        self.assertEqual(result["recurrences"][0]["label"], "collective_care_directive")
        self.assertEqual(result["recurrences"][0]["interpretation"],
                         "cross_author_wording_recurrence_only")
        self.assertEqual(result["verdict"], "not_assessed")

    def test_repeated_fund_announcement_is_one_action(self):
        action = {"action_id": "fund", "description": "performing-arts fund", "status": "announced"}
        result = review([statement("a", "A", "$250,000 contribution", [action]),
                         statement("b", "B", "We will give $250,000", [action])])
        self.assertEqual(len(result["reported_actions"]), 1)
        self.assertEqual(result["reported_actions"][0]["source_statement_ids"], ["a", "b"])
        self.assertEqual(result["reported_actions"][0]["verification"],
                         "source_reported_not_independently_audited")

    def test_excerpt_does_not_prove_absence(self):
        result = review([statement("a", "A", "We stand with our colleagues.")])
        self.assertFalse(any(o["label"] == "contemporaneous_security_posture_description"
                             for o in result["observations"]))
        self.assertIn("An absent phrase in an excerpt does not establish a missing procedure.",
                      result["disclaimers"])

    def test_determinism_and_duplicate_rejection(self):
        x = statement("a", "A", "Citi Tampa has always been a tremendous force for good")
        y = statement("b", "B", "We are providing counseling and other resources available")
        cues = citi_cues()
        self.assertEqual(json.dumps(review([x, y], cues=cues), sort_keys=True),
                         json.dumps(review([y, x], cues=cues), sort_keys=True))
        with self.assertRaises(ValueError):
            review([x, x])

    # A dollar sign is not a word character, so a \b in front of it can never match after a space:
    # the amount cues were dead for ordinary sentences.
    def test_dollar_amount_in_a_sentence_is_an_announced_action_cue(self):
        result = review([
            statement("a", "A", "Citi announced a $250,000 contribution to the fund."),
            statement("b", "B", "The fund will receive $250,000."),
        ], cues=citi_cues())
        cues = {o["statement_id"]: o["cue"] for o in result["observations"]
                if o["label"] == "announced_action"}
        self.assertEqual(cues, {"a": "$250,000 contribution", "b": "$250,000"})

    def test_larger_amount_sharing_the_prefix_is_not_the_announced_amount(self):
        result = review([statement("a", "A", "The settlement was $250,000,000.")],
                        cues=citi_cues())
        labels = [o["label"] for o in result["observations"]]
        self.assertNotIn("announced_action", labels)


class CueSetTests(unittest.TestCase):
    def test_default_cues_name_no_organisation_and_no_person(self):
        words = " ".join(p for patterns in DEFAULT_CUES.values() for p in patterns).lower()
        for name in ("citi", "selman", "fraley", "tampa", "jacksonville"):
            self.assertNotIn(name, words)

    def test_cues_are_supplied_by_the_caller(self):
        text = "We will remember Jane Doe."
        self.assertEqual(review([statement("a", "A", text)])["observations"], [])
        cues = merge_cues(DEFAULT_CUES, {"named_person": (r"\bjane doe\b",)})
        seen = review([statement("a", "A", text)], cues=cues)["observations"]
        self.assertEqual([(o["label"], o["cue"]) for o in seen], [("named_person", "Jane Doe")])

    def test_merging_extends_a_label_and_keeps_the_default_patterns_first(self):
        merged = merge_cues({"x": ("a",), "y": ("b",)}, {"x": ("c",), "z": ("d",)})
        self.assertEqual(merged, {"x": ("a", "c"), "y": ("b",), "z": ("d",)})

    def test_the_example_case_adds_its_wording_on_top_of_the_defaults(self):
        statements = json.loads((EXAMPLE / "statements.json").read_text(encoding="utf-8"))
        statements = statements["statements"] if isinstance(statements, dict) else statements
        generic = review(statements)
        with_case = review(statements, cues=citi_cues())
        labels = lambda r: {o["label"] for o in r["observations"]}  # noqa: E731
        self.assertLess(labels(generic), labels(with_case))
        self.assertTrue({"named_victim", "institutional_virtue_claim"} <= labels(with_case))
        amounts = {o["statement_id"] for o in with_case["observations"]
                   if o["label"] == "announced_action" and "$" in o["cue"]}
        self.assertEqual(amounts, {"citi_corporate_post", "skyler_fund_post"})


class ReviewOutputTests(unittest.TestCase):
    def test_one_observation_per_label_per_statement_naming_the_matched_text(self):
        text = "Look out for one another, and take care of one another."
        seen = review([statement("a", "A", text)])["observations"]
        self.assertEqual(len(seen), 1)
        self.assertEqual((seen[0]["label"], seen[0]["cue"], seen[0]["status"]),
                         ("collective_care_directive", "Look out for one another",
                          "wording_observed"))

    def test_a_recurrence_needs_two_different_actors(self):
        same_actor = review([statement("a", "A", "Take care of one another."),
                             statement("b", "A", "Look out for one another.")])
        self.assertEqual(same_actor["recurrences"], [])
        one_statement = review([statement("a", "A", "Take care of one another.")])
        self.assertEqual(one_statement["recurrences"], [])
        two_actors = review([statement("b", "B", "Look out for one another."),
                             statement("a", "A", "Take care of one another.")])
        self.assertEqual(two_actors["recurrences"], [{
            "label": "collective_care_directive", "statement_ids": ["a", "b"], "actor_count": 2,
            "interpretation": "cross_author_wording_recurrence_only"}])

    def test_outputs_are_sorted_whatever_order_statements_arrive_in(self):
        act = lambda i, s: {"action_id": i, "description": "d", "status": s}  # noqa: E731
        statements = [
            statement("c", "C", "Take care of one another.",
                      [act("z", "reported"), act("y", "announced")]),
            statement("a", "A", "We offer counseling and other resources available.",
                      [act("y", "firsthand_report")]),
            statement("b", "B", "Look out for one another."),
        ]
        r = review(statements)
        self.assertEqual([(o["statement_id"], o["label"]) for o in r["observations"]],
                         [("a", "announced_action"), ("b", "collective_care_directive"),
                          ("c", "collective_care_directive")])
        self.assertEqual([a["action_id"] for a in r["reported_actions"]], ["y", "z"])
        y = r["reported_actions"][0]
        self.assertEqual(y["source_statement_ids"], ["a", "c"])
        self.assertEqual(y["statuses"], ["announced", "firsthand_report"])
        self.assertEqual(r["statement_count"], 3)
        self.assertEqual(r["verdict"], "not_assessed")

    def test_each_kind_of_invalid_statement_is_refused_with_its_own_reason(self):
        good = statement("a", "A", "text")
        action = {"action_id": "x", "description": "d", "status": "announced"}
        cases = [
            ({**good, "actor": ""}, "missing nonempty actor"),
            ({**good, "text": 3}, "missing nonempty text"),
            ({**good, "coverage": "summary"}, "invalid coverage"),
            ({**good, "reported_actions": [{**action, "description": ""}]}, "incomplete action"),
            ({**good, "reported_actions": [{**action, "status": "verified"}]},
             "unknown action evidence status"),
        ]
        for bad, reason in cases:
            with self.assertRaisesRegex(ValueError, reason):
                review([bad])


class ReviewOrderingTests(unittest.TestCase):
    """Fixtures in which arrival order, date order and alphabetical order disagree."""

    def test_an_action_is_described_by_its_earliest_statement_not_the_first_to_arrive(self):
        def with_action(sid, date, description):
            row = statement(sid, sid.upper(), "text", [{"action_id": "fund",
                                                        "description": description,
                                                        "status": "announced"}])
            return {**row, "date": date}
        later = with_action("a", "2026-11-09", "described later")
        earlier = with_action("z", "2026-11-05", "described first")
        for order in ([later, earlier], [earlier, later]):
            action = review(order)["reported_actions"][0]
            self.assertEqual(action["description"], "described first")
            self.assertEqual(action["source_statement_ids"], ["a", "z"])

    def test_recurrences_are_listed_by_label_whatever_label_was_seen_first(self):
        statements = [
            statement("a", "A", "The security team showed professionalism."),
            statement("b", "B", "The security team showed bravery. Take care of one another."),
            statement("c", "C", "Look out for one another."),
        ]
        labels = [r["label"] for r in review(statements)["recurrences"]]
        self.assertEqual(labels, ["collective_care_directive", "response_recognition"])

    def test_observations_for_one_statement_are_listed_by_label(self):
        text = "Take care of one another. We will add additional security."
        seen = review([statement("a", "A", text)])["observations"]
        self.assertEqual([o["label"] for o in seen],
                         ["announced_action", "collective_care_directive"])

    def test_reported_actions_are_listed_by_action_id_not_by_first_seen(self):
        def acts(sid, action_id):
            return statement(sid, sid.upper(), "text", [
                {"action_id": action_id, "description": "d", "status": "announced"}])
        r = review([acts("a", "z-fund"), acts("b", "m-fund"), acts("c", "a-fund")])
        self.assertEqual([x["action_id"] for x in r["reported_actions"]],
                         ["a-fund", "m-fund", "z-fund"])


if __name__ == "__main__":
    unittest.main()
