"""Independent negative fixtures for public AgentProof demo."""
import copy
import json
import subprocess
import sys
import unittest

from src.compound_intelligence.agentproof import (
    fictional_manifest, parse_manifest, payload_digest, verify_manifest,
)


class AgentProofTests(unittest.TestCase):
    def test_demo_integrity_only(self):
        report = verify_manifest(fictional_manifest())
        self.assertTrue(report["integrity_valid"])
        self.assertEqual(report["events_checked"], 3)
        self.assertIn("no proof of truth", report["scope"])

    def test_detects_payload_tamper(self):
        sample = fictional_manifest()
        sample["events"][1]["payload"]["passed"] = False
        self.assertFalse(verify_manifest(sample)["integrity_valid"])
        self.assertIn("digest mismatch", str(verify_manifest(sample)["errors"]))

    def test_detects_duplicate_identity(self):
        sample = fictional_manifest()
        sample["events"][2]["event_id"] = "example-1"
        self.assertIn("duplicate event_id", str(verify_manifest(sample)["errors"]))

    def test_detects_sequence_gap(self):
        sample = fictional_manifest()
        sample["events"][2]["sequence"] = 5
        self.assertIn("non-contiguous", str(verify_manifest(sample)["errors"]))

    def test_missing_producer_and_unexpected_field(self):
        sample = fictional_manifest()
        sample["events"][0].pop("claimed_producer")
        sample["events"][1]["secret"] = "forbidden"
        errors = str(verify_manifest(sample)["errors"])
        self.assertIn("claimed_producer", errors)
        self.assertIn("unexpected", errors)

    def test_rejects_boolean_sequence_and_nan(self):
        sample = fictional_manifest()
        sample["events"][0]["sequence"] = True
        self.assertFalse(verify_manifest(sample)["integrity_valid"])
        self.assertNotEqual(payload_digest({"a": 1}), payload_digest({"a": 2}))
        with self.assertRaises(ValueError):
            payload_digest({"a": float("nan")})

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate JSON"):
            parse_manifest('{"schema":"x","schema":"y","events":[]}')
        with self.assertRaises(ValueError):
            parse_manifest('{"a":NaN}')

    def test_cli_demo(self):
        result = subprocess.run(
            [sys.executable, "-m", "src.compound_intelligence.agentproof", "--demo"],
            capture_output=True, text=True, check=True,
        )
        self.assertTrue(json.loads(result.stdout)["integrity_valid"])


if __name__ == "__main__":
    unittest.main()
