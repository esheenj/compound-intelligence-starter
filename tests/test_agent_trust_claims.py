"""Adversarial tests for deliberately non-authoritative agent identity claim checks."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from src.compound_intelligence.agentproof import parse_manifest
from src.compound_intelligence.agent_trust_claims import claim_digest, fixture, inspect, render_html


class AgentTrustClaimsTests(unittest.TestCase):
    def test_all_fictional_failure_modes_and_claim_only_not_authentication(self):
        r = inspect(fixture())
        self.assertEqual(r["claims_checked"], 11)
        self.assertEqual(r["held"], 10)
        self.assertEqual(r["claim_matches_only"], 1)
        self.assertFalse(r["identity_authenticated"])
        self.assertEqual(r["execution_authority"], "NONE")
        d = {x["claim_id"]: x for x in r["records"]}
        self.assertEqual(d["matching-claim"]["gate"], "CLAIM_MATCH_ONLY")
        self.assertEqual(d["matching-claim"]["claimed_proof"], "SELF_REPORTED_SIGNED")
        self.assertFalse(d["matching-claim"]["cryptographic_signature_verified"])
        pairs = {
            "revoked-agent": "REVOKED_REGISTRATION",
            "unknown-agent": "UNKNOWN_AGENT",
            "wrong-origin": "ORIGIN_MISMATCH",
            "wrong-key": "KEY_FINGERPRINT_MISMATCH",
            "capability-escalation": "CAPABILITY_NOT_DECLARED",
            "stale-registry": "STALE_REGISTRY_REVISION",
            "nonce-replay-first": "REPLAYED_NONCE",
            "nonce-replay-second": "REPLAYED_NONCE",
            "expired": "EXPIRED_CLAIM",
            "checksum-tamper": "CHECKSUM_MISMATCH",
        }
        for cid, issue in pairs.items():
            with self.subTest(cid=cid):
                self.assertEqual(d[cid]["gate"], "HOLD")
                self.assertIn(issue, d[cid]["reasons"])
                self.assertFalse(d[cid]["identity_authenticated"])

    def test_deterministic_and_input_unchanged(self):
        f = fixture()
        old = copy.deepcopy(f)
        self.assertEqual(inspect(f), inspect(f))
        self.assertEqual(f, old)
        self.assertRegex(inspect(f)["input_sha256"], r"^[a-f0-9]{64}$")

    def test_claim_order_changes_input_hash_not_decisions(self):
        f = fixture()
        old = inspect(f)
        f["claims"].reverse()
        f["registry"].reverse()
        r = inspect(f)
        self.assertEqual(old["records"], r["records"])
        self.assertNotEqual(old["input_sha256"], r["input_sha256"])

    def test_valid_checksum_is_not_authenticated_identity(self):
        f = fixture()
        f["claims"] = [f["claims"][0]]
        r = inspect(f)
        self.assertEqual(r["held"], 0)
        self.assertFalse(r["records"][0]["identity_authenticated"])
        self.assertFalse(r["records"][0]["cryptographic_signature_verified"])
        self.assertEqual(r["status"], "DIAGNOSTIC_ONLY_NO_IDENTITY_AUTHENTICATION")

    def test_a_forged_claim_with_recalculated_checksum_still_not_authentic(self):
        f = fixture()
        bad = f["claims"][0]
        bad["key_fingerprint"] = "c" * 64
        bad["payload_sha256"] = claim_digest(bad)
        r = next(x for x in inspect(f)["records"] if x["claim_id"] == bad["claim_id"])
        self.assertTrue(r["checksum_matches"])
        self.assertIn("KEY_FINGERPRINT_MISMATCH", r["reasons"])
        self.assertFalse(r["identity_authenticated"])

    def test_new_capability_without_manifest_grant_is_not_allowed(self):
        f = fixture()
        claim = f["claims"][0]
        claim["capability"] = "payments"
        claim["payload_sha256"] = claim_digest(claim)
        r = next(x for x in inspect(f)["records"] if x["claim_id"] == claim["claim_id"])
        self.assertEqual(r["gate"], "HOLD")
        self.assertIn("CAPABILITY_NOT_DECLARED", r["reasons"])

    def test_not_yet_valid_and_expiry(self):
        f = fixture()
        f["evaluation_tick"] = 1
        rec = next(x for x in inspect(f)["records"] if x["claim_id"] == "matching-claim")
        self.assertIn("NOT_YET_VALID", rec["reasons"])
        f["evaluation_tick"] = 200
        rec = next(x for x in inspect(f)["records"] if x["claim_id"] == "matching-claim")
        self.assertIn("EXPIRED_CLAIM", rec["reasons"])

    def test_missing_replayed_nonce_same_agent_hold(self):
        f = fixture()
        f["claims"] = [x for x in f["claims"] if x["claim_id"] not in
                       {"nonce-replay-second", "nonce-replay-first"}]
        r = inspect(f)
        self.assertEqual(r["held"], 8)

    def test_duplicate_structural_fields_and_types_rejected(self):
        f = fixture()
        cases = []
        def v(fn):
            copy_f = copy.deepcopy(f)
            fn(copy_f)
            cases.append(copy_f)
        v(lambda d: d["registry"].append(copy.deepcopy(d["registry"][0])))
        v(lambda d: d["claims"].append(copy.deepcopy(d["claims"][0])))
        v(lambda d: d["registry"][0].update(state="UNKNOWN"))
        v(lambda d: d["registry"][0].update(revision=True))
        v(lambda d: d["claims"][0].update(proof_claim="CRYPTO_VERIFIED"))
        v(lambda d: d["claims"][0].update(expires_tick=-2))
        v(lambda d: d["claims"][0].update(issued_tick=200, expires_tick=100))
        v(lambda d: d["claims"][0].update(payload_sha256="bad"))
        v(lambda d: d["claims"][0].update(origin="http://insecure.invalid"))
        v(lambda d: d["claims"][0].update(newField="unexpected"))
        v(lambda d: d["registry"][0].update(capabilities=["x", "x"]))
        v(lambda d: d.update(schema="v0"))
        for doc in cases:
            with self.subTest(doc=str(doc)[:90]):
                with self.assertRaises(ValueError):
                    inspect(doc)

    def test_reject_duplicate_json_key(self):
        with self.assertRaises(ValueError):
            parse_manifest('{"schema":"a","schema":"b"}')

    def test_html_escapes_untrusted_data_and_blocks_script(self):
        r = inspect(fixture())
        r["records"][0]["claim_id"] = "<img src=x onerror=alert(1)>"
        page = render_html(r)
        self.assertIn("&lt;img", page)
        self.assertNotIn("<img", page)
        self.assertNotIn("<script", page)
        self.assertIn("Content-Security-Policy", page)

    def test_cli_and_bad_document(self):
        cmd = [sys.executable, "-m", "src.compound_intelligence.agent_trust_claims"]
        with tempfile.TemporaryDirectory() as td:
            output = Path(td) / "report.html"
            run = subprocess.run(cmd+["--demo","--html",str(output)],capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stderr)
            self.assertEqual(json.loads(run.stdout)["claims_checked"],11)
            self.assertTrue(output.exists())
            bad = Path(td)/"bad.json"
            bad.write_text('{"schema":"bad","schema":"bad"}',encoding="utf-8")
            denied = subprocess.run(cmd+["--input",str(bad)],capture_output=True,text=True)
            self.assertEqual(denied.returncode,2)
            self.assertEqual(json.loads(denied.stdout)["status"],"REJECTED")


if __name__ == "__main__":
    unittest.main()
