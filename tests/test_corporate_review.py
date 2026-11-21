"""Negative controls for evidence-conservative corporate wording review."""
import json
import unittest

from convergence.corporate_review import review


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
        self.assertEqual(json.dumps(review([x, y]), sort_keys=True),
                         json.dumps(review([y, x]), sort_keys=True))
        with self.assertRaises(ValueError):
            review([x, x])

    # A dollar sign is not a word character, so a \b in front of it can never match after a space:
    # the amount cues were dead for ordinary sentences.
    def test_dollar_amount_in_a_sentence_is_an_announced_action_cue(self):
        result = review([
            statement("a", "A", "Citi announced a $250,000 contribution to the fund."),
            statement("b", "B", "The fund will receive $250,000."),
        ])
        cues = {o["statement_id"]: o["cue"] for o in result["observations"]
                if o["label"] == "announced_action"}
        self.assertEqual(cues, {"a": "$250,000 contribution", "b": "$250,000"})

    def test_larger_amount_sharing_the_prefix_is_not_the_announced_amount(self):
        result = review([statement("a", "A", "The settlement was $250,000,000.")])
        labels = [o["label"] for o in result["observations"]]
        self.assertNotIn("announced_action", labels)


if __name__ == "__main__":
    unittest.main()
