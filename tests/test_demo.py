import json
import tempfile
import unittest
from pathlib import Path
from src.compound_intelligence.demo import CANDIDATES, evaluate, read_records, run


class DemoTests(unittest.TestCase):
    def test_validator_accepts_supported_candidate(self):
        self.assertEqual(evaluate(CANDIDATES[0])["status"], "VERIFIED")

    def test_challenger_rejects_false_expectation(self):
        self.assertEqual(evaluate(CANDIDATES[1])["status"], "REJECTED")

    def test_append_only_idempotence(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            first = run(workspace)
            first_bytes = (workspace / "evidence.jsonl").read_bytes()
            second = run(workspace)
            self.assertEqual(first["new_experiments"], 3)
            self.assertEqual(second["new_experiments"], 0)
            self.assertEqual(first_bytes, (workspace / "evidence.jsonl").read_bytes())
            self.assertEqual(len(read_records(workspace / "evidence.jsonl")), 3)

    def test_bounded_iterations(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(run(Path(tmp), 1)["new_experiments"], 1)

    def test_no_negative_iterations(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                run(Path(tmp), -1)


if __name__ == "__main__":
    unittest.main()
