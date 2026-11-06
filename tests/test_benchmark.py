import json
import tempfile
import unittest
from pathlib import Path

from src.compound_intelligence.benchmark import generate, metrics, wilson_interval
from src.compound_intelligence.problem_runner import fixture


TASKS = json.loads((Path(__file__).resolve().parents[1] / "examples/challenges.json").read_text())


class BenchmarkTests(unittest.TestCase):
    def test_fixture_report_counts_and_scope(self):
        with tempfile.TemporaryDirectory() as root:
            result = generate(TASKS, ["fixture-correct", "fixture-incorrect"],
                              Path(root), fixture, fixture_mode=True)
            self.assertEqual(result["run_mode"], "SIMULATED_FIXTURE")
            self.assertEqual(result["task_count"], 2)
            self.assertEqual(len(result["dataset_sha256"]), 64)
            a, b = result["models"]
            self.assertEqual(a["overall"]["verified_per_attempt"], 1.0)
            self.assertEqual(b["overall"]["verified_per_attempt"], 0.0)
            self.assertEqual(set(a["by_task_type"]), {"extract", "patch"})

    def test_replay_keeps_scores_and_does_not_call_proposer(self):
        with tempfile.TemporaryDirectory() as root:
            before = generate(TASKS, ["fixture-correct"], Path(root), fixture,
                              fixture_mode=True)
            def fail(*args):
                raise AssertionError("called after successful evidence recording")
            after = generate(TASKS, ["fixture-correct"], Path(root), fail,
                             fixture_mode=True)
            self.assertEqual(before["models"], after["models"])
            self.assertEqual(after["results"][0]["new"], False)

    def test_no_result_counts_in_denominator(self):
        score = metrics([
            {"status": "VERIFIED"}, {"status": "REJECTED"},
            {"status": "NO_RESULT"}, {"status": "NO_RESULT"}])
        self.assertEqual(score["attempted"], 4)
        self.assertEqual(score["completion_rate"], 0.5)
        self.assertEqual(score["verified_per_attempt"], 0.25)
        self.assertEqual(score["exact_match_given_answer"], 0.5)

    def test_only_missing_results(self):
        score = metrics([{"status": "NO_RESULT"}])
        self.assertIsNone(score["exact_match_given_answer"])
        self.assertEqual(score["verified_per_attempt"], 0.0)

    def test_no_results_or_unknown_status(self):
        self.assertIsNone(metrics([])["verified_per_attempt"])
        self.assertIsNone(wilson_interval(0, 0))
        with self.assertRaises(ValueError):
            metrics([{"status": "made-up"}])

    def test_wilson_interval_bounds(self):
        lo, hi = wilson_interval(1, 2)
        self.assertLess(lo, 0.5)
        self.assertGreater(hi, 0.5)
        self.assertEqual(wilson_interval(0, 1)[0], 0)
        self.assertEqual(wilson_interval(1, 1)[1], 1)

    def test_reference_change_changes_dataset_digest(self):
        with tempfile.TemporaryDirectory() as root:
            original = generate(TASKS, ["fixture-correct"], Path(root), fixture,
                                fixture_mode=True)
            edited = [dict(t) for t in TASKS]
            edited[0]["expected"] = {**edited[0]["expected"], "returns_days": 31}
            new = generate(edited, ["fixture-correct"], Path(root), fixture,
                           fixture_mode=True)
            self.assertNotEqual(original["dataset_sha256"], new["dataset_sha256"])


if __name__ == "__main__":
    unittest.main()
