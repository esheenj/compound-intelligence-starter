"""Simulated review approval and denial; no actual execution permission."""
from __future__ import annotations
import copy
import json
import subprocess
import sys
import unittest

from src.compound_intelligence.agent_review_gate import fictional_events, replay


class AgentReviewGateTests(unittest.TestCase):
    def test_demo_records_claim_without_execution_authority(self):
        r = replay(fictional_events())
        self.assertTrue(r["valid_input"])
        self.assertTrue(r["fully_resolved"])
        self.assertEqual(r["requests"]["demo-request"]["status"], "ACTION_REPORTED")
        self.assertEqual(r["execution_authority"], "NONE")
        self.assertEqual(r["duplicates_ignored"], 1)

    def test_pending_not_authorized_or_resolved(self):
        r = replay(fictional_events("pending"))
        self.assertTrue(r["valid_input"])
        self.assertFalse(r["fully_resolved"])
        self.assertEqual(r["unresolved_request_ids"], ["demo-request"])

    def test_denial_terminal_without_execution(self):
        r = replay(fictional_events("denied"))
        self.assertTrue(r["fully_resolved"])
        self.assertEqual(r["requests"]["demo-request"]["status"], "DENIED")

    def test_restart_same_event_id_never_repeats_action_claim(self):
        journal = fictional_events()
        original = replay(journal)
        journal["events"].extend(copy.deepcopy(journal["events"]))
        replayed = replay(journal)
        self.assertEqual(replayed["events_applied"], original["events_applied"])
        self.assertEqual(replayed["requests"], original["requests"])
        self.assertEqual(replayed["duplicates_ignored"], original["duplicates_ignored"]+4)

    def test_conflicting_duplicate_rejected_atomically(self):
        journal = fictional_events()
        journal["events"][-1]["scope"] = "OTHER_DEMO"
        r = replay(journal)
        self.assertFalse(r["valid_input"])
        self.assertEqual(r["requests"], {})

    def test_requester_cannot_approve_own_request(self):
        journal = fictional_events()
        journal["events"][1]["actor"] = "fictional-requester"
        self.assertFalse(replay(journal)["valid_input"])

    def test_pretend_report_without_approval_rejected(self):
        journal = fictional_events()
        journal["events"][1]["kind"] = "ACTION_REPORTED"
        journal["events"][1].pop("expires_tick")
        self.assertFalse(replay(journal)["valid_input"])

    def test_expired_approval_rejects_action_claim(self):
        journal = fictional_events()
        journal["events"][2]["tick"] = 61
        r = replay(journal)
        self.assertFalse(r["valid_input"])
        self.assertIn("expired", str(r["errors"]))

    def test_changed_scope_rejected(self):
        journal = fictional_events()
        journal["events"][1]["scope"] = "CHANGED"
        self.assertFalse(replay(journal)["valid_input"])

    def test_second_transition_after_denial_rejected(self):
        journal = fictional_events("denied")
        journal["events"].append({"event_id": "r4", "request_id": "demo-request",
                                  "sequence": 3, "actor": "fictional-worker",
                                  "kind": "ACTION_REPORTED", "scope": "LOCAL_DEMO", "tick": 25})
        self.assertFalse(replay(journal)["valid_input"])

    def test_bad_input_and_unhashable_kind_rejected(self):
        self.assertFalse(replay(None)["valid_input"])
        journal = fictional_events()
        journal["events"][0]["kind"] = []
        self.assertFalse(replay(journal)["valid_input"])

    def test_boolean_sequence_and_expiry_rejected(self):
        journal = fictional_events()
        journal["events"][0]["sequence"] = True
        self.assertFalse(replay(journal)["valid_input"])
        journal = fictional_events()
        journal["events"][1]["expires_tick"] = True
        self.assertFalse(replay(journal)["valid_input"])

    def test_cli_exit_codes_and_fixture(self):
        cmd = [sys.executable, "-m", "src.compound_intelligence.agent_review_gate"]
        approved = subprocess.run(cmd+["--demo"], text=True, capture_output=True)
        pending = subprocess.run(cmd+["--pending-demo"], text=True, capture_output=True)
        denied = subprocess.run(cmd+["--denied-demo"], text=True, capture_output=True)
        self.assertEqual(approved.returncode, 0)
        self.assertEqual(pending.returncode, 1)
        self.assertEqual(denied.returncode, 0)
        self.assertEqual(json.loads(approved.stdout)["execution_authority"], "NONE")


if __name__ == "__main__":
    unittest.main()
