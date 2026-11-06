import copy
import json
import tempfile
import unittest
from pathlib import Path

from src.compound_intelligence.benchmark import generate
from src.compound_intelligence.problem_runner import fixture
from src.compound_intelligence.progress import (
    compare_reports, read_report, receipt, validate_report,
)

TASKS = json.loads((Path(__file__).resolve().parents[1] / "examples/challenges.json").read_text())


class ProgressTests(unittest.TestCase):
    def report(self, root):
        return generate(TASKS, ["fixture-correct", "fixture-incorrect"],
                        root, fixture, fixture_mode=True)

    def test_same_fixture_is_not_fictitious_improvement(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            prior = self.report(root)
            current = self.report(root)
            changes = compare_reports(prior, current)
            self.assertTrue(all(m["outcome"] == "UNCHANGED" for m in changes["models"]))
            self.assertIn("does not prove learning", changes["interpretation"])

    def test_valid_more_and_fewer_ledger_outcomes(self):
        with tempfile.TemporaryDirectory() as d:
            before = self.report(Path(d))
            after = copy.deepcopy(before)
            item = after["models"][1]["overall"]
            item["verified"] += 1
            item["rejected"] -= 1
            item["verified_per_attempt"] = 0.5
            diff = compare_reports(before, after)
            self.assertEqual(diff["models"][1]["outcome"], "MORE_VERIFIED")
            backwards = compare_reports(after, before)
            self.assertEqual(backwards["models"][1]["outcome"], "FEWER_VERIFIED")

    def test_reject_different_dataset(self):
        with tempfile.TemporaryDirectory() as d:
            before = self.report(Path(d))
            after = copy.deepcopy(before)
            after["dataset_sha256"] = "f" * 64
            with self.assertRaisesRegex(ValueError, "different datasets"):
                compare_reports(before, after)

    def test_reject_simulated_vs_real(self):
        with tempfile.TemporaryDirectory() as d:
            before = self.report(Path(d))
            after = copy.deepcopy(before)
            after["run_mode"] = "MODEL_PROPOSALS"
            with self.assertRaisesRegex(ValueError, "fixture and real"):
                compare_reports(before, after)

    def test_reject_inconsistent_counts(self):
        with tempfile.TemporaryDirectory() as d:
            before = self.report(Path(d))
            bad = copy.deepcopy(before)
            bad["models"][0]["overall"]["attempted"] = 100
            with self.assertRaisesRegex(ValueError, "inconsistent"):
                validate_report(bad)

    def test_reject_changed_model_roster(self):
        with tempfile.TemporaryDirectory() as d:
            before = self.report(Path(d))
            after = copy.deepcopy(before)
            after["models"][0]["model"] = "different"
            with self.assertRaisesRegex(ValueError, "different model"):
                compare_reports(before, after)

    def test_receipt_retains_origin_and_hash(self):
        with tempfile.TemporaryDirectory() as d:
            report = self.report(Path(d))
            r = receipt(report, "123456")
            self.assertEqual(r["evidence_origin"], "SIMULATED_FIXTURE")
            self.assertEqual(r["status"], "RECORDED_NOT_PROMOTED")
            self.assertEqual(len(r["benchmark_sha256"]), 64)
            with self.assertRaises(ValueError):
                receipt(report, "not-a-run")

    def test_read_report_is_bounded(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            report = self.report(root)
            path = root / "report.json"
            path.write_text(json.dumps(report))
            self.assertEqual(read_report(path)["schema"], report["schema"])
            path.write_text("a" * (1_000_001))
            with self.assertRaisesRegex(ValueError, "exceeds"):
                read_report(path)


if __name__ == "__main__":
    unittest.main()
