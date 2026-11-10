"""Literal quote evidence checks with entirely invented local excerpts."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from src.compound_intelligence.claim_evidence_map import (
    fictional_claims, inspect_claims,
)


class ClaimEvidenceTests(unittest.TestCase):
    def test_demo_matches_only_supplied_literal_quotes(self):
        original = fictional_claims()
        unchanged = copy.deepcopy(original)
        result = inspect_claims(original)
        self.assertTrue(result["valid_input"])
        self.assertTrue(result["all_literal_citations_found"])
        self.assertEqual(result["claims_checked"], 2)
        self.assertEqual(result["unresolved_claims"], 0)
        self.assertEqual([row["status"] for row in result["results"]],
                         ["ALL_QUOTES_FOUND_LITERAL_ONLY"] * 2)
        self.assertEqual(original, unchanged)
        self.assertIn("No truth", result["scope"])

    def test_mismatch_gap_is_visible_without_false_factual_claims(self):
        result = inspect_claims(fictional_claims(missing=True))
        self.assertTrue(result["valid_input"])
        self.assertFalse(result["all_literal_citations_found"])
        self.assertEqual(result["unresolved_claims"], 1)
        self.assertEqual(result["results"][1]["status"], "QUOTE_NOT_FOUND_IN_ALL_CITED_SOURCES")

    def test_unquoted_unreferenced_and_unknown_sources(self):
        fixture = fictional_claims()
        fixture["claims"][0]["quote"] = ""
        fixture["claims"][1]["cited_source_ids"] = []
        result = inspect_claims(fixture)
        self.assertEqual([x["status"] for x in result["results"]],
                         ["NO_TESTABLE_QUOTE", "NO_CITATION"])
        fixture["claims"][0]["cited_source_ids"] = ["missing-source"]
        self.assertEqual(inspect_claims(fixture)["results"][0]["status"], "SOURCE_NOT_SUPPLIED")

    def test_multiple_citations_dont_hide_a_mismatch(self):
        fixture = fictional_claims()
        fixture["claims"][0]["cited_source_ids"] = ["fictional-note", "fictional-receipt"]
        result = inspect_claims(fixture)
        row = result["results"][0]
        self.assertEqual(row["matched_source_ids"], ["fictional-note"])
        self.assertEqual(row["unmatched_source_ids"], ["fictional-receipt"])
        self.assertEqual(row["status"], "QUOTE_NOT_FOUND_IN_ALL_CITED_SOURCES")

    def test_input_rejection_fails_closed_with_no_partial_results(self):
        source = fictional_claims()
        for doc in [
            None, {}, {"schema": source["schema"], "claims": [], "sources": []},
            {"schema": source["schema"], "claims": source["claims"], "sources": []},
        ]:
            self.assertFalse(inspect_claims(doc)["valid_input"])
        invalid_sources = [
            {**source["sources"][0], "source_id": ""},
            {**source["sources"][0], "excerpt": ""},
            {**source["sources"][0], "excerpt": 42},
            {**source["sources"][0], "private": "ineligible"},
            source["sources"][0],
        ]
        for bad_source in invalid_sources:
            fixture = fictional_claims()
            fixture["sources"][1] = bad_source
            result = inspect_claims(fixture)
            self.assertFalse(result["valid_input"])
            self.assertEqual(result["results"], [])
        invalid_claims = [
            {**source["claims"][0], "claim_id": "../escape"},
            {**source["claims"][0], "quote": 42},
            {**source["claims"][0], "cited_source_ids": [True]},
            {**source["claims"][0], "cited_source_ids": ["fictional-note"] * 2},
            {**source["claims"][0], "extra_field": "secret"},
            source["claims"][0],
        ]
        for bad_claim in invalid_claims:
            fixture = fictional_claims()
            fixture["claims"][1] = bad_claim
            result = inspect_claims(fixture)
            self.assertFalse(result["valid_input"])
            self.assertEqual(result["results"], [])

    def test_hostile_excerpt_is_treated_as_literal_input_not_rendered_markup(self):
        fixture = fictional_claims()
        fixture["sources"][0]["excerpt"] = '<img src=x onerror=alert(1)>'
        fixture["claims"][0]["quote"] = "onerror=alert(1)"
        report = inspect_claims(fixture)
        self.assertEqual(report["results"][0]["status"], "ALL_QUOTES_FOUND_LITERAL_ONLY")
        self.assertNotIn("<img", json.dumps(report))
        self.assertNotIn("onerror=", json.dumps(report))

    def test_cli_demo_gap_duplicate_json_and_oversized_input(self):
        base = [sys.executable, "-m", "src.compound_intelligence.claim_evidence_map"]
        for arg, exit_code in (("--demo", 0), ("--gap-demo", 1)):
            run = subprocess.run(base + [arg], capture_output=True, text=True)
            self.assertEqual(run.returncode, exit_code, run.stderr)
            self.assertEqual(json.loads(run.stdout)["valid_input"], True)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fictional.json"
            path.write_text('{"schema":"x","schema":"y","sources":[],"claims":[]}', encoding="utf-8")
            duplicate = subprocess.run(base + ["--input", str(path)], capture_output=True, text=True)
            self.assertEqual(duplicate.returncode, 2)
            self.assertFalse(json.loads(duplicate.stdout)["valid_input"])
            path.write_bytes(b" " * 256_001)
            huge = subprocess.run(base + ["--input", str(path)], capture_output=True, text=True)
            self.assertEqual(huge.returncode, 2)
            self.assertNotIn(str(path), huge.stdout)


if __name__ == "__main__":
    unittest.main()
