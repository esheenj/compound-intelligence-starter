"""Source-only public directory staging must be deterministic and safe."""
import hashlib
import tempfile
import unittest
from pathlib import Path

from scripts.stage_showcase import SOURCE, MVP_WAVE_SOURCE, AGENTOPS_SOURCE, AGENTPROOF_SOURCE, AGENTCREDITS_SOURCE, MODEL_COST_SOURCE, MODEL_FIT_SOURCE, CONTEXT_SOURCE, DISAGREEMENT_SOURCE, DECISION_REVIEW_SOURCE, AGENT_TRUST_SOURCE, SIGNED_AGENT_SOURCE, stage_catalog, verify_catalog


class ShowcaseStageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.output = self.root / "pages"

    def test_exact_public_collection_stage_and_receipt(self):
        report = stage_catalog(self.output)
        self.assertEqual(report["state"], "STAGED_ONLY")
        self.assertEqual(report["repoCount"], 8)
        self.assertIn(b"SUPPORT_AND_SUSTAINABILITY.md", SOURCE.read_bytes())
        self.assertIn(b"PUBLIC_INTELLIGENCE_BOUNDARY.md", SOURCE.read_bytes())
        self.assertEqual(report["githubDeployedUrlCount"], 8)
        self.assertFalse(report["independentBrowserVerified"])
        self.assertFalse(report["publicHostingVerified"])
        self.assertEqual(report["files"], [".nojekyll", "agent-trust.html", "agentcredits.html", "agentops.html", "agentproof.html", "context-preservation.html", "decision-review.html", "index.html", "model-cost.html", "model-disagreement.html", "model-fit.html", "mvp-wave.html", "signed-agent.html", "support.html"])
        support = self.output.joinpath("support.html").read_bytes()
        self.assertIn(b"No public wallet address", support)
        self.assertIn(b"Not connected yet", support)
        self.assertIn(b"connect-src 'none'", support)
        self.assertNotIn(b"https://paystack.com/pay/", support)
        self.assertNotIn(b"https://pay.yoco.com/", support)
        self.assertEqual(report["supportPageSha256"], hashlib.sha256(support).hexdigest())
        content = self.output.joinpath("index.html").read_bytes()
        self.assertEqual(content, SOURCE.read_bytes())
        self.assertIn(b"28 of 28 public demo pages passed independent live HTTPS Chrome acceptance", content)
        self.assertIn(b"actions/runs/43064815195", content)
        self.assertIn(b"docs/MARKETING_AND_EMBED_KIT.md", content)
        self.assertIn(b'href="support.html"', content)
        self.assertNotIn(b"independent external HTTPS checks for those six are pending", content)
        self.assertEqual(report["htmlSha256"], hashlib.sha256(content).hexdigest())
        self.assertEqual(report["additionalHostedToolCount"], 11)
        self.assertEqual(report["additionalLinkedPublicToolCount"], 10)
        self.assertIn(b"https://esheenj.github.io/mobile-first-flow-kit-oss/recovery.html", content)
        self.assertIn(b"https://esheenj.github.io/design-system-foundations-oss/audit.html", content)
        self.assertIn(b"https://esheenj.github.io/data-table-interactions-oss/experiment.html", content)
        for tool_url in (
            b"https://esheenj.github.io/form-experience-kit-oss/onboarding.html",
            b"https://esheenj.github.io/flow-state-machine-oss/journey.html",
            b"https://esheenj.github.io/data-table-interactions-oss/quality.html",
        ):
            self.assertIn(tool_url, content)
        for tool_url in (
            b"https://esheenj.github.io/form-experience-kit-oss/consent.html",
            b"https://esheenj.github.io/mobile-first-flow-kit-oss/notifications.html",
            b"https://esheenj.github.io/flow-state-machine-oss/blueprint.html",
            b"https://esheenj.github.io/flow-state-machine-oss/approval.html",
        ):
            self.assertIn(tool_url, content)
        agentops = self.output.joinpath("agentops.html").read_bytes()
        self.assertEqual(agentops, AGENTOPS_SOURCE.read_bytes())
        self.assertEqual(report["agentOpsSha256"], hashlib.sha256(agentops).hexdigest())
        self.assertIn(b"connect-src 'none'", agentops)
        self.assertIn(b"agentops.html", content)
        self.assertIn(b"AgentOps Replay Studio", content)
        agentproof = self.output.joinpath("agentproof.html").read_bytes()
        self.assertEqual(agentproof, AGENTPROOF_SOURCE.read_bytes())
        self.assertEqual(report["agentProofSha256"], hashlib.sha256(agentproof).hexdigest())
        self.assertIn(b"connect-src 'none'", agentproof)
        self.assertIn(b"agentproof.html", content)
        self.assertIn(b"AgentProof Receipt Verifier", content)
        agentcredits = self.output.joinpath("agentcredits.html").read_bytes()
        self.assertEqual(agentcredits, AGENTCREDITS_SOURCE.read_bytes())
        self.assertEqual(report["agentCreditsSha256"], hashlib.sha256(agentcredits).hexdigest())
        self.assertIn(b"connect-src 'none'", agentcredits)
        self.assertIn(b"agentcredits.html", content)
        self.assertIn(b"AgentCredits Ledger Studio", content)
        for fname, original, digest_key, label in (
            ("model-cost.html", MODEL_COST_SOURCE, "modelCostSha256", b"Model Cost Comparator"),
            ("model-fit.html", MODEL_FIT_SOURCE, "modelFitSha256", b"Local Model Fit Planner"),
            ("context-preservation.html", CONTEXT_SOURCE, "contextSha256", b"Context Preservation Lab"),
            ("model-disagreement.html", DISAGREEMENT_SOURCE, "modelDisagreementSha256", b"Model Disagreement Lab"),
            ("decision-review.html", DECISION_REVIEW_SOURCE, "decisionReviewSha256", b"Explainable Decision Review"),
            ("agent-trust.html", AGENT_TRUST_SOURCE, "agentTrustSha256", b"Agent Trust &amp; Identity Lab"),
            ("signed-agent.html", SIGNED_AGENT_SOURCE, "signedAgentSha256", b"Signed Agent Challenge"),
        ):
            page = self.output.joinpath(fname).read_bytes()
            self.assertEqual(page, original.read_bytes())
            self.assertEqual(report[digest_key], hashlib.sha256(page).hexdigest())
            self.assertIn(b"connect-src 'none'", page)
            self.assertIn(fname.encode(), content)
            self.assertIn(label, content)
        wave = self.output.joinpath("mvp-wave.html").read_bytes()
        self.assertEqual(wave, MVP_WAVE_SOURCE.read_bytes())
        self.assertEqual(report["mvpWaveSha256"], hashlib.sha256(wave).hexdigest())
        self.assertIn(b"connect-src 'none'", wave)
        self.assertIn(b"MVP Wave Planner", content)
        self.assertEqual(sorted(x.name for x in self.output.iterdir()), [".nojekyll", "agent-trust.html", "agentcredits.html", "agentops.html", "agentproof.html", "context-preservation.html", "decision-review.html", "index.html", "model-cost.html", "model-disagreement.html", "model-fit.html", "mvp-wave.html", "signed-agent.html", "support.html"])
        self.assertNotIn(b"<script", content)
        self.assertNotIn(b"<img", content)
        self.assertEqual(content.count(b">Try demo</a>"), 8)
        self.assertIn(b"https://esheenj.github.io/agent-capability-policy-lab/", content)
        self.assertIn(b"29</strong><span>public demo pages", content)
        self.assertEqual(content.count(b'<li class="tool '), 21)
        self.assertIn(b'id="filter-ai"', content)
        self.assertIn(b"prefers-reduced-motion", content)
        self.assertIn(b"https://esheenj.github.io/visual-regression-starter-oss/", content)

    def test_repeated_stage_never_overwrites(self):
        stage_catalog(self.output)
        first = (self.output / "index.html").read_bytes()
        with self.assertRaisesRegex(ValueError, "OUTPUT_EXISTS"):
            stage_catalog(self.output)
        self.assertEqual((self.output / "index.html").read_bytes(), first)

    def test_source_html_needs_all_eight_public_repo_links(self):
        source = SOURCE.read_bytes()
        self.assertEqual(verify_catalog(source)["repoCount"], 8)
        with self.assertRaisesRegex(ValueError, "PUBLIC_REPOSITORY_LINK_MISSING"):
            verify_catalog(source.replace(b"visual-regression-starter-oss", b"broken-repo-name"))
        for new_tool in (b"model-cost.html", b"model-fit.html", b"context-preservation.html", b"model-disagreement.html", b"decision-review.html", b"agent-trust.html", b"signed-agent.html"):
            with self.assertRaisesRegex(ValueError, "ADDITIONAL_TOOL_LINK_MISSING"):
                verify_catalog(source.replace(b'href="' + new_tool + b'"',
                                              b'href="missing-tool.html"'))
        with self.assertRaisesRegex(ValueError, "ADDITIONAL_TOOL_LINK_MISSING"):
            verify_catalog(source.replace(b'href="agentcredits.html"', b'href="agentcredits-invalid.html"'))
        with self.assertRaisesRegex(ValueError, "ADDITIONAL_TOOL_LINK_MISSING"):
            verify_catalog(source.replace(b'href="agentproof.html"', b'href="agentproof-invalid.html"'))
        with self.assertRaisesRegex(ValueError, "ADDITIONAL_TOOL_LINK_MISSING"):
            verify_catalog(source.replace(b'href="agentcredits.html"', b'href="agentcredits-invalid.html"'))
        with self.assertRaisesRegex(ValueError, "ADDITIONAL_TOOL_LINK_MISSING"):
            verify_catalog(source.replace(b'href="agentops.html"', b'href="agentops-invalid.html"'))
        with self.assertRaisesRegex(ValueError, "ADDITIONAL_TOOL_LINK_MISSING"):
            verify_catalog(source.replace(b'href="agentcredits.html"', b'href="agentcredits-invalid.html"'))
        with self.assertRaisesRegex(ValueError, "ADDITIONAL_TOOL_LINK_MISSING"):
            verify_catalog(source.replace(b'href="agentproof.html"', b'href="agentproof-invalid.html"'))
        with self.assertRaisesRegex(ValueError, "ADDITIONAL_TOOL_LINK_MISSING"):
            verify_catalog(source.replace(b'href="agentcredits.html"', b'href="agentcredits-invalid.html"'))
        with self.assertRaisesRegex(ValueError, "ADDITIONAL_TOOL_LINK_MISSING"):
            verify_catalog(source.replace(b"https://esheenj.github.io/design-system-foundations-oss/audit.html", b"https://esheenj.github.io/design-system-foundations-oss/"))
        with self.assertRaisesRegex(ValueError, "ADDITIONAL_TOOL_LINK_MISSING"):
            verify_catalog(source.replace(b'href="agentcredits.html"', b'href="agentcredits-invalid.html"'))
        with self.assertRaisesRegex(ValueError, "ADDITIONAL_TOOL_LINK_MISSING"):
            verify_catalog(source.replace(b'href="agentproof.html"', b'href="agentproof-invalid.html"'))
        with self.assertRaisesRegex(ValueError, "ADDITIONAL_TOOL_LINK_MISSING"):
            verify_catalog(source.replace(b'href="agentcredits.html"', b'href="agentcredits-invalid.html"'))
        with self.assertRaisesRegex(ValueError, "ADDITIONAL_TOOL_LINK_MISSING"):
            verify_catalog(source.replace(b"https://esheenj.github.io/flow-state-machine-oss/approval.html", b"https://esheenj.github.io/flow-state-machine-oss/"))
        with self.assertRaisesRegex(ValueError, "ADDITIONAL_TOOL_LINK_MISSING"):
            verify_catalog(source.replace(b'href="support.html"', b'href="support-fake.html"'))
        with self.assertRaisesRegex(ValueError, "CATALOG_EXTERNAL_LINK_NOT_ALLOWED"):
            verify_catalog(source.replace(b'href="#projects"', b'href="https://example.invalid/projects"'))
        with self.assertRaisesRegex(ValueError, "PUBLIC_CARD_LINK_MISMATCH"):
            verify_catalog(source.replace(
                b'https://esheenj.github.io/visual-regression-starter-oss/',
                b'https://esheenj.github.io/form-experience-kit-oss/', 1))
        with self.assertRaisesRegex(ValueError, "INVALID_CATALOG_STRUCTURE"):
            verify_catalog(source.replace(b"<main", b"<section", 1))

    def test_refuses_binary_and_unbounded_input(self):
        for example in (b"\x00", b"x" * 150001, b"\xff\xfe"):
            with self.subTest(length=len(example)):
                with self.assertRaises((UnicodeError, ValueError)):
                    verify_catalog(example)

    def test_does_not_stage_into_unapproved_repo_directory(self):
        with self.assertRaisesRegex(ValueError, "DESTINATION_INSIDE_PUBLIC_SOURCE"):
            stage_catalog(SOURCE.parent / "staged-inside-site")


if __name__ == "__main__":
    unittest.main()
