"""Fail-closed source, deployment and public-link tests for the Sigma Code integration offer."""
import hashlib
import tempfile
import unittest
from pathlib import Path
from scripts.stage_showcase import (
    INTEGRATION_OFFER_SOURCE, SOURCE, stage_catalog,
    verify_catalog, verify_integration_offer,
)

class IntegrationOfferTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw=INTEGRATION_OFFER_SOURCE.read_bytes()
        cls.page=cls.raw.decode("utf-8")

    def test_source_contract_and_hash(self):
        result=verify_integration_offer(self.raw)
        self.assertEqual(result["state"],"SOURCE_VALIDATED")
        self.assertEqual(result["linkedFreeTools"],4)
        self.assertEqual(result["linkedDeveloperLabs"],2)
        self.assertEqual(result["htmlSha256"],hashlib.sha256(self.raw).hexdigest())

    def test_gallery_does_not_inflate_repository_or_demo_counts(self):
        catalog=verify_catalog(SOURCE.read_bytes())
        self.assertEqual(catalog["repoCount"],22)
        self.assertEqual(catalog["githubDeployedUrlCount"],22)
        text=SOURCE.read_text()
        self.assertIn("<strong>43</strong><span>public demo pages",text)
        self.assertGreaterEqual(text.count('href="integration-reliability.html"'),2)

    def test_explicit_six_original_links(self):
        for slug in (
            "integration-reliability-assessment","integration-delivery-trace-inspector",
            "workflow-failure-test-builder","deterministic-replay-fixture-generator",
            "event-replay-rust-parity-lab","event-contract-evolution-lab"
        ):
            with self.subTest(slug=slug):
                self.assertIn('href="https://esheenj.github.io/'+slug+'/"',self.page)
                self.assertIn('href="https://github.com/esheenj/'+slug+'"',self.page)

    def test_customer_enquiry_is_user_initiated_only(self):
        self.assertIn('mailto:info@sigmacode.co.za?subject=Integration%20reliability%20pilot%20enquiry',self.page)
        self.assertIn("An enquiry is not a booking",self.page)
        self.assertIn("Keep customer identifiers, production logs, credentials",self.page)

    def test_discloses_synthetic_and_real_world_boundary(self):
        self.assertIn("not a security certification",self.page)
        self.assertIn("fictional",self.page)
        self.assertIn("not a booking",self.page)
        self.assertIn("not of the provider",self.page)
        self.assertNotIn("guaranteed ROI",self.page)

    def test_no_analytics_or_data_collection(self):
        for forbidden in ("<script", "<form", "fetch(", "XMLHttpRequest", "localStorage",
                          "sessionStorage", "gtag(", "dataLayer", "<iframe", "google-analytics"):
            self.assertNotIn(forbidden,self.page)
        self.assertIn("connect-src 'none'",self.page)
        self.assertIn("script-src 'none'",self.page)

    def test_reject_script_injection(self):
        mutated=self.raw.replace(b"</main>",b"<script>alert('x')</script></main>")
        with self.assertRaises(ValueError):
            verify_integration_offer(mutated)

    def test_reject_unapproved_link(self):
        mutated=self.raw.replace(b'href="https://sigmacode.co.za/"',
                                b'href="https://unknown-example.com/"')
        with self.assertRaisesRegex(ValueError,"DESTINATION"):
            verify_integration_offer(mutated)

    def test_reject_missing_qualifying_tool(self):
        mutated=self.raw.replace(b'href="https://esheenj.github.io/event-contract-evolution-lab/"',
                                 b'href="#engineering"')
        with self.assertRaisesRegex(ValueError,"MISSING_TOOL"):
            verify_integration_offer(mutated)

    def test_reject_altered_commercial_enquiry_destination(self):
        mutated=self.raw.replace(b"mailto:info@sigmacode.co.za",b"mailto:attacker@example.com")
        with self.assertRaisesRegex(ValueError,"EMAIL_ROUTE"):
            verify_integration_offer(mutated)

    def test_reject_mailto_bcc_injection(self):
        mutated=self.raw.replace(b"by%20email.",b"by%20email.&amp;bcc=unknown%40example.com")
        with self.assertRaisesRegex(ValueError,"EMAIL_ROUTE"):
            verify_integration_offer(mutated)

    def test_reject_form_or_network_capability(self):
        for extra in (b'<form action="https://example.org">', b'fetch("https://example.org")'):
            with self.subTest(extra=extra):
                with self.assertRaises(ValueError):
                    verify_integration_offer(self.raw.replace(b"</main>",extra+b"</main>"))

    def test_reject_wrong_inventory_claim(self):
        mutated=self.raw.replace(b"All 43 demos",b"44 demos")
        with self.assertRaisesRegex(ValueError,"UNSUPPORTED_CLAIM"):
            verify_integration_offer(mutated)

    def test_strict_utf8_source_and_size(self):
        with self.assertRaises(UnicodeDecodeError):
            verify_integration_offer(b"\xff")
        with self.assertRaises(ValueError):
            verify_integration_offer(b"x"*46001)

    def test_stage_contains_exact_offer_byte_copy_not_runtime_bundle(self):
        with tempfile.TemporaryDirectory() as folder:
            dst=Path(folder)/"site"
            result=stage_catalog(dst)
            self.assertTrue(result["integrationOfferSourceValidated"])
            self.assertEqual((dst/"integration-reliability.html").read_bytes(),self.raw)
            self.assertFalse((dst/"scripts").exists())
            self.assertFalse((dst/".git").exists())

if __name__=="__main__":
    unittest.main()
