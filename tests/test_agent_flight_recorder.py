"""Bounded original regression fixtures for metadata-only agent trace replay."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from src.compound_intelligence.agent_flight_recorder import (
    fictional_trace, inspect_trace,
)


class FlightRecorderTests(unittest.TestCase):
    def test_replays_retry_and_exact_duplicate_without_double_application(self):
        sample = fictional_trace()
        unchanged = copy.deepcopy(sample)
        output = inspect_trace(sample)
        self.assertTrue(output["valid_input"])
        self.assertFalse(output["requires_review"])
        self.assertEqual(output["events_applied"], 4)
        self.assertEqual(output["duplicates_ignored"], 1)
        self.assertEqual(output["jobs"], [
            {"job_id": "synthetic-lookup", "attempts": 2, "last_phase": "SUCCESS"}
        ])
        self.assertEqual(sample, unchanged)
        self.assertEqual(output, inspect_trace(sample))

    def test_open_attempt_is_visible_not_claimed_complete(self):
        output = inspect_trace(fictional_trace(open_attempt=True))
        self.assertTrue(output["valid_input"])
        self.assertTrue(output["requires_review"])
        self.assertEqual(output["observations"][0]["code"], "MISSING_TERMINAL_RECEIPT")

    def test_conflicting_retry_does_not_publish_partial_state(self):
        sample = fictional_trace()
        sample["events"][1]["phase"] = "SUCCESS"
        output = inspect_trace(sample)
        self.assertFalse(output["valid_input"])
        self.assertEqual(output["events_applied"], 0)
        self.assertEqual(output["jobs"], [])
        self.assertIn("conflicting event ID", str(output["errors"]))

    def test_overlap_and_out_of_order_terminal_rejected(self):
        sample = fictional_trace()
        for bad in [
            [sample["events"][2]],
            [sample["events"][0], sample["events"][3]],
            [sample["events"][0], sample["events"][2], sample["events"][4]],
        ]:
            result = inspect_trace({"schema": sample["schema"], "events": bad})
            self.assertFalse(result["valid_input"])

    def test_retry_after_success_requires_review(self):
        sample = fictional_trace()
        sample["events"].append({"event_id": "t5", "job_id": "synthetic-lookup", "attempt": 3, "phase": "STARTED"})
        sample["events"].append({"event_id": "t6", "job_id": "synthetic-lookup", "attempt": 3, "phase": "SUCCESS"})
        output = inspect_trace(sample)
        self.assertTrue(output["valid_input"])
        self.assertTrue(output["requires_review"])
        self.assertEqual(output["observations"], [
            {"job_id": "synthetic-lookup", "code": "RETRY_AFTER_SUCCESS"}
        ])

    def test_bad_shapes_and_privileged_payload_rejected(self):
        sample = fictional_trace()
        for doc in [
            {}, {"schema": "wrong", "events": []},
            {"schema": sample["schema"], "events": []},
            {"schema": sample["schema"], "events": [{}] * 501},
        ]:
            self.assertFalse(inspect_trace(doc)["valid_input"])
        for bad_event in [
            {"event_id": "a", "job_id": "b", "attempt": True, "phase": "STARTED"},
            {"event_id": "a", "job_id": "b", "attempt": 0, "phase": "STARTED"},
            {"event_id": "a", "job_id": "b", "attempt": 31, "phase": "STARTED"},
            {"event_id": "a", "job_id": "b", "attempt": 1, "phase": []},
            {"event_id": "../secret", "job_id": "b", "attempt": 1, "phase": "STARTED"},
            {"event_id": "a", "job_id": "b", "attempt": 1, "phase": "STARTED", "payload": "sensitive"},
            ["a", "b", 1, "STARTED"],
        ]:
            self.assertFalse(inspect_trace({"schema": sample["schema"], "events": [bad_event]})["valid_input"])

    def test_cli_exit_codes_and_invalid_duplicate_key_file(self):
        base = [sys.executable, "-m", "src.compound_intelligence.agent_flight_recorder"]
        for flag, code in [("--demo", 0), ("--gap-demo", 1)]:
            run = subprocess.run(base + [flag], capture_output=True, text=True)
            self.assertEqual(run.returncode, code, run.stderr)
            self.assertTrue(json.loads(run.stdout)["valid_input"])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fictional.json"
            path.write_text('{"schema":"one","schema":"two","events":[]}', encoding="utf-8")
            run = subprocess.run(base + ["--input", str(path)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 2)
            self.assertFalse(json.loads(run.stdout)["valid_input"])
            path.write_bytes(b" " * 256_001)
            oversized = subprocess.run(base + ["--input", str(path)], capture_output=True, text=True)
            self.assertEqual(oversized.returncode, 2)
            self.assertNotIn(str(path), oversized.stdout)


if __name__ == "__main__":
    unittest.main()
