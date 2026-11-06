"""Static report regression: accessibility landmarks, hostile input and no execution."""
import contextlib
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path

from src.compound_intelligence.issue_challenger import plan
from src.compound_intelligence.issue_report import main, render, validate_report


FIXTURE = Path(__file__).resolve().parents[1] / "examples" / "engineering_issues.json"


class IssueReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.proposals = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.input = self.root / "issues.json"
        self.output = self.root / "report.html"
        self.input.write_text(json.dumps(self.proposals), encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def run_cli(self):
        result = io.StringIO()
        with contextlib.redirect_stdout(result):
            exit_code = main(["--input", str(self.input), "--output", str(self.output)])
        return exit_code, json.loads(result.getvalue())

    def test_renders_original_proposals_in_one_command(self):
        status, receipt = self.run_cli()
        self.assertEqual(status, 0)
        self.assertEqual(receipt["state"], "CREATED")
        self.assertEqual(receipt["issues"], 2)
        self.assertFalse(receipt["external_execution"])
        page = self.output.read_text(encoding="utf-8")
        for marker in (
            "<!doctype html>", 'lang="en"', '<main id="main">',
            'href="#main"', 'aria-labelledby="warning"', "<article",
            "Competing explanations", "Cheapest suggested next test",
            "What would disprove it:", "Evidence: NOT VERIFIED",
            "No experiments, code builds, pull requests",
            'script-src &#x27;none&#x27;',
        ):
            # CSP quotes remain literal in the HTML head; asserted separately.
            if marker != "script-src &#x27;none&#x27;":
                self.assertIn(marker, page)
        self.assertIn("script-src 'none'", page)
        self.assertNotIn("<script", page.lower())
        self.assertNotIn("<img", page.lower())
        self.assertNotIn("<iframe", page.lower())
        self.assertNotIn("https://", page)

    def test_accepts_existing_challenger_json_without_modifying_it(self):
        report = plan(self.proposals)
        self.input.write_text(json.dumps(report), encoding="utf-8")
        before = self.input.read_bytes()
        status, result = self.run_cli()
        self.assertEqual(status, 0)
        self.assertEqual(self.input.read_bytes(), before)
        self.assertEqual(result["issues"], 2)
        self.assertEqual(self.output.read_text(encoding="utf-8"), render(report))

    def test_identical_inputs_generate_identical_output(self):
        first = render(plan(self.proposals))
        second = render(plan(json.loads(json.dumps(self.proposals))))
        self.assertEqual(first, second)
        self.assertEqual(len(first.encode("utf-8")) > 0, True)
        self.assertEqual(first.count("<article"), 2)
        self.assertEqual(first.count("<h2 id="), 3)

    def test_html_is_escaped_not_executed(self):
        self.proposals["issues"][0]["title"] = '<script>alert("danger")</script>'
        self.proposals["issues"][0]["hypotheses"][0]["claim"] = '<img src=x onerror=alert(1)>'
        self.proposals["issues"][0]["hypotheses"][0]["test"] = 'Click "confirm" & <iframe>'
        page = render(plan(self.proposals))
        self.assertNotIn('<script>alert', page)
        self.assertNotIn('<img src=', page)
        self.assertNotIn("<iframe>", page)
        self.assertIn("&lt;script&gt;", page)
        self.assertIn("&lt;img src=x onerror=alert(1)&gt;", page)
        self.assertIn("&quot;confirm&quot; &amp; &lt;iframe&gt;", page)
        self.assertIn("No experiments, code builds, pull requests", page)

    def test_refuses_forged_report_claims_and_selection(self):
        original = plan(self.proposals)
        changes = [
            lambda x: x.update({"results_verified": True}),
            lambda x: x.update({"external_execution": True}),
            lambda x: x.update({"release_or_merge_authority": "PUBLISH"}),
            lambda x: x.update({"unknown": 1}),
            lambda x: x["ranked_issues"].reverse(),
            lambda x: x["ranked_issues"][0].update({"build_execution_allowed": True}),
            lambda x: x["ranked_issues"][0].update({"brief_id": "bad"}),
            lambda x: x["ranked_issues"][0].update({"priority_hint": 999}),
            lambda x: x["ranked_issues"][0]["chosen_next_test"].update({"experiment": "unrelated"}),
            lambda x: x["ranked_issues"][0]["competing_hypotheses"][0].update({"estimated_cost_units": 99}),
            lambda x: x["ranked_issues"][0]["competing_hypotheses"][0].update({"additional": "bad"}),
            lambda x: x["ranked_issues"][0]["competing_hypotheses"].pop(),
            lambda x: x["ranked_issues"][0]["competing_hypotheses"].reverse(),
        ]
        for change in changes:
            with self.subTest(change=change):
                item = copy.deepcopy(original)
                change(item)
                with self.assertRaises(ValueError):
                    validate_report(item)

    def test_input_duplicate_json_and_nan_fail_without_output(self):
        for raw in ('{"version":1,"version":1,"issues":[]}', '{"version":NaN,"issues":[]}',
                    '{"schema":"bad"}', '[]'):
            self.input.write_text(raw)
            status, receipt = self.run_cli()
            self.assertEqual(status, 2)
            self.assertEqual(receipt["state"], "REJECTED")
            self.assertFalse(self.output.exists())

    def test_output_no_overwrite_or_symlink_and_missing_parent(self):
        first, receipt = self.run_cli()
        self.assertEqual(first, 0)
        original = self.output.read_bytes()
        second, result = self.run_cli()
        self.assertEqual(second, 2)
        self.assertEqual(result["state"], "REJECTED")
        self.assertEqual(self.output.read_bytes(), original)
        self.output.unlink()
        self.output.symlink_to(self.input)
        status, _ = self.run_cli()
        self.assertEqual(status, 2)
        self.assertTrue(self.output.is_symlink())
        self.assertTrue(self.input.exists())
        self.output.unlink()
        missing_parent = self.root / "missing" / "report.html"
        with contextlib.redirect_stdout(io.StringIO()):
            status = main(["--input", str(self.input), "--output", str(missing_parent)])
        self.assertEqual(status, 2)
        self.assertFalse(missing_parent.exists())

    def test_input_symlink_and_size_limit(self):
        other = self.root / "other.json"
        other.write_text(self.input.read_text())
        self.input.unlink()
        self.input.symlink_to(other)
        self.assertEqual(self.run_cli()[0], 2)
        self.input.unlink()
        self.input.write_bytes(b" " * 131073)
        self.assertEqual(self.run_cli()[0], 2)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
