"""Negative, default-deny tests for public support checkout and wallet destinations."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from scripts.render_support import load_channels, render_support, validate_channels


def default():
    return {
        "schema": "esheen-labs.support.v1",
        "github_sponsors": {"state": "pending", "url": ""},
        "fiat": {"state": "pending", "provider": "none", "url": ""},
        "crypto": {"state": "pending", "wallets": []},
    }


def sponsor():
    return {"state": "active", "url": "https://github.com/sponsors/esheenj", "verified_by_owner": True}


def fiat():
    return {"state": "active", "provider": "yoco", "url": "https://pay.yoco.com/exampleproject", "verified_by_owner": True}


def crypto():
    return {"state": "active", "wallets": [
        {"asset": "ETH", "network": "ethereum-mainnet",
         "address": "0x" + "a1" * 20, "verified_by_owner": True},
        {"asset": "BTC", "network": "bitcoin-mainnet",
         "address": "1BoatSLRHtKNngkdXEeobR76b53LETtpyT", "verified_by_owner": True},
    ]}


class SupportRenderTests(unittest.TestCase):
    def test_actual_manifest_is_default_deny_and_no_live_destinations(self):
        path = Path(__file__).resolve().parents[1] / "support/channels.json"
        manifest = load_channels(path)
        self.assertEqual(manifest, default())
        page = render_support(manifest).decode("utf-8")
        self.assertIn("No public wallet address", page)
        self.assertIn("Not connected yet", page)
        self.assertNotIn("https://pay.yoco.com/", page)
        self.assertNotIn("https://paystack.com/pay/", page)
        self.assertNotIn("https://github.com/sponsors/esheenj", page)
        self.assertNotIn("<script", page)
        self.assertNotIn("<form", page)
        self.assertIn("connect-src 'none'", page)
        self.assertIn("No Section 18A certificate", page)

    def test_active_example_fully_renders_only_if_explicitly_marked_verified(self):
        doc = default()
        doc["github_sponsors"] = sponsor()
        doc["fiat"] = fiat()
        doc["crypto"] = crypto()
        original = copy.deepcopy(doc)
        value = render_support(doc).decode("utf-8")
        self.assertIn("https://github.com/sponsors/esheenj", value)
        self.assertIn("https://pay.yoco.com/exampleproject", value)
        self.assertIn("bitcoin-mainnet", value)
        self.assertIn("ethereum-mainnet", value)
        self.assertIn("No automatic product access", value)
        self.assertEqual(original, doc)
        self.assertEqual(render_support(doc).decode("utf-8"), value)

    def test_active_provider_strict_hosts_no_redirect_or_query_parameters(self):
        for url in [
            "http://pay.yoco.com/exampleproject",
            "https://pay.yoco.com.evil.test/exampleproject",
            "https://user:pass@pay.yoco.com/exampleproject",
            "https://pay.yoco.com:8443/exampleproject",
            "https://pay.yoco.com/exampleproject?amount=1",
            "https://pay.yoco.com/exampleproject#fragment",
            "javascript:alert(1)",
            "https://pay.yoco.com/",
            "https://pay.yoco.com/example/another",
            "https://pay.yoco.com/exampleproject\n",
        ]:
            with self.subTest(url=url):
                doc = default()
                doc["fiat"] = fiat()
                doc["fiat"]["url"] = url
                with self.assertRaisesRegex(ValueError, "SUPPORT_FIAT_URL"):
                    render_support(doc)
        doc = default()
        doc["fiat"] = {"state": "active", "provider": "paystack",
                       "url": "https://paystack.com/pay/exampleproject",
                       "verified_by_owner": True}
        self.assertIn("secure Paystack checkout", render_support(doc).decode("utf-8"))

    def test_missing_owner_attestation_never_activates_any_channel(self):
        for method, value in [("github_sponsors", sponsor()), ("fiat", fiat())]:
            for flag in (False, None):
                doc = default()
                doc[method] = {**value, "verified_by_owner": flag}
                with self.assertRaises(ValueError):
                    render_support(doc)
        doc = default()
        doc["crypto"] = crypto()
        doc["crypto"]["wallets"][0]["verified_by_owner"] = False
        with self.assertRaises(ValueError):
            render_support(doc)

    def test_wrong_network_address_type_and_missing_asset_are_rejected(self):
        invalid_wallets = [
            {"asset": "ETH", "network": "bitcoin-mainnet", "address": "0x" + "a1" * 20, "verified_by_owner": True},
            {"asset": "USDT", "network": "base-mainnet", "address": "0x" + "a1" * 20, "verified_by_owner": True},
            {"asset": "ETH", "network": "ethereum-mainnet", "address": "0x" + "0" * 40, "verified_by_owner": True},
            {"asset": "BTC", "network": "bitcoin-mainnet", "address": "1abc", "verified_by_owner": True},
            {"asset": "ETH", "network": "ethereum-mainnet", "address": "0x" + "g" * 40, "verified_by_owner": True},
            {"asset": "SOL", "network": "solana-mainnet", "address": "O" * 33, "verified_by_owner": True},
            {"asset": "ETH", "network": "ethereum-mainnet", "address": True, "verified_by_owner": True},
            {"asset": "ETH", "network": "ethereum-mainnet", "address": "0x" + "a1" * 20, "verified_by_owner": True, "private_key": "do-not-publish"},
        ]
        for row in invalid_wallets:
            with self.subTest(row=row):
                doc = default()
                doc["crypto"] = {"state": "active", "wallets": [row]}
                with self.assertRaises(ValueError):
                    render_support(doc)

    def test_duplicate_chain_pair_or_unreviewed_future_field_fails_closed(self):
        doc = default()
        doc["crypto"] = crypto()
        doc["crypto"]["wallets"].append(copy.deepcopy(doc["crypto"]["wallets"][0]))
        with self.assertRaisesRegex(ValueError, "DUPLICATE"):
            validate_channels(doc)
        doc = default()
        doc["extra_provider"] = {"status": "active", "address": "bad"}
        with self.assertRaisesRegex(ValueError, "FIELDS_ROOT"):
            render_support(doc)

    def test_pending_cannot_sneak_a_checkout_or_wallet_into_source(self):
        doc = default()
        doc["github_sponsors"]["url"] = "https://github.com/sponsors/esheenj"
        with self.assertRaises(ValueError):
            render_support(doc)
        doc = default()
        doc["crypto"]["wallets"] = crypto()["wallets"]
        with self.assertRaises(ValueError):
            render_support(doc)
        doc = default()
        doc["fiat"]["provider"] = "yoco"
        with self.assertRaises(ValueError):
            render_support(doc)

    def test_duplicate_json_keys_and_nonfinite_parse_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "channels.json"
            path.write_text('{"schema":"x","schema":"y"}', encoding="utf-8")
            with self.assertRaises(ValueError):
                load_channels(path)
            path.write_text('{"schema":NaN}', encoding="utf-8")
            with self.assertRaises(ValueError):
                load_channels(path)
            path.write_text("x" * 16385, encoding="utf-8")
            with self.assertRaises(ValueError):
                load_channels(path)


if __name__ == "__main__":
    unittest.main()
