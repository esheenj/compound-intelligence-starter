"""Offline, adversarial tests for non-authoritative multi-model disagreement triage."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from src.compound_intelligence.agentproof import parse_manifest
from src.compound_intelligence.model_disagreement import fixture, inspect, render_html


class ModelDisagreementTests(unittest.TestCase):
    def test_fictional_fixture_shows_split_wrong_consensus_and_abstention(self):
        report = inspect(fixture())
        self.assertEqual(report["origin"], "SYNTHETIC_OR_CALLER_SUPPLIED")
        self.assertEqual(report["status"], "REVIEW_REQUIRED")
        self.assertEqual(report["model_count"], 3)
        self.assertEqual(report["case_count"], 5)
        self.assertEqual(report["review_cases"], 4)
        self.assertEqual(report["critical_review_cases"], 2)
        by_id = {r["case_id"]: r for r in report["records"]}
        self.assertEqual(by_id["unverified-consensus"]["state"], "UNVERIFIED_CONSENSUS")
        self.assertEqual(by_id["unverified-consensus"]["triage"], "REVIEW")
        self.assertEqual(by_id["split-critical-decision"]["state"], "DISAGREEMENT")
        self.assertEqual(by_id["split-critical-decision"]["matching_reference"], 2)
        self.assertEqual(by_id["split-critical-decision"]["contradicting_reference"], 1)
        self.assertEqual(by_id["unanimous-wrong"]["state"], "CONTRADICTS_SUPPLIED_REFERENCE")
        self.assertEqual(by_id["unanimous-wrong"]["contradicting_reference"], 3)
        self.assertEqual(by_id["missing-and-abstained"]["state"], "INCOMPLETE")
        self.assertEqual(by_id["missing-and-abstained"]["missing_models"], ["fictional-gamma"])
        self.assertEqual(by_id["missing-and-abstained"]["abstained_models"], ["fictional-beta"])
        self.assertEqual(by_id["matches-supplied"]["state"], "MATCHES_SUPPLIED_REFERENCE")
        self.assertEqual(by_id["matches-supplied"]["triage"], "REFERENCE_MATCH_ONLY")

    def test_determinism_and_no_input_mutation(self):
        data = fixture()
        old = copy.deepcopy(data)
        self.assertEqual(inspect(data), inspect(data))
        self.assertEqual(data, old)
        self.assertRegex(inspect(data)["input_sha256"], r"^[a-f0-9]{64}$")

    def test_response_order_only_affects_input_hash(self):
        data = fixture()
        a = inspect(data)
        for case in data["cases"]:
            case["responses"].reverse()
        data["cases"].reverse()
        b = inspect(data)
        self.assertEqual(a["records"], b["records"])
        self.assertNotEqual(a["input_sha256"], b["input_sha256"])

    def test_all_abstain_no_answer(self):
        data = fixture()
        c = data["cases"][0]
        c["responses"] = [{"model_id": m, "status": "ABSTAIN", "answer": None}
                          for m in data["models"]]
        result = next(r for r in inspect(data)["records"] if r["case_id"] == c["case_id"])
        self.assertEqual(result["state"], "NO_ANSWERS")
        self.assertEqual(result["answers_observed"], 0)
        self.assertEqual(len(result["abstained_models"]), 3)

    def test_reference_not_secretly_verified(self):
        data = fixture()
        data["cases"] = [data["cases"][-1]]
        report = inspect(data)
        self.assertEqual(report["status"], "REFERENCE_MATCHES_ONLY")
        self.assertIn("untrusted supplied reference", report["scope"])

    def test_structural_conflicts_fail_closed(self):
        base = fixture()
        variants = []
        def variant(mutator):
            doc = copy.deepcopy(base)
            mutator(doc)
            variants.append(doc)
        variant(lambda d:d["models"].append(d["models"][0]))
        variant(lambda d:d["cases"].append(copy.deepcopy(d["cases"][0])))
        variant(lambda d:d["cases"][0]["responses"].append(copy.deepcopy(d["cases"][0]["responses"][0])))
        variant(lambda d:d["cases"][0]["responses"][0].update(model_id="fictional-unknown"))
        variant(lambda d:d["cases"][0].update(critical=1))
        variant(lambda d:d["cases"][0]["responses"][0].update(status="ABSTAIN"))
        variant(lambda d:d["cases"][0]["responses"][0].update(status="PENDING"))
        variant(lambda d:d["cases"][0]["responses"][0].update(answer=""))
        variant(lambda d:d["cases"][0]["responses"][0].update(answer="\ud800"))
        variant(lambda d:d["cases"][0].update(unexpected="extra"))
        variant(lambda d:d.update(schema="wrong-version"))
        variant(lambda d:d["cases"][0].update(reference=[]))
        for doc in variants:
            with self.subTest(case=str(doc)[:70]):
                with self.assertRaises(ValueError):
                    inspect(doc)

    def test_missing_responses_are_explicit_not_imputed(self):
        doc = fixture()
        doc["cases"][1]["responses"] = []
        c = next(r for r in inspect(doc)["records"] if r["case_id"] == "split-critical-decision")
        self.assertEqual(c["state"], "NO_ANSWERS")
        self.assertEqual(c["missing_models"], sorted(doc["models"]))
        self.assertEqual(c["triage"], "REVIEW")

    def test_no_fabricated_model_calls_or_silent_truth_promotion(self):
        result = inspect(fixture())
        self.assertFalse(any(k in result for k in ("model_executed", "truth_certified", "trade_authorized")))
        self.assertTrue(all(r["triage"] != "APPROVED" for r in result["records"]))

    def test_duplicate_json_fields_rejected_by_reused_safe_parser(self):
        with self.assertRaises(ValueError):
            parse_manifest('{"schema":"one","schema":"two","models":[],"cases":[]}')

    def test_script_free_html_escapes_untrusted_values(self):
        r = inspect(fixture())
        r["records"][0]["case_id"] = '<img src=x onerror=alert(1)>'
        page = render_html(r)
        self.assertIn("&lt;img", page)
        self.assertNotIn("<img", page)
        self.assertNotIn("<script", page)
        self.assertIn("Content-Security-Policy", page)

    def test_cli_demo_and_rejected_input(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            cmd=[sys.executable, "-m", "src.compound_intelligence.model_disagreement"]
            page=root/"review.html"
            proc=subprocess.run(cmd+["--demo","--html",str(page)],capture_output=True,text=True)
            self.assertEqual(proc.returncode,0,proc.stderr)
            result=json.loads(proc.stdout)
            self.assertEqual(result["case_count"],5)
            self.assertTrue(page.exists())
            wrong=root/"dup.json"
            wrong.write_text('{"schema":"x","schema":"x"}',encoding="utf-8")
            failed=subprocess.run(cmd+["--input",str(wrong)],capture_output=True,text=True)
            self.assertEqual(failed.returncode,2)
            self.assertEqual(json.loads(failed.stdout)["status"],"REJECTED")


if __name__=="__main__":
    unittest.main()
