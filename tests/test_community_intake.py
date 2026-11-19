import contextlib
import io
import urllib.error
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.compound_intelligence.community_intake import (
    EXPANDED_PUBLIC_REPOS, PUBLIC_REPOS, fetch_public_issues, main, report, summarize,
)


def issue(number=7, body="A synthetic report"):
    return {"number": number, "title": "Synthetic edge case",
            "body": body, "updated_at": "2026-11-06T09:00:00Z"}


class FeedbackTests(unittest.TestCase):
    def test_seven_public_repositories_and_redacted_full_inventory(self):
        expected = {
            "esheenj/compound-intelligence-starter",
            "esheenj/design-system-foundations-oss",
            "esheenj/mobile-first-flow-kit-oss",
            "esheenj/data-table-interactions-oss",
            "esheenj/flow-state-machine-oss",
            "esheenj/form-experience-kit-oss",
            "esheenj/visual-regression-starter-oss",
        }
        self.assertEqual(set(PUBLIC_REPOS), expected)
        all_issues = {repo: [issue(number=i+1)] for i, repo in enumerate(PUBLIC_REPOS)}
        observed = report(all_issues)
        self.assertEqual(len(observed["records"]), 7)
        self.assertEqual(sum(x["count"] for x in observed["records"]), 7)
        self.assertTrue(all(r["interpretation"] == "NONE" and
                            not r["safe_to_execute"] for r in observed["records"]))
        self.assertNotIn("Synthetic edge case", json.dumps(observed))

    def test_report_hides_body_and_preserves_source_digest(self):
        out = report({PUBLIC_REPOS[0]: [issue()]})
        self.assertTrue(out["contents_redacted"])
        self.assertFalse(out["intelligence_validated"])
        record = out["records"][0]["issues"][0]
        self.assertEqual(record["number"], 7)
        self.assertEqual(record["source"], f"https://github.com/{PUBLIC_REPOS[0]}/issues/7")
        self.assertEqual(len(record["content_digest"]), 64)
        self.assertNotIn("Synthetic edge case", json.dumps(out))
        self.assertNotIn("A synthetic report", json.dumps(out))
        self.assertFalse(record["safe_to_execute"] if "safe_to_execute" in record
                         else out["records"][0]["safe_to_execute"])

    def test_pr_is_excluded_and_duplicate_numbers_rejected(self):
        pr = {"number": 11, "pull_request": {"url": "ignored"}}
        self.assertEqual(summarize(PUBLIC_REPOS[0], [pr, issue()])["count"], 1)
        with self.assertRaises(ValueError):
            summarize(PUBLIC_REPOS[0], [issue(), issue()])

    def test_invalid_or_private_sources_rejected(self):
        with self.assertRaises(ValueError):
            report({"esheenj/agent-job-runner": [issue()]})
        with self.assertRaises(ValueError):
            fetch_public_issues("esheenj/private-project")
        with self.assertRaises(ValueError):
            summarize(PUBLIC_REPOS[0], [issue(body="x" * 100001)])
        bad = issue()
        bad["updated_at"] = "tomorrow"
        with self.assertRaises(ValueError):
            summarize(PUBLIC_REPOS[0], [bad])

    def test_expanded_fixture_is_complete_redacted_and_offline(self):
        extra = {
            "esheenj/agent-capability-policy-lab",
            "esheenj/prompt-evaluation-harness-oss",
            "esheenj/eval-dataset-leakage-lab",
            "esheenj/rag-retrieval-eval-lab",
        }
        expected = set(PUBLIC_REPOS) | extra
        self.assertEqual(set(EXPANDED_PUBLIC_REPOS), expected)
        payload = {repo: [issue()] for repo in expected}
        expanded = report(payload, expanded_fixture=True)
        self.assertEqual(len(expanded["records"]), 11)
        self.assertEqual({row["repository"] for row in expanded["records"]}, expected)
        self.assertNotIn("A synthetic report", json.dumps(expanded))
        missing = dict(payload)
        missing.pop(next(iter(extra)))
        for bad, mode in ((payload, False), (missing, True),
                          ({**missing, "esheenj/unknown-example": [issue()]}, True)):
            with self.assertRaises(ValueError):
                report(bad, expanded_fixture=mode)
        with tempfile.TemporaryDirectory() as tmp:
            src, target = Path(tmp) / "fixture.json", Path(tmp) / "report.json"
            src.write_text(json.dumps(payload), encoding="utf-8")
            with patch("src.compound_intelligence.community_intake.fetch_public_issues",
                       side_effect=AssertionError("network used")):
                self.assertEqual(main(["--fixture", str(src), "--expanded-fixture",
                                       "--output", str(target)]), 0)
                self.assertEqual(json.loads(target.read_bytes()), expanded)
                self.assertEqual(main(["--live", "--expanded-fixture",
                                       "--output", str(target)]), 2)
                self.assertEqual(json.loads(target.read_bytes()), expanded)

    def test_http_failure_diagnostics_are_redacted_and_do_not_write_partial_inventory(self):
        cases = [(429, {}, "RATE_LIMITED"),
                 (403, {"X-RateLimit-Remaining": "0"}, "RATE_LIMITED"),
                 (403, {}, "HTTP_REQUEST_REJECTED"),
                 (404, {}, "HTTP_REQUEST_REJECTED")]
        for status, headers, reason in cases:
            with self.subTest(status=status, headers=headers), tempfile.TemporaryDirectory() as tmp:
                target = Path(tmp) / "report.json"
                target.write_text("previous evidence", encoding="utf-8")
                failure = urllib.error.HTTPError(
                    "https://example.invalid/private-token", status, "sensitive message",
                    headers, io.BytesIO(b"private response body"))
                captured = io.StringIO()
                with patch("src.compound_intelligence.community_intake.fetch_public_issues",
                           side_effect=[[], failure]), contextlib.redirect_stdout(captured):
                    self.assertEqual(main(["--live", "--output", str(target)]), 2)
                self.assertEqual(json.loads(captured.getvalue()),
                    {"state": "FAILED", "error_type": "HTTPError", "http_status": status,
                     "reason": reason, "partial_inventory_written": False})
                self.assertEqual(target.read_text(), "previous evidence")

    def test_fixture_cli_reproducible_and_offline(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "source.json"
            target = Path(tmp) / "report.json"
            src.write_text(json.dumps({PUBLIC_REPOS[0]: [issue()]}), encoding="utf-8")
            with patch("src.compound_intelligence.community_intake.fetch_public_issues",
                       side_effect=AssertionError("network used")):
                self.assertEqual(main(["--fixture", str(src), "--output", str(target)]), 0)
            first = target.read_bytes()
            self.assertEqual(main(["--fixture", str(src), "--output", str(target)]), 0)
            self.assertEqual(target.read_bytes(), first)
            self.assertFalse(json.loads(first)["automated_code_changes"])


if __name__ == "__main__":
    unittest.main()
