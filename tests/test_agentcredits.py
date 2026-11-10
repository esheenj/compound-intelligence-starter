"""Original accounting tests: replay, double charge and negative limits."""
import copy
import json
import subprocess
import sys
import unittest

from src.compound_intelligence.agentcredits import fictional_journal, replay


class AgentCreditsTests(unittest.TestCase):
    def test_demo_and_idempotent_replay(self):
        journal = fictional_journal()
        first = replay(journal)
        self.assertTrue(first["valid"])
        self.assertEqual(first["duplicates_ignored"], 1)
        self.assertEqual(first["events_applied"], 4)
        self.assertEqual(first["accounts"]["demo-team"], {"available": 80, "held": 0, "spent": 20})
        self.assertEqual(first, replay(journal))

    def test_conflicting_replay_rejected(self):
        journal = fictional_journal()
        journal["events"][2]["amount"] = 41
        self.assertIn("conflicting duplicate", str(replay(journal)["errors"]))

    def test_insufficient_funds_rejected(self):
        journal = fictional_journal()
        journal["events"][1]["amount"] = 101
        journal["events"][2]["amount"] = 101
        result = replay(journal)
        self.assertFalse(result["valid"])
        self.assertEqual(result["accounts"], {})

    def test_settle_above_reserve_rejected(self):
        journal = fictional_journal()
        journal["events"][3]["amount"] = 41
        self.assertFalse(replay(journal)["valid"])

    def test_refund_above_spent_rejected(self):
        journal = fictional_journal()
        journal["events"][4]["amount"] = 26
        self.assertIn("refund exceeds", str(replay(journal)["errors"]))

    def test_double_settlement_rejected(self):
        journal = fictional_journal()
        journal["events"].append({"event_id": "s2", "account": "demo-team", "op": "settle", "request_id": "demo-run", "amount": 1})
        self.assertFalse(replay(journal)["valid"])

    def test_bool_amount_invalid(self):
        journal = fictional_journal()
        journal["events"][0]["amount"] = True
        self.assertFalse(replay(journal)["valid"])

    def test_cli_demo(self):
        result = subprocess.run(
            [sys.executable, "-m", "src.compound_intelligence.agentcredits", "--demo"],
            capture_output=True, text=True, check=True,
        )
        self.assertEqual(json.loads(result.stdout)["accounts"]["demo-team"]["spent"], 20)


if __name__ == "__main__":
    unittest.main()
