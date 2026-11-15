"""Unit-only contracts for exact public source / deployed-byte parity."""
from __future__ import annotations

import hashlib
import unittest

from live_runner_preflight_acceptance import MAX_HTML_BYTES, verify_deployed_bytes


class LiveRunnerPreflightAcceptanceContracts(unittest.TestCase):
    def setUp(self):
        self.valid = (
            b"<!doctype html><html><body>runner-preflight-v0.2.0"
            b"<main>READY WARN HOLD</main></body></html>"
        )

    def test_exact_match_returns_hash(self):
        self.assertEqual(
            verify_deployed_bytes(self.valid, self.valid),
            hashlib.sha256(self.valid).hexdigest(),
        )

    def test_any_changed_live_byte_fails_closed(self):
        with self.assertRaisesRegex(AssertionError, "NOT_MATCH_SOURCE"):
            verify_deployed_bytes(self.valid, self.valid.replace(b"READY", b"HOLD"))

    def test_missing_release_label_fails_closed(self):
        with self.assertRaisesRegex(AssertionError, "RELEASE_LINK_MISSING"):
            verify_deployed_bytes(b"<html>no version</html>", b"<html>no version</html>")

    def test_oversized_source_or_response_rejected(self):
        with self.assertRaisesRegex(AssertionError, "SOURCE_EXCEEDS_BOUND"):
            verify_deployed_bytes(b"X" * (MAX_HTML_BYTES + 1), b"X")
        with self.assertRaisesRegex(AssertionError, "LIVE_HTML_EXCEEDS_BOUND"):
            verify_deployed_bytes(self.valid, b"X" * (MAX_HTML_BYTES + 1))


if __name__ == "__main__":
    unittest.main()
