"""Synthetic budget hard-fail, duplicate and input abuse tests."""
import copy
import json
import subprocess
import sys
import unittest

from src.compound_intelligence.agent_budget_guard import assess, fictional_events


class AgentBudgetGuardTests(unittest.TestCase):
    def test_fictional_budget_and_replay(self):
        journal = fictional_events()
        r = assess(journal)
        self.assertTrue(r["admitted"])
        self.assertEqual(r["spent_by_agent"], {"fictional-agent": 60})
        self.assertEqual(r["duplicates_ignored"], 1)
        self.assertEqual(r["events_applied"], 2)
        self.assertEqual(r, assess(journal))

    def test_overrun_is_not_admitted(self):
        r = assess(fictional_events(overrun=True))
        self.assertTrue(r["valid_input"])
        self.assertFalse(r["admitted"])
        self.assertEqual(r["spent_by_agent"], {})
        self.assertIn("cap exceeded", str(r["errors"]))

    def test_duplicate_id_conflict_rejected(self):
        x = fictional_events()
        x["events"][2]["credits"] = 36
        self.assertFalse(assess(x)["admitted"])
        self.assertFalse(assess(x)["valid_input"])

    def test_bad_amount_and_boolean_limit_rejected(self):
        x = fictional_events()
        x["events"][0]["credits"] = -1
        self.assertFalse(assess(x)["valid_input"])
        x = fictional_events()
        x["limits"]["fictional-agent"] = True
        self.assertFalse(assess(x)["valid_input"])

    def test_unknown_agent_rejected(self):
        x = fictional_events()
        x["events"][1]["agent_id"] = "another-agent"
        self.assertFalse(assess(x)["valid_input"])

    def test_unhashable_agent_rejected(self):
        x = fictional_events()
        x["events"][1]["agent_id"] = []
        self.assertFalse(assess(x)["valid_input"])

    def test_exit_codes(self):
        cmd = [sys.executable, "-m", "src.compound_intelligence.agent_budget_guard"]
        yes = subprocess.run(cmd + ["--demo"], capture_output=True, text=True)
        no = subprocess.run(cmd + ["--overrun-demo"], capture_output=True, text=True)
        self.assertEqual(yes.returncode, 0)
        self.assertEqual(no.returncode, 1)
        self.assertFalse(json.loads(no.stdout)["admitted"])


if __name__ == "__main__":
    unittest.main()
