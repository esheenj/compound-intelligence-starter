"""Deterministic regression and hostile-input checks for public issue challenger."""
import contextlib
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path

from src.compound_intelligence.issue_challenger import main, plan, validate


def demo():
    return {
        "version": 1,
        "issues": [
            {"id": "keyboard-focus", "title": "Synthetic keyboard focus has weak visibility",
             "impact": 5, "effort": 2, "risk": 1, "hypotheses": [
                {"id": "contrast", "claim": "Focus outline lacks contrast",
                 "test": "Compare outline with adjacent surface", "counterexample": "Contrast is sufficient",
                 "cost": 1},
                {"id": "clipping", "claim": "Container clips the outline",
                 "test": "Disable overflow clipping on synthetic view",
                 "counterexample": "Outline remains invisible", "cost": 2},
             ]},
            {"id": "empty-state", "title": "Fictional empty state has confusing reset",
             "impact": 3, "effort": 1, "risk": 1, "hypotheses": [
                 {"id": "labels", "claim": "A reset label is missing",
                  "test": "Inspect synthetic empty-state instructions",
                  "counterexample": "Instructions clearly explain reset", "cost": 1},
                 {"id": "filter", "claim": "Search filter is stale",
                  "test": "Clear the query and inspect filters",
                  "counterexample": "Filter state is empty", "cost": 2},
             ]},
        ],
    }


class IssueChallengerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.file = self.root / "fixture.json"
        self.data = demo()
        self.file.write_text(json.dumps(self.data))

    def tearDown(self):
        self.temp.cleanup()

    def invoke(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            status = main(["--input", str(self.file)])
        return status, json.loads(out.getvalue())

    def test_fixture_ranking_and_falsifiable_experiment(self):
        output = plan(self.data)
        self.assertEqual(output["schema"], "compound-engineering-challenger-v1")
        self.assertEqual([x["issue_id"] for x in output["ranked_issues"]],
                         ["keyboard-focus", "empty-state"])
        first = output["ranked_issues"][0]
        self.assertEqual(first["priority_hint"], 14)
        self.assertEqual(first["chosen_next_test"]["hypothesis_id"], "contrast")
        self.assertEqual(first["chosen_next_test"]["falsifying_observation"],
                         "Contrast is sufficient")
        self.assertEqual(len(first["competing_hypotheses"]), 2)
        self.assertFalse(first["build_execution_allowed"])
        self.assertEqual(first["source_evidence_status"], "NOT_VERIFIED")
        self.assertFalse(output["results_verified"])
        self.assertFalse(output["external_execution"])
        self.assertEqual(output["release_or_merge_authority"], "NONE")

    def test_stable_duplicated_invocation_and_changed_input_digest(self):
        first = plan(self.data)
        self.assertEqual(first, plan(copy.deepcopy(self.data)))
        self.assertEqual(self.invoke(), (0, first))
        modified = copy.deepcopy(self.data)
        modified["issues"][0]["hypotheses"][0]["test"] += " in dark theme"
        second = plan(modified)
        self.assertNotEqual(first["ranked_issues"][0]["input_sha256"],
                            second["ranked_issues"][0]["input_sha256"])
        self.assertEqual(first["ranked_issues"][1]["input_sha256"],
                         second["ranked_issues"][1]["input_sha256"])
        self.assertTrue(all(len(x["brief_id"]) == 24 for x in second["ranked_issues"]))

    def test_tie_breaks_are_stable_independent_of_issue_order(self):
        d = copy.deepcopy(self.data)
        for issue in d["issues"]:
            issue["impact"], issue["effort"], issue["risk"] = 2, 2, 2
            issue["hypotheses"][0]["cost"] = issue["hypotheses"][1]["cost"] = 1
        a = plan(d)
        d["issues"].reverse()
        b = plan(d)
        self.assertEqual(a, b)
        self.assertEqual([x["issue_id"] for x in a["ranked_issues"]],
                         ["empty-state", "keyboard-focus"])
        self.assertEqual(a["ranked_issues"][1]["chosen_next_test"]["hypothesis_id"],
                         "clipping")

    def test_reject_malformed_schemas_and_unfalsifiable_issues(self):
        variants = []
        x = copy.deepcopy(self.data); x["extra"] = True; variants.append(x)
        x = copy.deepcopy(self.data); x["version"] = True; variants.append(x)
        x = copy.deepcopy(self.data); x["issues"] = []; variants.append(x)
        x = copy.deepcopy(self.data); x["issues"].append(x["issues"][0]); variants.append(x)
        x = copy.deepcopy(self.data); x["issues"][0]["impact"] = True; variants.append(x)
        x = copy.deepcopy(self.data); x["issues"][0]["risk"] = -1; variants.append(x)
        x = copy.deepcopy(self.data); x["issues"][0]["hypotheses"].pop(); variants.append(x)
        x = copy.deepcopy(self.data); x["issues"][0]["hypotheses"][0]["id"] = "bad id"; variants.append(x)
        x = copy.deepcopy(self.data); x["issues"][0]["hypotheses"][0]["cost"] = 6; variants.append(x)
        x = copy.deepcopy(self.data); x["issues"][0]["hypotheses"][1]["id"] = "contrast"; variants.append(x)
        x = copy.deepcopy(self.data); x["issues"][0]["hypotheses"][0]["extra"] = "x"; variants.append(x)
        x = copy.deepcopy(self.data); x["issues"][0]["hypotheses"][0]["test"] = (
            x["issues"][0]["hypotheses"][0]["counterexample"]); variants.append(x)
        x = copy.deepcopy(self.data); x["issues"][0]["title"] = "Title\nInjection"; variants.append(x)
        x = copy.deepcopy(self.data); x["issues"][0]["title"] = "-----BEGIN PRIVATE KEY-----"; variants.append(x)
        for item in variants:
            with self.subTest(item=item):
                with self.assertRaises(ValueError):
                    validate(item)

    def test_reject_duplicate_json_keys_nan_and_oversize_without_details(self):
        for raw in ('{"version":1,"version":1,"issues":[]}',
                    '{"version":NaN,"issues":[]}', "["):
            self.file.write_text(raw)
            status, result = self.invoke()
            self.assertEqual(status, 2)
            self.assertEqual(result["state"], "REJECTED")
            self.assertNotIn(raw[:8], json.dumps(result))
        self.file.write_bytes(b" " * 65537)
        self.assertEqual(self.invoke()[0], 2)

    def test_no_implicit_files_network_or_code_execution(self):
        self.assertEqual(list(self.root.iterdir()), [self.file])
        status, report = self.invoke()
        self.assertEqual(status, 0)
        self.assertFalse(report["github_writes"])
        self.assertFalse(report["financial_or_trading_logic"])
        self.assertEqual(list(self.root.iterdir()), [self.file])

    def test_reject_missing_file_and_symlink(self):
        self.file.unlink()
        status, data = self.invoke()
        self.assertEqual(status, 2)
        self.assertEqual(data["state"], "REJECTED")
        self.file.symlink_to(self.root / "does-not-exist")
        self.assertEqual(self.invoke()[0], 2)


if __name__ == "__main__":
    unittest.main()
