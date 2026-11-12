"""Guard the owner's public exchange deposit funding routes and rendered labels."""
from __future__ import annotations

import copy
import unittest
from pathlib import Path

from scripts.render_support import PIONEX_MINIMUM_SNAPSHOT, load_channels, render_support, validate_channels


class OwnerFundingRoutesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = load_channels(Path(__file__).resolve().parents[1] / "support/channels.json")

    def test_exact_current_owner_supplied_route_types(self):
        self.assertEqual(self.manifest["github_sponsors"]["state"], "pending")
        self.assertEqual(self.manifest["fiat"]["state"], "pending")
        self.assertEqual(self.manifest["crypto"]["state"], "active")
        rows = self.manifest["crypto"]["wallets"]
        self.assertEqual(len(rows), 4)
        self.assertEqual({(row["asset"], row["network"]) for row in rows},
                         {("BTC", "bitcoin-mainnet"),
                          ("USDT", "solana-mainnet"),
                          ("USDT", "ethereum-mainnet"),
                          ("USDT", "tron-mainnet")})
        self.assertTrue(all(row["verified_by_owner"] is True and
                            row["destination_type"] == "pionex-exchange-deposit" and
                            row["minimum_snapshot"] ==
                            PIONEX_MINIMUM_SNAPSHOT[(row["asset"], row["network"])]
                            for row in rows))

    def test_all_destinations_render_as_inert_html_with_precise_custody_and_minimum(self):
        html = render_support(self.manifest).decode("utf-8")
        for row in self.manifest["crypto"]["wallets"]:
            self.assertIn(row["address"], html)
            self.assertIn(row["network"], html)
            self.assertIn(row["minimum_snapshot"], html)
        self.assertEqual(html.count("<li><strong>"), 4)
        self.assertEqual(html.count("Pionex custodial exchange deposit"), 4)
        self.assertIn("Before each transfer, verify the current Pionex deposit address", html)
        self.assertIn("Never reuse an address after an exchange replacement notice", html)
        self.assertIn("No Section 18A certificate", html)
        self.assertNotIn("https://github.com/sponsors/esheenj", html)
        self.assertNotIn("https://paystack.com/pay/", html)
        self.assertNotIn("<script", html)
        self.assertNotIn("<form", html)

    def test_invalid_exchange_metadata_cannot_publish(self):
        for action in ("wrong_minimum", "wrong_custodian", "unverified", "extra_key", "wrong_coin"):
            doc = copy.deepcopy(self.manifest)
            row = doc["crypto"]["wallets"][0]
            if action == "wrong_minimum":
                row["minimum_snapshot"] = "0.0 BTC"
            elif action == "wrong_custodian":
                row["destination_type"] = "official-github-sponsors"
            elif action == "unverified":
                row["verified_by_owner"] = False
            elif action == "extra_key":
                row["private_key"] = "NEVER"
            else:
                row["asset"] = "USDT"
            with self.subTest(action=action), self.assertRaises(ValueError):
                validate_channels(doc)

    def test_wrong_chain_address_is_rejected(self):
        doc = copy.deepcopy(self.manifest)
        doc["crypto"]["wallets"][1]["address"] = doc["crypto"]["wallets"][2]["address"]
        with self.assertRaises(ValueError):
            validate_channels(doc)


if __name__ == "__main__":
    unittest.main()
