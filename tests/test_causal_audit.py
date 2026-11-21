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


def tiny_case(**over):
    """Four control questions, one per assessment, over two sources with different origins."""
    base = {
        "case_id": "c1", "as_of": "2026-01-01",
        "sources": [{"id": "s1", "origin": "O1", "url": "u1"},
                    {"id": "s2", "origin": "O2", "url": "u2"}],
        "events": [
            {"id": "E2", "seq": 2, "kind": "k", "text": "second", "source_ids": ["s2", "s1", "s1"],
             "signals": ["bad", "exposed"], "time": "10:00", "evidence_level": "verified"},
            {"id": "E1", "seq": 1, "kind": "k", "text": "first", "source_ids": ["s1"],
             "signals": ["act"]},
        ],
        "questions": [
            {"id": "Q4", "title": "t4", "positive_signals": ["nothing"], "negative_signals": [],
             "required_evidence": ["r"], "limit": "l4"},
            {"id": "Q3", "title": "t3", "positive_signals": [], "negative_signals": ["bad"],
             "exposure_signals": ["exposed"], "required_evidence": ["r"], "limit": "l3"},
            {"id": "Q2", "title": "t2", "positive_signals": ["act"], "negative_signals": [],
             "required_evidence": ["r"], "limit": "l2"},
            {"id": "Q1", "title": "t1", "positive_signals": ["act"], "negative_signals": ["bad"],
             "required_evidence": ["r"], "limit": "l1"},
        ],
    }
    base.update(over)
    return base


class SyntheticAuditTests(unittest.TestCase):
    def test_each_question_gets_the_assessment_its_signals_imply(self):
        r = audit_causal_chain(tiny_case())
        got = {q["id"]: (q["assessment"], q["positive_event_ids"], q["negative_event_ids"],
                         q["exposure_event_ids"]) for q in r["control_questions"]}
        self.assertEqual(got, {
            "Q1": ("conflicting_evidence_requires_review", ["E1"], ["E2"], []),
            "Q2": ("affirmative_action_reported", ["E1"], [], []),
            "Q3": ("adverse_outcome_or_nonaction_reported", [], ["E2"], ["E2"]),
            "Q4": ("unresolved_in_reviewed_public_record", [], [], []),
        })
        self.assertEqual([q["id"] for q in r["control_questions"]], ["Q1", "Q2", "Q3", "Q4"])
        q = r["control_questions"][2]
        self.assertEqual((q["title"], q["required_evidence"], q["interpretive_limit"]),
                         ("t3", ["r"], "l3"))

    def test_the_summary_counts_questions_by_assessment(self):
        case = tiny_case()
        case["questions"] = [q for q in case["questions"] if q["id"] != "Q1"]  # no conflict
        for n in ("Q5", "Q6"):  # three adverse, one affirmative, one unresolved: all counts differ
            case["questions"].append({"id": n, "title": n, "positive_signals": [],
                                      "negative_signals": ["bad"], "required_evidence": [],
                                      "limit": "l"})
        self.assertEqual(audit_causal_chain(case)["summary"],
                         {"unresolved": 1, "reported_affirmative": 1, "reported_adverse": 3})

    def test_chronology_is_ordered_by_sequence_with_deduplicated_sorted_provenance(self):
        r = audit_causal_chain(tiny_case())
        self.assertEqual([c["id"] for c in r["chronology"]], ["E1", "E2"])
        first, second = r["chronology"]
        self.assertEqual((first["reported_time"], first["evidence_level"]),
                         ("unspecified", "reported"))
        self.assertEqual((second["reported_time"], second["evidence_level"]),
                         ("10:00", "verified"))
        self.assertEqual(second["source_ids"], ["s1", "s2"])
        self.assertEqual(second["origin_groups"], ["O1", "O2"])
        self.assertEqual(first["origin_groups"], ["O1"])
        self.assertEqual((r["source_count"], r["distinct_origin_count"]), (2, 2))

    def test_no_causation_or_intent_verdict_is_ever_issued(self):
        r = audit_causal_chain(tiny_case())
        self.assertEqual((r["causation_verdict"], r["intent_verdict"]),
                         ("not_determined", "not_determined"))

    def test_default_limitations_name_no_organisation(self):
        limits = audit_causal_chain(tiny_case())["limitations"]
        self.assertGreaterEqual(len(limits), 5)
        self.assertNotIn("citi", " ".join(limits).lower())

    def test_a_case_supplies_its_own_limitations(self):
        mine = ["Only what this case's sources say."]
        self.assertEqual(audit_causal_chain(tiny_case(limitations=mine))["limitations"], mine)

    def test_the_example_case_keeps_its_own_limitations(self):
        limits = audit_causal_chain(case())["limitations"]
        self.assertEqual(len(limits), 7)
        self.assertIn("Citi knowing", limits[0])

    def test_each_kind_of_invalid_case_is_refused_with_its_own_reason(self):
        def with_(**changes):
            c = tiny_case()
            c.update(changes)
            return c
        bad_id = tiny_case()
        bad_id["sources"][0]["id"] = ""
        dup_source = tiny_case()
        dup_source["sources"][1]["id"] = "s1"
        dup_event = tiny_case()
        dup_event["events"][1]["id"] = "E2"
        dup_question = tiny_case()
        dup_question["questions"][1]["id"] = "Q4"
        no_origin = tiny_case()
        no_origin["sources"][0]["origin"] = ""
        no_url = tiny_case()
        del no_url["sources"][1]["url"]
        same_seq = tiny_case()
        same_seq["events"][1]["seq"] = 2
        no_source = tiny_case()
        no_source["events"][0]["source_ids"] = []
        for bad, reason in [
            (bad_id, "empty/invalid id"), (dup_source, "duplicate source id"),
            (dup_event, "duplicate event id"), (dup_question, "duplicate question id"),
            (no_origin, "origin and URL"), (no_url, "origin and URL"),
            (same_seq, "duplicate event sequence"), (no_source, "missing/unknown source"),
        ]:
            with self.assertRaisesRegex(ValueError, reason):
                audit_causal_chain(bad)


if __name__ == "__main__":
    unittest.main()
