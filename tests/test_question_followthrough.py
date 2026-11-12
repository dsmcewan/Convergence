"""Question/response audit guards: no claim of direct answers without evidence."""
import copy
import json
import unittest
from pathlib import Path

from convergence.question_followthrough import audit_followthrough

PATH = (Path(__file__).parent.parent / "examples" / "citi_tampa_2026"
        / "question_followthrough_20261112.json")


def case():
    return json.loads(PATH.read_text(encoding="utf-8"))


class QuestionFollowthroughTests(unittest.TestCase):
    def test_expected_public_questions_and_statuses(self):
        r = audit_followthrough(case())
        self.assertEqual(r["question_count"], 9)
        by_id = {i["id"]: i for i in r["issues"]}
        expected = {
            "P01": "official_operational_description_partial",
            "P02": "independent_public_fact_on_aspect",
            "P03": "unverified_firsthand_claims_only",
            "P04": "unverified_firsthand_claims_only",
            "P05": "independent_public_fact_on_aspect",
            "P06": "no_relevant_response_in_selected_public_material",
            "P07": "specific_commitment_publicly_reported",
            "P08": "specific_commitment_publicly_reported",
            "P09": "independent_public_fact_on_aspect",
        }
        self.assertEqual({k: x["status"] for k, x in by_id.items()}, expected)

    def test_no_automatic_full_answer_from_partial_fact(self):
        r = audit_followthrough(case())
        self.assertTrue(all(
            not x["full_answer_independently_verified"] for x in r["issues"]
        ))
        self.assertEqual(r["inferences"]["institutional_neglect"], "not_determined")
        self.assertEqual(r["inferences"]["communications_caused_distraction"],
                         "not_established")

    def test_forum_notification_times_not_misrepresented_as_verified(self):
        r = audit_followthrough(case())
        by_id = {i["id"]: i for i in r["issues"]}
        for issue in ("P03", "P04"):
            self.assertFalse(by_id[issue]["verified_incident_fact_ids"])
            self.assertTrue(by_id[issue]["anonymous_employee_claim_ids"])

    def test_no_direct_reply_is_invented(self):
        r = audit_followthrough(case())
        self.assertTrue(all(
            not x["all_official_responses_are_direct_to_original_question"]
            for x in r["issues"]
        ))

    def test_repeated_reporting_groups_by_original_source(self):
        d = case()
        # Multiple reports quoting the same Skyler remarks share one origin.
        d["sources"].append({
            "id": "skyler_mirror", "url": "https://example.com/republication",
            "origin": "SKYLER_NOV5_PUBLIC_REMARKS",
            "quality": "news_reporting",
        })
        out = audit_followthrough(d)
        self.assertEqual(out["source_count"], len(d["sources"]))
        self.assertEqual(out["underlying_source_origin_count"], 7)

    def test_an_unanswered_question_is_not_asserted_never_answered(self):
        r = audit_followthrough(case())
        issue = next(i for i in r["issues"] if i["id"] == "P06")
        self.assertEqual(issue["scope"], "selected_public_material")
        self.assertEqual(issue["response_ids"], [])
        self.assertFalse(r["inferences"]["all_questions_answered"])

    def test_bad_source_and_orphan_questions_are_rejected(self):
        d = case()
        d["responses"][0]["source_id"] = "unknown"
        with self.assertRaisesRegex(ValueError, "source"):
            audit_followthrough(d)
        d = case()
        d["responses"][0]["question_ids"] = ["unknown"]
        with self.assertRaisesRegex(ValueError, "orphan question"):
            audit_followthrough(d)

    def test_duplicate_ids_rejected(self):
        d = case()
        d["responses"].append(copy.deepcopy(d["responses"][0]))
        with self.assertRaisesRegex(ValueError, "duplicated response id"):
            audit_followthrough(d)

    def test_order_independence(self):
        d1 = case()
        d2 = case()
        for key in ("questions", "responses", "sources"):
            d2[key].reverse()
        self.assertEqual(
            json.dumps(audit_followthrough(d1), sort_keys=True),
            json.dumps(audit_followthrough(d2), sort_keys=True),
        )


if __name__ == "__main__":
    unittest.main()
