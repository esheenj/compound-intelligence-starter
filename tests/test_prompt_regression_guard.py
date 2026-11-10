"""Independent synthetic critical-case regression checks."""
import copy
import json
import subprocess
import sys
import unittest

from src.compound_intelligence.prompt_regression_guard import compare, fictional_cases


class RegressionGuardTests(unittest.TestCase):
    def test_green_baseline(self):
        x = compare(fictional_cases())
        self.assertTrue(x["valid_input"])
        self.assertTrue(x["gate_passed"])
        self.assertEqual(x["critical_regressions"], [])

    def test_aggregate_gain_cannot_hide_critical_drop(self):
        x = compare(fictional_cases(with_regression=True))
        self.assertFalse(x["gate_passed"])
        self.assertGreater(x["candidate_average"], x["baseline_average"])
        self.assertEqual(x["critical_regressions"][0]["case_id"], "important-safety-case")

    def test_forged_critical_flag_rejected(self):
        item = fictional_cases()
        item["candidate"][0]["critical"] = False
        self.assertFalse(compare(item)["valid_input"])

    def test_missing_or_duplicate_case_rejected(self):
        item = fictional_cases()
        item["candidate"].pop()
        self.assertFalse(compare(item)["valid_input"])
        item = fictional_cases()
        item["candidate"].append(copy.deepcopy(item["candidate"][0]))
        self.assertFalse(compare(item)["valid_input"])

    def test_bool_score_rejected(self):
        item = fictional_cases()
        item["baseline"][0]["score"] = True
        self.assertFalse(compare(item)["valid_input"])

    def test_malformed_nested_data_rejected(self):
        item = fictional_cases()
        item["baseline"][0] = []
        self.assertFalse(compare(item)["valid_input"])

    def test_exit_codes_and_replay(self):
        cmd = [sys.executable, "-m", "src.compound_intelligence.prompt_regression_guard"]
        okay = subprocess.run(cmd + ["--demo"], capture_output=True, text=True)
        fail = subprocess.run(cmd + ["--regression-demo"], capture_output=True, text=True)
        self.assertEqual(okay.returncode, 0)
        self.assertEqual(fail.returncode, 1)
        self.assertTrue(json.loads(okay.stdout)["gate_passed"])
        self.assertFalse(json.loads(fail.stdout)["gate_passed"])


if __name__ == "__main__":
    unittest.main()
