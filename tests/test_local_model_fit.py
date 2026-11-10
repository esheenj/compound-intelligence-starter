"""Resource-fit planner tests: boundary cases and invalid user-supplied estimates."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from src.compound_intelligence.local_model_fit import evaluate, fixture, render_html


class LocalModelFitTests(unittest.TestCase):
    def test_demo_distinguishes_fit_from_nonfit(self):
        result = evaluate(fixture())
        self.assertTrue(result["valid_input"])
        self.assertTrue(result["any_candidate_fits"])
        by_id = {c["model_id"]: c for c in result["candidates"]}
        self.assertTrue(by_id["fictional-small-q4"]["meets_supplied_limits"])
        self.assertEqual(by_id["fictional-small-q4"]["estimated_ram_headroom_mib"], 810)
        self.assertFalse(by_id["fictional-large-q4"]["meets_supplied_limits"])
        self.assertEqual(len(by_id["fictional-large-q4"]["reasons"]), 2)

    def test_constrained_device_admits_none(self):
        result = evaluate(fixture(constrained=True))
        self.assertTrue(result["valid_input"])
        self.assertFalse(result["any_candidate_fits"])
        self.assertEqual(len(result["candidates"]), 2)

    def test_exact_ram_storage_and_context_boundaries_fit(self):
        sample = fixture()
        sample["models"] = [
            {"model_id": "exact-model", "file_mib": 2048,
             "estimated_runtime_ram_mib": 2560, "context_capacity_tokens": 4096}
        ]
        result = evaluate(sample)
        self.assertTrue(result["any_candidate_fits"])
        self.assertEqual(result["candidates"][0]["estimated_ram_headroom_mib"], 0)
        self.assertEqual(result["candidates"][0]["storage_headroom_mib"], 0)
        self.assertEqual(result["candidates"][0]["context_headroom_tokens"], 0)

    def test_context_limit_is_independent(self):
        sample = fixture()
        sample["models"][0]["context_capacity_tokens"] = 2048
        result = evaluate(sample)
        self.assertFalse(result["any_candidate_fits"])
        self.assertIn("context_capacity_below_requirement",
                      next(x for x in result["candidates"] if x["model_id"] == "fictional-small-q4")["reasons"])

    def test_negative_boolean_and_zero_values_fail_closed(self):
        for value in [-1, True, [], "1000", 1000001]:
            sample = fixture()
            sample["device"]["ram_mib"] = value
            self.assertFalse(evaluate(sample)["valid_input"])
        sample = fixture()
        sample["models"][0]["file_mib"] = 0
        self.assertFalse(evaluate(sample)["valid_input"])

    def test_no_ram_after_reservation_is_invalid(self):
        sample = fixture()
        sample["device"]["reserved_ram_mib"] = sample["device"]["ram_mib"]
        self.assertFalse(evaluate(sample)["valid_input"])

    def test_duplicate_models_and_unknown_fields_rejected(self):
        sample = fixture()
        sample["models"][1]["model_id"] = sample["models"][0]["model_id"]
        self.assertFalse(evaluate(sample)["valid_input"])
        sample = fixture()
        sample["models"][0]["secret"] = "should reject unknown fields"
        self.assertFalse(evaluate(sample)["valid_input"])

    def test_malformed_input_returns_no_partial_candidate_info(self):
        for sample in [None, {"schema":"bad", "device":{}, "models":[]}, []]:
            result = evaluate(sample)
            self.assertFalse(result["valid_input"])
            self.assertEqual(result["candidates"], [])
        sample = fixture()
        sample["models"][1] = []
        result = evaluate(sample)
        self.assertFalse(result["valid_input"])
        self.assertEqual(result["candidates"], [])

    def test_deterministic_reordering(self):
        sample = fixture()
        original = evaluate(sample)
        sample["models"].reverse()
        result = evaluate(sample)
        self.assertEqual(result["candidates"], original["candidates"])

    def test_script_free_html_escapes_output(self):
        result = evaluate(fixture())
        result["candidates"][0]["model_id"] = "<script>alert(1)</script>"
        page = render_html(result)
        self.assertIn("&lt;script&gt;", page)
        self.assertNotIn("<script>", page)
        self.assertIn("Content-Security-Policy", page)

    def test_cli_exit_codes_and_local_html(self):
        cmd = [sys.executable, "-m", "src.compound_intelligence.local_model_fit"]
        with tempfile.TemporaryDirectory() as root:
            out = Path(root) / "fit.html"
            okay = subprocess.run(cmd+["--demo", "--html", str(out)], capture_output=True, text=True)
            badfit = subprocess.run(cmd+["--constrained-demo"], capture_output=True, text=True)
            self.assertEqual(okay.returncode, 0)
            self.assertEqual(badfit.returncode, 1)
            self.assertTrue(out.is_file())
            self.assertEqual(json.loads(okay.stdout)["candidates"][0]["model_id"], "fictional-small-q4")
            p = Path(root) / "bad.json"
            p.write_text('{"schema":"x","schema":"y","models":[]}', encoding="utf-8")
            invalid = subprocess.run(cmd+["--input", str(p)], capture_output=True, text=True)
            self.assertEqual(invalid.returncode, 2)

    def test_scope_never_asserts_measured_performance(self):
        result = evaluate(fixture())
        self.assertIn("no model loading", result["scope"])


if __name__ == "__main__":
    unittest.main()
