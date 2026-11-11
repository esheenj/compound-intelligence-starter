"""Adversarial offline tests for non-authoritative explanation and review triage."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from src.compound_intelligence.agentproof import parse_manifest
from src.compound_intelligence.explainable_review import fixture, inspect, render_html


class ExplainableReviewTests(unittest.TestCase):
    def test_six_invented_decisions_have_conservative_gates(self):
        r = inspect(fixture())
        self.assertEqual((r["decisions_checked"], r["hold_count"],
                          r["human_review_count"], r["recorded_review_count"]), (6, 3, 2, 1))
        self.assertEqual(r["status"], "REVIEW_ONLY_NO_EXECUTION")
        self.assertEqual(r["execution_authority"], "NONE")
        by_id = {x["decision_id"]: x for x in r["results"]}
        self.assertEqual(by_id["routine"]["gate"], "REVIEW_RECORDED_NOT_AUTHORIZED")
        self.assertEqual(by_id["routine"]["self_reported_sample"], {"correct": 8, "cases": 10})
        self.assertEqual(by_id["high-impact"]["gate"], "HUMAN_REVIEW_REQUIRED")
        self.assertIn("HIGH_IMPACT", by_id["high-impact"]["reasons"])
        self.assertEqual(by_id["contradicted"]["gate"], "HOLD")
        self.assertIn("OPPOSING_EVIDENCE", by_id["contradicted"]["reasons"])
        self.assertIn("STALE_REVISION", by_id["stale"]["reasons"])
        self.assertIn("UNVERIFIED_SOURCE", by_id["unverified"]["reasons"])
        self.assertIn("NO_CONFIDENCE_METHOD", by_id["unscored"]["reasons"])
        self.assertTrue(all(x["execution_authority"] == "NONE" for x in r["results"]))

    def test_deterministic_report_and_unchanged_input(self):
        data = fixture()
        original = copy.deepcopy(data)
        self.assertEqual(inspect(data), inspect(data))
        self.assertEqual(data, original)
        self.assertRegex(inspect(data)["input_sha256"], r"^[0-9a-f]{64}$")

    def test_permutation_preserves_gate_but_changes_input_hash(self):
        doc = fixture()
        old = inspect(doc)
        doc["sources"].reverse()
        doc["decisions"].reverse()
        for d in doc["decisions"]:
            d["support"].reverse()
            d["oppose"].reverse()
        new = inspect(doc)
        self.assertEqual(old["results"], new["results"])
        self.assertNotEqual(old["input_sha256"], new["input_sha256"])

    def test_unverified_assumed_approved_still_held(self):
        doc = fixture()
        d = doc["decisions"][4]
        self.assertEqual(d["review"], "RECORDED_APPROVE")
        outcome = next(x for x in inspect(doc)["results"] if x["decision_id"] == d["decision_id"])
        self.assertEqual(outcome["gate"], "HOLD")
        self.assertIn("UNVERIFIED_SOURCE", outcome["reasons"])

    def test_rejected_human_record_never_authorizes(self):
        doc = fixture()
        doc["decisions"][0]["review"] = "RECORDED_REJECT"
        r = next(x for x in inspect(doc)["results"] if x["decision_id"] == "routine")
        self.assertEqual(r["gate"], "HOLD")
        self.assertIn("REVIEW_REJECTED", r["reasons"])
        self.assertEqual(r["execution_authority"], "NONE")

    def test_unknown_reference_holds_instead_of_inventing_source(self):
        doc = fixture()
        doc["decisions"][0]["support"][0]["source_id"] = "fictional-missing"
        result = next(x for x in inspect(doc)["results"] if x["decision_id"] == "routine")
        self.assertEqual(result["gate"], "HOLD")
        self.assertIn("UNKNOWN_SOURCE", result["reasons"])
        self.assertEqual(result["evidence"][0]["statement"], None)

    def test_no_support_holds_even_if_review_approved(self):
        doc = fixture()
        doc["decisions"][0]["support"] = []
        x = next(x for x in inspect(doc)["results"] if x["decision_id"] == "routine")
        self.assertEqual(x["gate"], "HOLD")
        self.assertIn("NO_SUPPORT", x["reasons"])

    def test_sample_outcome_not_reinterpreted_as_probability(self):
        doc = fixture()
        d = doc["decisions"][0]
        d["confidence"] = {"method": "SELF_REPORTED_SAMPLE", "correct": 0, "cases": 1}
        x = next(x for x in inspect(doc)["results"] if x["decision_id"] == d["decision_id"])
        self.assertEqual(x["self_reported_sample"], {"correct": 0, "cases": 1})
        self.assertNotIn("probability", x)
        self.assertEqual(x["gate"], "REVIEW_RECORDED_NOT_AUTHORIZED")

    def test_bad_types_duplicates_and_overlimits_rejected(self):
        base = fixture()
        variants = []
        def changed(fn):
            v = copy.deepcopy(base)
            fn(v)
            variants.append(v)
        changed(lambda d: d["sources"].append(copy.deepcopy(d["sources"][0])))
        changed(lambda d: d["decisions"].append(copy.deepcopy(d["decisions"][0])))
        changed(lambda d: d["decisions"][0]["support"].append(copy.deepcopy(d["decisions"][0]["support"][0])))
        changed(lambda d: d["decisions"][0]["oppose"].append(copy.deepcopy(d["decisions"][0]["support"][0])))
        changed(lambda d: d["sources"][0].update(revision=True))
        changed(lambda d: d["sources"][0].update(evidence_status=[]))
        changed(lambda d: d["decisions"][0].update(impact=["LOW"]))
        changed(lambda d: d["decisions"][0].update(review=1))
        changed(lambda d: d["decisions"][0]["confidence"].update(correct=True))
        changed(lambda d: d["decisions"][0]["confidence"].update(correct=11))
        changed(lambda d: d["decisions"][5]["confidence"].update(correct=0))
        changed(lambda d: d["decisions"][0].update(action="\ud800"))
        changed(lambda d: d["decisions"][0].update(unknown_key="unexpected"))
        changed(lambda d: d.update(schema="different"))
        changed(lambda d: d["sources"][0].update(statement="s" * 70000))
        for v in variants:
            with self.subTest(v=str(v)[:80]):
                with self.assertRaises(ValueError):
                    inspect(v)

    def test_no_actual_human_review_or_execution_authority_claim(self):
        r = inspect(fixture())
        self.assertIn("no", r["scope"].lower())
        self.assertNotIn("CERTIFIED", r["status"])
        self.assertTrue(all(x["gate"] != "APPROVED" for x in r["results"]))

    def test_html_escapes_untrusted_decisions(self):
        r = inspect(fixture())
        r["results"][0]["decision_id"] = '<img src=x onerror=alert(1)>'
        html_text = render_html(r)
        self.assertIn("&lt;img", html_text)
        self.assertNotIn("<img", html_text)
        self.assertNotIn("<script", html_text)
        self.assertIn("Content-Security-Policy", html_text)

    def test_reuses_duplicate_key_rejection(self):
        with self.assertRaises(ValueError):
            parse_manifest('{"schema":"a","schema":"b"}')

    def test_cli_good_bad_and_offline_html(self):
        cmd = [sys.executable, "-m", "src.compound_intelligence.explainable_review"]
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            result = subprocess.run(cmd+["--demo","--html",str(target/"report.html")],
                                    capture_output=True,text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["decisions_checked"], 6)
            self.assertTrue((target/"report.html").is_file())
            bad = target/"invalid.json"
            bad.write_text('{"schema":"one","schema":"two"}', encoding="utf-8")
            failed = subprocess.run(cmd+["--input",str(bad)],capture_output=True,text=True)
            self.assertEqual(failed.returncode, 2)
            self.assertEqual(json.loads(failed.stdout)["status"], "REJECTED")


if __name__ == "__main__":
    unittest.main()
