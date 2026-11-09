"""Deterministic unit and invalid-input tests for the public MVP wave planner."""
import contextlib
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path

from src.compound_intelligence.mvp_portfolio import load, main, plan


def fixture():
    def entry(name, status, value, effort, risk, rights, tests):
        return {"id": name, "status": status, "value": value, "effort": effort,
                "risk": risk, "rights_reviewed": rights, "tests_verified": tests}
    return {"version": 1, "max_active": 2, "candidates": [
        entry("fictional-brochure", "scaffold", 5, 1, 0, False, False),
        entry("fictional-dashboard", "implemented", 4, 2, 1, True, True),
        entry("fictional-form", "pages_deployed", 2, 1, 1, True, True),
        entry("fictional-table", "browser_verified", 5, 1, 0, True, True),
    ]}


class MVPWaveTests(unittest.TestCase):
    def test_bounded_selection_and_review_only(self):
        out = plan(fixture())
        self.assertEqual(out["candidate_count"], 4)
        self.assertEqual(out["active_review_candidates"],
                         ["fictional-form", "fictional-dashboard"])
        self.assertFalse(out["external_execution"])
        self.assertFalse(out["results_verified"])
        self.assertEqual(out["publication_authority"], "NONE")
        self.assertTrue(all(not item["release_authorized"] and
                            not item["execution_authorized"] for item in out["candidates"]))
        self.assertIn("INDEPENDENT_BROWSER_VERIFICATION_MISSING",
                      next(item for item in out["candidates"] if item["id"] == "fictional-form")["unverified_gates"])

    def test_stable_plan_and_input_digest(self):
        data = fixture()
        self.assertEqual(plan(data), plan(copy.deepcopy(data)))
        changed = copy.deepcopy(data)
        changed["candidates"][0]["risk"] = 1
        self.assertNotEqual(plan(data)["input_sha256"], plan(changed)["input_sha256"])

    def test_rejects_bad_schema_duplicates_and_scores(self):
        bad = []
        duplicate = fixture()
        duplicate["candidates"][1]["id"] = duplicate["candidates"][0]["id"]
        bad.append(duplicate)
        extra = fixture()
        extra["candidates"][0]["private_key"] = "should-not-appear"
        bad.append(extra)
        for field, value in [("value", True), ("effort", -1), ("risk", 7)]:
            copy_data = fixture()
            copy_data["candidates"][0][field] = value
            bad.append(copy_data)
        stage = fixture()
        stage["candidates"][0]["status"] = "fully_verified"
        bad.append(stage)
        flag = fixture()
        flag["candidates"][0]["rights_reviewed"] = "true"
        bad.append(flag)
        limit = fixture()
        limit["max_active"] = 4
        bad.append(limit)
        for data in bad:
            with self.subTest(data=data):
                with self.assertRaises(ValueError):
                    plan(data)

    def test_cli_rejects_invalid_file_without_leaking_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.json"
            path.write_text(json.dumps(fixture()), encoding="utf-8")
            result = io.StringIO()
            with contextlib.redirect_stdout(result):
                status = main(["--input", str(path)])
            self.assertEqual(status, 0)
            self.assertEqual(json.loads(result.getvalue()), plan(load(path)))
            path.write_text('{"sensitive": "do-not-print"', encoding="utf-8")
            with contextlib.redirect_stdout(result := io.StringIO()):
                status = main(["--input", str(path)])
            self.assertEqual(status, 2)
            self.assertNotIn("do-not-print", result.getvalue())
            link = Path(tmp) / "alias.json"
            link.symlink_to(path)
            with self.assertRaises(ValueError):
                load(link)

    def test_large_file_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "huge.json"
            path.write_text("x" * 65537)
            with self.assertRaises(ValueError):
                load(path)


if __name__ == "__main__":
    unittest.main()
