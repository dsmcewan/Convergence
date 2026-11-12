"""Causal-gap guards: absence of public evidence is not evidence of nonaction."""
import json
import unittest
from pathlib import Path

from convergence.causal_audit import audit_causal_chain

ROOT = Path(__file__).parent.parent / "examples" / "citi_tampa_2026"


def case():
    return json.loads((ROOT / "incident_record.json").read_text(encoding="utf-8"))


class AuditTests(unittest.TestCase):
    def test_unresolved_protection_is_not_declared_failure(self):
        r = audit_causal_chain(case())
        by_id = {x["id"]: x for x in r["control_questions"]}
        self.assertEqual(by_id["Q03"]["assessment"], "unresolved_in_reviewed_public_record")
        self.assertTrue(by_id["Q03"]["exposure_event_ids"])
        self.assertEqual(r["causation_verdict"], "not_determined")

    def test_perimeter_breach_documented_without_design_negligence(self):
        r = audit_causal_chain(case())
        q = next(x for x in r["control_questions"] if x["id"] == "Q04")
        self.assertEqual(q["assessment"], "adverse_outcome_or_nonaction_reported")
        self.assertIn("E05", q["negative_event_ids"])
        self.assertIn("design", q["interpretive_limit"])

    def test_heroism_does_not_resolve_prevention(self):
        r = audit_causal_chain(case())
        by_id = {x["id"]: x for x in r["control_questions"]}
        self.assertEqual(by_id["Q06"]["assessment"], "affirmative_action_reported")
        self.assertEqual(by_id["Q01"]["assessment"], "unresolved_in_reviewed_public_record")
        self.assertEqual(by_id["Q05"]["assessment"], "unresolved_in_reviewed_public_record")

    def test_shared_source_origin_deduplicated(self):
        x = case()
        x["sources"].append({"id": "new_media", "origin": "HCSO_NOV5_ACCOUNT",
                             "url": "https://example.com/repost"})
        r = audit_causal_chain(x)
        self.assertEqual(r["source_count"], len(x["sources"]))
        self.assertEqual(r["distinct_origin_count"], len({s["origin"] for s in x["sources"]}))

    def test_event_order_independent_of_input_sequence(self):
        x, y = case(), case()
        y["events"].reverse()
        y["questions"].reverse()
        self.assertEqual(json.dumps(audit_causal_chain(x), sort_keys=True),
                         json.dumps(audit_causal_chain(y), sort_keys=True))

    def test_rejects_orphaned_provenance(self):
        x = case()
        x["events"][0]["source_ids"] = ["unknown-source"]
        with self.assertRaises(ValueError):
            audit_causal_chain(x)


if __name__ == "__main__":
    unittest.main()
