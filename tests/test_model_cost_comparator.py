"""Model cost comparison contract: deterministic, replay-safe and fail closed."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from src.compound_intelligence.model_cost_comparator import compare, fixture, render_html


class ModelCostTests(unittest.TestCase):
    def test_decimal_totals_and_budget(self):
        x = compare(fixture())
        self.assertTrue(x["valid_input"])
        self.assertFalse(x["all_within_budget"])
        self.assertEqual(x["duplicates_ignored"], 1)
        self.assertEqual(x["events_applied"], 2)
        costs = {m["model_id"]: m for m in x["models"]}
        self.assertEqual(costs["sample-small"]["estimated_usd"], "0.000380000000")
        self.assertEqual(costs["sample-large"]["estimated_usd"], "0.000460000000")
        self.assertTrue(costs["sample-small"]["within_budget"])
        self.assertFalse(costs["sample-large"]["within_budget"])

    def test_zero_rate_can_admit(self):
        x = fixture()
        for rate in x["rates"]:
            rate["input_usd_per_million"] = "0"
            rate["output_usd_per_million"] = "0"
        self.assertTrue(compare(x)["all_within_budget"])

    def test_restart_replay_idempotence(self):
        x = fixture()
        baseline = compare(x)
        x["events"].extend(copy.deepcopy(x["events"]))
        replay = compare(x)
        self.assertEqual(baseline["models"], replay["models"])
        self.assertEqual(baseline["events_applied"], replay["events_applied"])
        self.assertEqual(replay["duplicates_ignored"], baseline["duplicates_ignored"]+3)

    def test_conflicting_duplicate_rejects_partial_output(self):
        x = fixture()
        x["events"][1]["output_tokens"] = 999
        result = compare(x)
        self.assertFalse(result["valid_input"])
        self.assertEqual(result["models"], [])
        self.assertIn("conflicting duplicate", str(result["errors"]))

    def test_bad_model_references(self):
        x = fixture()
        x["events"][0]["model_id"] = "unknown"
        self.assertFalse(compare(x)["valid_input"])
        x = fixture()
        x["rates"][1]["model_id"] = "sample-small"
        self.assertFalse(compare(x)["valid_input"])

    def test_bad_tokens(self):
        for invalid in [-1, True, 1000000001, [], "1"]:
            x = fixture()
            x["events"][0]["input_tokens"] = invalid
            self.assertFalse(compare(x)["valid_input"])
        x = fixture()
        x["events"][0]["input_tokens"] = 0
        x["events"][0]["output_tokens"] = 0
        self.assertFalse(compare(x)["valid_input"])

    def test_bad_prices(self):
        for invalid in ["NaN", "Infinity", "-1", "1e3", "0.1234567", 0.1, []]:
            x = fixture()
            x["rates"][0]["input_usd_per_million"] = invalid
            self.assertFalse(compare(x)["valid_input"])
        x = fixture()
        x["budget_usd"] = "-1"
        self.assertFalse(compare(x)["valid_input"])

    def test_malformed_nested_and_unknown_fields(self):
        self.assertFalse(compare(None)["valid_input"])
        x = fixture()
        x["events"][0] = []
        self.assertFalse(compare(x)["valid_input"])
        x = fixture()
        x["rates"][0]["extra"] = "untrusted"
        self.assertFalse(compare(x)["valid_input"])

    def test_event_split_does_not_change_total(self):
        a = fixture()
        original = compare(a)
        x = fixture()
        x["events"][0]["input_tokens"] = 600
        x["events"][0]["output_tokens"] = 100
        x["events"][1] = {"event_id": "small-2", "model_id": "sample-small",
                          "input_tokens": 400, "output_tokens": 100}
        self.assertTrue(compare(x)["valid_input"])
        self.assertEqual([z["estimated_usd"] for z in compare(x)["models"]],
                         [z["estimated_usd"] for z in original["models"]])

    def test_html_escape_and_no_scripts(self):
        x = compare(fixture())
        x["price_book_revision"] = "<script>alert(1)</script>"
        page = render_html(x)
        self.assertIn("&lt;script&gt;", page)
        self.assertNotIn("<script>", page)
        self.assertIn("Content-Security-Policy", page)

    def test_cli_reports_and_exit_status(self):
        cmd = [sys.executable, "-m", "src.compound_intelligence.model_cost_comparator"]
        with tempfile.TemporaryDirectory() as work:
            html_path = Path(work) / "quote.html"
            result = subprocess.run(cmd + ["--demo", "--html", str(html_path)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertTrue(html_path.is_file())
            self.assertEqual(json.loads(result.stdout)["events_applied"], 2)
            sample = fixture()
            for rate in sample["rates"]:
                rate["input_usd_per_million"] = "0"
                rate["output_usd_per_million"] = "0"
            source = Path(work) / "input.json"
            source.write_text(json.dumps(sample), encoding="utf-8")
            ok = subprocess.run(cmd + ["--input", str(source)], capture_output=True, text=True)
            self.assertEqual(ok.returncode, 0)
            source.write_text('{"a":1,"a":2}', encoding="utf-8")
            bad = subprocess.run(cmd + ["--input", str(source)], capture_output=True, text=True)
            self.assertEqual(bad.returncode, 2)


if __name__ == "__main__":
    unittest.main()
