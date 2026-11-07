"""Offline scenario explorer: validated source, inert output and no overwrite."""
import contextlib
import copy
import hashlib
import io
import json
import re
import tempfile
import unittest
from pathlib import Path

from src.compound_intelligence.issue_challenger import plan
from src.compound_intelligence.issue_explorer import SCRIPT, main, render_explorer

FIXTURE = Path(__file__).resolve().parents[1] / "examples" / "engineering_issues.json"


class ExplorerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.document = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.input = self.root / "issues.json"
        self.output = self.root / "explorer.html"
        self.input.write_text(json.dumps(self.document), encoding="utf-8")

    def run_cli(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = main(["--input", str(self.input), "--output", str(self.output)])
        return code, json.loads(out.getvalue())

    def test_cli_creates_reproducible_explorer_with_actual_challenger_results(self):
        exit_code, receipt = self.run_cli()
        self.assertEqual(exit_code, 0)
        self.assertEqual(receipt["state"], "CREATED")
        self.assertEqual(receipt["issues"], 2)
        self.assertFalse(receipt["external_execution"])
        page = self.output.read_text(encoding="utf-8")
        self.assertEqual(page, render_explorer(plan(self.document)))
        self.assertEqual(hashlib.sha256(page.encode()).hexdigest(), receipt["sha256"])
        for phrase in (
            "One issue. Many explanations", "focus outline blends",
            "A visible and keyboard-accessible reset action",
            "Cheapest proposed first test", "not executed",
            'id="issue-filter"', 'data-issue="keyboard-focus"',
            'data-issue="empty-state"', 'role="status"', 'href="#main"',
            'script-src &#x27;sha256-',
        ):
            if phrase.startswith("script-src"):
                self.assertIn("script-src 'sha256-", page)
            else:
                self.assertIn(phrase, page)
        self.assertIn("The focus outline blends into the background", page)
        self.assertIn("A visible and keyboard-accessible reset action already exists", page)
        self.assertEqual(page.count("<article"), 2)
        self.assertEqual(page.count("<details"), 4)
        self.assertNotIn("http://", page)
        self.assertNotIn("https://", page)
        self.assertNotIn("fetch(", page)
        self.assertNotIn("XMLHttpRequest", page)

    def test_hash_based_csp_matches_exact_fixed_script(self):
        page = render_explorer(plan(self.document))
        import base64
        token = base64.b64encode(hashlib.sha256(SCRIPT.encode()).digest()).decode()
        self.assertIn("script-src 'sha256-" + token + "'", page)
        self.assertIn("<script>" + SCRIPT + "</script>", page)
        self.assertIn("connect-src 'none'", page)
        self.assertIn("form-action 'none'", page)
        self.assertEqual(render_explorer(plan(copy.deepcopy(self.document))), page)

    def test_hostile_text_escaped_into_inert_html_only(self):
        self.document["issues"][0]["title"] = '<img src=x onerror="alert(1)">'
        self.document["issues"][0]["hypotheses"][0]["claim"] = '</script><svg onload="alert(1)">'
        page = render_explorer(plan(self.document))
        self.assertNotIn('<img src=x', page)
        self.assertNotIn('<svg onload=', page)
        self.assertNotIn('</script><svg', page)
        self.assertIn("&lt;img src=x", page)
        self.assertIn("&lt;/script&gt;&lt;svg", page)
        self.assertEqual(page.count("<script>"), 1)
        self.assertEqual(page.count("</script>"), 1)

    def test_refuses_forged_authority_and_inconsistent_briefs(self):
        report = plan(self.document)
        variants = []
        x = copy.deepcopy(report); x["external_execution"] = True; variants.append(x)
        x = copy.deepcopy(report); x["release_or_merge_authority"] = "PUBLISH"; variants.append(x)
        x = copy.deepcopy(report); x["ranked_issues"][0]["build_execution_allowed"] = True; variants.append(x)
        x = copy.deepcopy(report); x["ranked_issues"][0]["chosen_next_test"]["experiment"] = "Unrelated test"; variants.append(x)
        for candidate in variants:
            with self.subTest(candidate=candidate):
                with self.assertRaises(ValueError):
                    render_explorer(candidate)

    def test_rejects_duplicate_keys_oversize_symlinks_and_never_overwrites(self):
        first, receipt = self.run_cli()
        self.assertEqual(first, 0)
        existing = self.output.read_bytes()
        second, rejected = self.run_cli()
        self.assertEqual(second, 2)
        self.assertEqual(rejected["state"], "REJECTED")
        self.assertEqual(existing, self.output.read_bytes())
        self.output.unlink()
        self.input.write_text('{"version":1,"version":1,"issues":[]}', encoding="utf-8")
        self.assertEqual(self.run_cli()[0], 2)
        self.assertFalse(self.output.exists())
        self.input.write_bytes(b" " * 131073)
        self.assertEqual(self.run_cli()[0], 2)
        self.assertFalse(self.output.exists())
        self.input.unlink()
        target = self.root / "other.json"
        target.write_text(json.dumps(self.document))
        self.input.symlink_to(target)
        self.assertEqual(self.run_cli()[0], 2)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
