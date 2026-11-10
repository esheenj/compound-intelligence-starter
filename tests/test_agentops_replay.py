"""Positive, adversarial and restart tests for original public AgentOps replay."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from src.compound_intelligence.agentops_replay import fictional_journal, html_report, replay


class AgentOpsReplayTests(unittest.TestCase):
    def test_demo_deduplicates_and_reconciles(self):
        result = replay(fictional_journal())
        self.assertTrue(result["valid_input"])
        self.assertTrue(result["fully_reconciled"])
        self.assertEqual(result["events_applied"], 3)
        self.assertEqual(result["duplicates_ignored"], 1)
        self.assertEqual(result["units_by_agent"], {"sample-agent": 7})
        self.assertEqual(result["runs"]["fictional-task"]["status"], "COMPLETED")

    def test_restart_replaying_same_receipts_has_no_additional_charge(self):
        original = fictional_journal()
        reissued = copy.deepcopy(original)
        reissued["events"].extend(copy.deepcopy(original["events"]))
        expected = replay(original)
        actual = replay(reissued)
        self.assertTrue(actual["fully_reconciled"])
        self.assertEqual(actual["units_by_agent"], expected["units_by_agent"])
        self.assertEqual(actual["events_applied"], expected["events_applied"])
        self.assertEqual(actual["duplicates_ignored"], expected["duplicates_ignored"] + len(original["events"]))

    def test_truncated_run_not_promoted_to_completed(self):
        result = replay(fictional_journal(truncated=True))
        self.assertTrue(result["valid_input"])
        self.assertFalse(result["fully_reconciled"])
        self.assertEqual(result["incomplete_run_ids"], ["fictional-task"])
        self.assertEqual(result["runs"]["fictional-task"]["status"], "INCOMPLETE")

    def test_changed_duplicate_is_rejected_without_partial_summary(self):
        sample = fictional_journal()
        sample["events"][2]["units"] = 8
        result = replay(sample)
        self.assertFalse(result["valid_input"])
        self.assertEqual(result["units_by_agent"], {})
        self.assertEqual(result["events_applied"], 0)

    def test_unknown_event_type_rejected(self):
        sample = fictional_journal()
        sample["events"][0]["kind"] = ["STARTED"]
        self.assertFalse(replay(sample)["valid_input"])

    def test_broken_sequence_rejected(self):
        sample = fictional_journal()
        sample["events"][-1]["sequence"] = 4
        self.assertFalse(replay(sample)["valid_input"])

    def test_missing_start_rejected(self):
        sample = fictional_journal()
        sample["events"] = sample["events"][1:]
        self.assertFalse(replay(sample)["valid_input"])

    def test_duplicate_terminal_rejected(self):
        sample = fictional_journal()
        sample["events"].append({
            "event_id": "again", "run_id": "fictional-task", "sequence": 4,
            "agent_id": "sample-agent", "kind": "COMPLETED",
        })
        self.assertFalse(replay(sample)["valid_input"])

    def test_agent_swap_and_bool_units_rejected(self):
        sample = fictional_journal()
        sample["events"][1]["agent_id"] = "rogue-agent"
        self.assertFalse(replay(sample)["valid_input"])
        sample = fictional_journal()
        sample["events"][1]["units"] = True
        self.assertFalse(replay(sample)["valid_input"])

    def test_failed_terminal_is_reconciled_but_not_completed(self):
        sample = fictional_journal()
        sample["events"][-1]["kind"] = "FAILED"
        result = replay(sample)
        self.assertTrue(result["fully_reconciled"])
        self.assertEqual(result["runs"]["fictional-task"]["status"], "FAILED")

    def test_malformed_and_empty_input_fails_closed(self):
        self.assertFalse(replay(None)["valid_input"])
        self.assertFalse(replay({"schema":"agentops.event-journal.v1","events":[]})["valid_input"])
        item = fictional_journal()
        item["events"].append({"oops":"no"})
        self.assertFalse(replay(item)["valid_input"])

    def test_interleaved_runs_sum_by_agent(self):
        sample = fictional_journal()
        sample["events"].insert(2, {
            "event_id": "other-start", "run_id": "other-run", "sequence": 1,
            "agent_id": "sample-agent", "kind": "STARTED",
        })
        sample["events"].append({
            "event_id": "other-usage", "run_id": "other-run", "sequence": 2,
            "agent_id": "sample-agent", "kind": "USAGE", "units": 3,
        })
        sample["events"].append({
            "event_id": "other-finish", "run_id": "other-run", "sequence": 3,
            "agent_id": "sample-agent", "kind": "COMPLETED",
        })
        result = replay(sample)
        self.assertTrue(result["fully_reconciled"])
        self.assertEqual(result["units_by_agent"], {"sample-agent": 10})

    def test_script_free_html_escapes_untrusted_content(self):
        report = replay(fictional_journal())
        report["errors"] = ['<script>alert("test")</script>']
        html = html_report(report)
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("<script>", html)
        self.assertIn("Content-Security-Policy", html)

    def test_cli_exit_status_and_local_html(self):
        cmd = [sys.executable, "-m", "src.compound_intelligence.agentops_replay"]
        with tempfile.TemporaryDirectory() as root:
            output = Path(root) / "result.html"
            valid = subprocess.run(cmd + ["--demo", "--html", str(output)],
                                   text=True, capture_output=True)
            incomplete = subprocess.run(cmd + ["--truncated-demo"], text=True, capture_output=True)
            self.assertEqual(valid.returncode, 0)
            self.assertEqual(incomplete.returncode, 1)
            self.assertIn("AgentOps Replay", output.read_text(encoding="utf-8"))
            self.assertTrue(json.loads(valid.stdout)["fully_reconciled"])
            self.assertFalse(json.loads(incomplete.stdout)["fully_reconciled"])


if __name__ == "__main__":
    unittest.main()
