"""Adversarial tests of deterministic, intentionally non-semantic handover preservation."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from src.compound_intelligence.agentproof import parse_manifest
from src.compound_intelligence.context_preservation import evaluate, fixture, render_html, validate


class ContextPreservationTests(unittest.TestCase):
    def test_fixture_exposes_omissions_exact_retention_and_drift(self):
        report = evaluate(fixture())
        self.assertEqual(report["origin"], "SYNTHETIC_OR_CALLER_SUPPLIED")
        self.assertEqual(report["status"], "BENCHMARKED_NOT_PROMOTED")
        by_id = {x["candidate_id"]: x for x in report["candidates"]}
        brief = by_id["brief-chat"]
        self.assertEqual(brief["state"], "HOLD")
        self.assertEqual(brief["critical_total"], 4)
        self.assertEqual(brief["critical_retained"], 1)
        self.assertEqual(brief["counts"]["MISSING"], 4)
        complete = by_id["evidence-checkpoint"]
        self.assertEqual(complete["state"], "PASS_LOSSLESS")
        self.assertEqual(complete["critical_retained"], 4)
        self.assertEqual(complete["counts"]["RETAINED"], 7)
        drift = by_id["unsafe-drift"]
        self.assertEqual(drift["state"], "HOLD")
        self.assertEqual(drift["counts"]["STALE_VERSION"], 1)
        self.assertEqual(drift["counts"]["CONTRADICTED_VALUE"], 1)
        self.assertEqual(drift["counts"]["EVIDENCE_STATUS_DRIFT"], 1)
        self.assertEqual(drift["counts"]["UNSUPPORTED"], 1)
        self.assertEqual(drift["critical_retained"], 2)

    def test_reporting_is_deterministic_and_input_is_not_mutated(self):
        spec = fixture()
        original = copy.deepcopy(spec)
        self.assertEqual(evaluate(spec), evaluate(spec))
        self.assertEqual(spec, original)
        self.assertRegex(evaluate(spec)["source_sha256"], r"^[0-9a-f]{64}$")

    def test_order_changes_do_not_alter_outcomes_but_do_alter_input_identity(self):
        spec = fixture()
        original = evaluate(spec)
        spec["source"]["facts"].reverse()
        spec["candidates"].reverse()
        for candidate in spec["candidates"]:
            candidate["entries"].reverse()
        reordered = evaluate(spec)
        self.assertEqual(original["candidates"], reordered["candidates"])
        self.assertNotEqual(original["input_sha256"], reordered["input_sha256"])

    def test_missing_supporting_fact_can_pass_critical_only(self):
        spec = fixture()
        item = next(x for x in spec["candidates"] if x["candidate_id"] == "evidence-checkpoint")
        item["entries"] = [x for x in item["entries"] if x["fact_id"] != "product"]
        out = next(x for x in evaluate(spec)["candidates"] if x["candidate_id"] == "evidence-checkpoint")
        self.assertEqual(out["state"], "PASS_CRITICAL_ONLY")
        self.assertEqual(out["counts"]["MISSING"], 1)

    def test_unverified_hypothesis_never_promoted_silently(self):
        spec = fixture()
        entry = next(x for c in spec["candidates"] if c["candidate_id"] == "evidence-checkpoint"
                     for x in c["entries"] if x["fact_id"] == "growth")
        entry["evidence_status"] = "DECLARED_VERIFIED"
        out = next(x for x in evaluate(spec)["candidates"] if x["candidate_id"] == "evidence-checkpoint")
        self.assertEqual(out["state"], "HOLD")
        self.assertEqual(out["counts"]["EVIDENCE_STATUS_DRIFT"], 1)

    def test_provenance_mismatch_and_independent_unknown_claims_hold(self):
        spec = fixture()
        candidate = spec["candidates"][1]
        candidate["entries"][0]["source_ref"] = "synthetic:wrong"
        candidate["entries"].append({
            "fact_id": "private-api", "value": "can-trade", "source_ref": "synthetic:unknown",
            "source_version": 2, "evidence_status": "HYPOTHESIS"
        })
        out = next(x for x in evaluate(spec)["candidates"] if x["candidate_id"] == candidate["candidate_id"])
        self.assertEqual(out["counts"]["PROVENANCE_DRIFT"], 1)
        self.assertEqual(out["counts"]["UNSUPPORTED"], 1)
        self.assertEqual(out["state"], "HOLD")

    def test_structural_conflicts_fail_closed_without_partial_report(self):
        variants = []
        base = fixture()
        bad = copy.deepcopy(base)
        bad["source"]["facts"][1]["fact_id"] = bad["source"]["facts"][0]["fact_id"]
        variants.append(bad)
        bad = copy.deepcopy(base)
        bad["candidates"][0]["entries"].append(copy.deepcopy(bad["candidates"][0]["entries"][0]))
        variants.append(bad)
        bad = copy.deepcopy(base)
        bad["candidates"][1]["candidate_id"] = bad["candidates"][0]["candidate_id"]
        variants.append(bad)
        bad = copy.deepcopy(base)
        bad["candidates"][1]["entries"][0]["source_version"] = True
        variants.append(bad)
        bad = copy.deepcopy(base)
        bad["source"]["facts"][0]["importance"] = "ALMOST_CRITICAL"
        variants.append(bad)
        bad = copy.deepcopy(base)
        bad["source"]["facts"][0]["value"] = ""
        variants.append(bad)
        bad = copy.deepcopy(base)
        bad["source"]["facts"][0]["value"] = "\ud800"
        variants.append(bad)
        bad = copy.deepcopy(base)
        bad["source"]["facts"][0]["secret"] = "unexpected"
        variants.append(bad)
        bad = copy.deepcopy(base)
        bad["source"]["facts"][0]["importance"] = ["CRITICAL"]
        variants.append(bad)
        bad = copy.deepcopy(base)
        bad["source"]["facts"][0]["evidence_status"] = {"status": "DECLARED_VERIFIED"}
        variants.append(bad)
        for variant in variants:
            with self.subTest(variant=str(variant)[:80]):
                with self.assertRaises(ValueError):
                    evaluate(variant)

    def test_rejects_oversized_and_boolean_versions(self):
        spec = fixture()
        spec["source"]["version"] = True
        with self.assertRaises(ValueError):
            evaluate(spec)
        spec = fixture()
        spec["source"]["facts"][0]["value"] = "x" * 65537
        with self.assertRaises(ValueError):
            evaluate(spec)

    def test_duplicate_json_members_rejected_by_existing_reference_parser(self):
        with self.assertRaises(ValueError):
            parse_manifest('{"schema":"a","schema":"b","source":{}}')

    def test_html_is_offline_escaped_and_no_scripts(self):
        result = evaluate(fixture())
        result["candidates"][0]["candidate_id"] = "<img src=x onerror=alert(1)>"
        page = render_html(result)
        self.assertIn("&lt;img", page)
        self.assertNotIn("<img", page)
        self.assertNotIn("<script", page)
        self.assertIn("Content-Security-Policy", page)

    def test_cli_demo_recovery_and_invalid_input(self):
        cmd = [sys.executable, "-m", "src.compound_intelligence.context_preservation"]
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)
            page = target / "report.html"
            ok = subprocess.run(cmd + ["--demo", "--html", str(page)],
                                capture_output=True, text=True)
            self.assertEqual(ok.returncode, 0, ok.stderr)
            result = json.loads(ok.stdout)
            self.assertEqual(len(result["candidates"]), 3)
            self.assertTrue(page.is_file())
            self.assertIn("Fictional AI handover", page.read_text())
            bad = target / "bad.json"
            bad.write_text('{"schema":"context-preservation.v1","schema":"duplicate"}')
            fail = subprocess.run(cmd + ["--input", str(bad)],
                                  capture_output=True, text=True)
            self.assertEqual(fail.returncode, 2)
            self.assertEqual(json.loads(fail.stdout)["status"], "REJECTED")


if __name__ == "__main__":
    unittest.main()
