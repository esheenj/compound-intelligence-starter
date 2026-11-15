"""Stage only the reviewed source-first public OSS catalog as a static site.

Never adds private source, generated secrets, Git history or claims hosting.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path
import shutil

if __package__:
    from .render_support import load_channels, render_support
    from .public_discovery import verify_public_discovery
else:
    from render_support import load_channels, render_support
    from public_discovery import verify_public_discovery

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "site" / "index.html"
MVP_WAVE_SOURCE = ROOT / "site" / "mvp-wave.html"
AGENTOPS_SOURCE = ROOT / "site" / "agentops.html"
AGENTPROOF_SOURCE = ROOT / "site" / "agentproof.html"
AGENTCREDITS_SOURCE = ROOT / "site" / "agentcredits.html"
MODEL_COST_SOURCE = ROOT / "site" / "model-cost.html"
MODEL_FIT_SOURCE = ROOT / "site" / "model-fit.html"
CONTEXT_SOURCE = ROOT / "site" / "context-preservation.html"
DISAGREEMENT_SOURCE = ROOT / "site" / "model-disagreement.html"
DECISION_REVIEW_SOURCE = ROOT / "site" / "decision-review.html"
AGENT_TRUST_SOURCE = ROOT / "site" / "agent-trust.html"
SIGNED_AGENT_SOURCE = ROOT / "site" / "signed-agent.html"
RUNNER_PREFLIGHT_SOURCE = ROOT / "site" / "runner-preflight.html"
INTEGRATION_OFFER_SOURCE = ROOT / "site" / "integration-reliability.html"
ROBOTS_SOURCE = ROOT / "site" / "robots.txt"
SITEMAP_SOURCE = ROOT / "site" / "sitemap.xml"
SUPPORT_CONFIG_SOURCE = ROOT / "support" / "channels.json"
DESTINATION = ROOT / "dist" / "pages"
REPOS = {
    "compound-intelligence-starter",
    "agent-capability-policy-lab",
    "prompt-evaluation-harness-oss",
    "eval-dataset-leakage-lab",
    "rag-retrieval-eval-lab",
    "agent-tool-schema-diff-lab",
    "agent-invocation-replay-lab",
    "agent-skills-manifest-validator",
    "webhook-idempotency-lab",
    "citation-provenance-inspector",
    "integration-reliability-assessment",
    "workflow-failure-test-builder",
    "integration-delivery-trace-inspector",
    "deterministic-replay-fixture-generator",
    "event-replay-rust-parity-lab",
    "event-contract-evolution-lab",
    "design-system-foundations-oss",
    "mobile-first-flow-kit-oss",
    "data-table-interactions-oss",
    "flow-state-machine-oss",
    "form-experience-kit-oss",
    "visual-regression-starter-oss",
}
DEPLOYED_PAGES = {"https://esheenj.github.io/" + repo + "/" for repo in REPOS}
UX_ENQUIRY_URL = "mailto:info@sigmacode.co.za?subject=UX%20Engineering%20Enquiry&body=Hello%20Sigma%20Code%2C%0A%0AI%20would%20like%20to%20discuss%20a%20UX%20engineering%20review.%0AChallenge%3A%20%5Bbriefly%20describe%20the%20workflow%20or%20user%20problem%5D%0ADesired%20outcome%3A%20%5Bwhat%20should%20improve%5D%0ACurrent%20platform%20(optional)%3A%20%5B%20%5D%0APreferred%20timing%20(optional)%3A%20%5B%20%5D%0A%0ASource%3A%20Compound%20Intelligence%20Lab%20UX%20Engineering.%0APlease%20recommend%20a%20suitable%20first%20step.%20No%20credentials%20or%20customer%20personal%20data%20are%20included."
EXTRA_TOOL_URLS = {
    "https://esheenj.github.io/mobile-first-flow-kit-oss/recovery.html",
    "https://esheenj.github.io/design-system-foundations-oss/audit.html",
    "https://esheenj.github.io/data-table-interactions-oss/experiment.html",
    "https://esheenj.github.io/form-experience-kit-oss/onboarding.html",
    "https://esheenj.github.io/flow-state-machine-oss/journey.html",
    "https://esheenj.github.io/data-table-interactions-oss/quality.html",
    "https://esheenj.github.io/form-experience-kit-oss/consent.html",
    "https://esheenj.github.io/mobile-first-flow-kit-oss/notifications.html",
    "https://esheenj.github.io/flow-state-machine-oss/blueprint.html",
    "https://esheenj.github.io/flow-state-machine-oss/approval.html",
}


class SourceCatalog(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.articles = 0
        self.heading = 0
        self.main = 0
        self.links = []
        self.script = False
        self.remote_assets = []
        self.card_links = []
        self._card_open = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "article" and "card" in attrs.get("class", "").split():
            self.articles += 1
            self.card_links.append([])
            self._card_open = True
        if tag == "h1":
            self.heading += 1
        if tag == "main":
            self.main += 1
        if tag == "script":
            self.script = True
        if tag in ("img", "iframe", "link", "audio", "video", "source", "object"):
            self.remote_assets.append(tag)
        if tag == "a":
            href = attrs.get("href", "")
            self.links.append(href)
            if self._card_open:
                self.card_links[-1].append(href)

    def handle_endtag(self, tag):
        if tag == "article":
            self._card_open = False


def verify_catalog(data: bytes) -> dict:
    if len(data) > 150_000 or b"\x00" in data:
        raise ValueError("INVALID_CATALOG_BYTES")
    html = data.decode("utf-8", errors="strict")
    parser = SourceCatalog()
    parser.feed(html)
    parser.close()
    if parser.script or parser.remote_assets != ["link"] or parser.articles != 22 or parser.main != 1 or parser.heading != 1:
        raise ValueError("INVALID_CATALOG_STRUCTURE")
    if (html.count('<link rel="canonical" href="https://esheenj.github.io/compound-intelligence-starter/">') != 1
            or parser.links.count("sitemap.xml") != 1):
        raise ValueError("CATALOG_DISCOVERY_LINKS_INVALID")
    if "connect-src 'none'" not in html or "script-src 'none'" not in html:
        raise ValueError("CATALOG_CSP_REQUIRED")
    expected_links = set()
    for repo in REPOS:
        base = "https://github.com/esheenj/" + repo
        expected_links.update((base, base + "/issues"))
    observed = set(parser.links)
    if not expected_links.issubset(observed):
        raise ValueError("PUBLIC_REPOSITORY_LINK_MISSING")
    if not EXTRA_TOOL_URLS.issubset(observed) or parser.links.count("mvp-wave.html") != 1 or parser.links.count("agentops.html") != 1 or parser.links.count("agentproof.html") != 1 or parser.links.count("agentcredits.html") != 1 or parser.links.count("model-cost.html") != 1 or parser.links.count("model-fit.html") != 1 or parser.links.count("context-preservation.html") != 1 or parser.links.count("model-disagreement.html") != 1 or parser.links.count("decision-review.html") != 1 or parser.links.count("agent-trust.html") != 1 or parser.links.count("signed-agent.html") != 1 or parser.links.count("support.html") != 2 or parser.links.count("integration-reliability.html") < 2:
        raise ValueError("ADDITIONAL_TOOL_LINK_MISSING")
    if parser.links.count(UX_ENQUIRY_URL) != 1:
        raise ValueError("UX_ENQUIRY_LINK_MISSING_OR_DUPLICATE")
    for link in parser.links:
        if not (link.startswith("#") or link.startswith("https://github.com/esheenj/") or link in DEPLOYED_PAGES or link == UX_ENQUIRY_URL or link in EXTRA_TOOL_URLS or link in {"mvp-wave.html", "agentops.html", "agentproof.html", "agentcredits.html", "model-cost.html", "model-fit.html", "context-preservation.html", "model-disagreement.html", "decision-review.html", "agent-trust.html", "signed-agent.html", "support.html", "integration-reliability.html", "sitemap.xml"}):
            raise ValueError("CATALOG_EXTERNAL_LINK_NOT_ALLOWED")
    # Verify exact source, issues and GitHub-deployed URL on each card.
    # A swapped destination or unrelated host must not be published.
    expected_cards = {
        ("https://github.com/esheenj/" + repo,
         "https://github.com/esheenj/" + repo + "/issues",
         "https://esheenj.github.io/" + repo + "/")
        for repo in REPOS
    }
    if {tuple(card) for card in parser.card_links} != expected_cards or len(parser.card_links) != 22:
        raise ValueError("PUBLIC_CARD_LINK_MISMATCH")
    if "WCAG certified" in html or "commercially adopted" in html:
        raise ValueError("UNSUPPORTED_CATALOG_CLAIM")
    return {"repoCount": 22, "githubDeployedUrlCount": 22,
            "independentBrowserVerified": False,
            "htmlSha256": hashlib.sha256(data).hexdigest()}


INTEGRATION_TOOL_SLUGS = (
    "integration-reliability-assessment",
    "integration-delivery-trace-inspector",
    "workflow-failure-test-builder",
    "deterministic-replay-fixture-generator",
    "event-replay-rust-parity-lab",
    "event-contract-evolution-lab",
)


APPROVED_PILOT_MAILTO = 'mailto:info@sigmacode.co.za?subject=Integration%20reliability%20pilot%20enquiry&body=Hi%20Sigma%20Code%2C%0A%0AI%27d%20like%20to%20discuss%20one%20integration%20reliability%20pilot.%0A%0AIntegration%20type%3A%20%0AObserved%20symptom%20%28general%20terms%29%3A%20%0ADesired%20outcome%3A%20%0A%0APlease%20do%20not%20request%20production%20logs%20or%20credentials%20by%20email.'

def verify_integration_offer(data: bytes) -> dict:
    """Fail closed on content, external destinations and active browser behavior."""
    if not data or len(data) > 46000 or b"\x00" in data:
        raise ValueError("INTEGRATION_OFFER_BYTES_INVALID")
    page = data.decode("utf-8")
    html = SourceCatalog()
    html.feed(page)
    html.close()
    if html.heading != 1 or html.main != 1 or html.script or html.remote_assets != ["link"] or html.articles:
        raise ValueError("INTEGRATION_OFFER_STRUCTURE")
    if ('<link rel="canonical" href="https://esheenj.github.io/compound-intelligence-starter/integration-reliability.html">' not in page or
            page.count('<link rel="canonical"') != 1 or
            "connect-src 'none'" not in page or "script-src 'none'" not in page or
            "<form" in page.lower() or "<script" in page.lower() or
            "localStorage" in page or "XMLHttpRequest" in page or
            "fetch(" in page or "innerHTML" in page):
        raise ValueError("INTEGRATION_OFFER_SAFETY")
    expected = set()
    for slug in INTEGRATION_TOOL_SLUGS:
        expected.add("https://esheenj.github.io/" + slug + "/")
        expected.add("https://github.com/esheenj/" + slug)
    if not expected.issubset(set(html.links)):
        raise ValueError("INTEGRATION_OFFER_MISSING_TOOL")
    if html.links.count(APPROVED_PILOT_MAILTO) != 1:
        raise ValueError("INTEGRATION_OFFER_EMAIL_ROUTE")
    approved = expected | {APPROVED_PILOT_MAILTO,
        "index.html", "#main", "#tools", "#engineering", "#pilot",
        "https://sigmacode.co.za/",
        "https://github.com/esheenj/compound-intelligence-starter",
        "https://github.com/esheenj/integration-reliability-assessment/issues/new?template=pilot.yml",
    }
    if any(x not in approved for x in html.links):
        raise ValueError("INTEGRATION_OFFER_EXTERNAL_DESTINATION")
    if ("not a booking" not in page or "fictional" not in page or
            "not a security certification" not in page or
            "23 public" in page or "44 demos" in page):
        raise ValueError("INTEGRATION_OFFER_UNSUPPORTED_CLAIM")
    return {"schema": "esheen-integration-offer-v1",
            "state": "SOURCE_VALIDATED",
            "linkedFreeTools": 4, "linkedDeveloperLabs": 2,
            "htmlSha256": hashlib.sha256(data).hexdigest()}


def stage_catalog(output: Path) -> dict:
    root = ROOT.resolve()
    if SOURCE.is_symlink() or not SOURCE.is_file():
        raise ValueError("INVALID_CATALOG_SOURCE")
    # Inspect source parent independently; refuse linked site directory.
    if SOURCE.parent.is_symlink():
        raise ValueError("CATALOG_SOURCE_SYMLINK")
    output = output.resolve(strict=False)
    try:
        relative = output.relative_to(root)
    except ValueError:
        relative = None
    if relative is not None and relative != Path("dist/pages"):
        raise ValueError("DESTINATION_INSIDE_PUBLIC_SOURCE")
    data = SOURCE.read_bytes()
    summary = verify_catalog(data)
    if MVP_WAVE_SOURCE.is_symlink() or MVP_WAVE_SOURCE.parent.is_symlink() or not MVP_WAVE_SOURCE.is_file():
        raise ValueError("MVP_WAVE_SOURCE_INVALID")
    wave = MVP_WAVE_SOURCE.read_bytes()
    if len(wave) > 65536 or b"\x00" in wave:
        raise ValueError("MVP_WAVE_BYTES_INVALID")
    if (b"connect-src 'none'" not in wave or b"default-src 'none'" not in wave or
            wave.count(b"<script>") != 1 or b"<script src" in wave or
            b"innerHTML" in wave or b"XMLHttpRequest" in wave or b"fetch(" in wave):
        raise ValueError("MVP_WAVE_SAFETY_CONTRACT")
    if AGENTOPS_SOURCE.is_symlink() or AGENTOPS_SOURCE.parent.is_symlink() or not AGENTOPS_SOURCE.is_file():
        raise ValueError("AGENTOPS_SOURCE_INVALID")
    agentops = AGENTOPS_SOURCE.read_bytes()
    if (len(agentops) > 65536 or b"\x00" in agentops or
            b"connect-src 'none'" not in agentops or b"default-src 'none'" not in agentops or
            agentops.count(b"<script>") != 1 or b"<script src" in agentops or
            b"innerHTML" in agentops or b"XMLHttpRequest" in agentops or b"fetch(" in agentops):
        raise ValueError("AGENTOPS_SAFETY_CONTRACT")
    if AGENTPROOF_SOURCE.is_symlink() or AGENTPROOF_SOURCE.parent.is_symlink() or not AGENTPROOF_SOURCE.is_file():
        raise ValueError("AGENTPROOF_SOURCE_INVALID")
    agentproof = AGENTPROOF_SOURCE.read_bytes()
    if (len(agentproof) > 65536 or b"\x00" in agentproof or
            b"connect-src 'none'" not in agentproof or b"default-src 'none'" not in agentproof or
            agentproof.count(b"<script>") != 1 or b"<script src" in agentproof or
            b"innerHTML" in agentproof or b"XMLHttpRequest" in agentproof or b"fetch(" in agentproof):
        raise ValueError("AGENTPROOF_SAFETY_CONTRACT")
    if AGENTCREDITS_SOURCE.is_symlink() or AGENTCREDITS_SOURCE.parent.is_symlink() or not AGENTCREDITS_SOURCE.is_file():
        raise ValueError("AGENTCREDITS_SOURCE_INVALID")
    agentcredits = AGENTCREDITS_SOURCE.read_bytes()
    if (len(agentcredits) > 65536 or b"\x00" in agentcredits or
            b"connect-src 'none'" not in agentcredits or b"default-src 'none'" not in agentcredits or
            agentcredits.count(b"<script>") != 1 or b"<script src" in agentcredits or
            b"innerHTML" in agentcredits or b"XMLHttpRequest" in agentcredits or b"fetch(" in agentcredits):
        raise ValueError("AGENTCREDITS_SAFETY_CONTRACT")
    for name, source in (("MODEL_COST", MODEL_COST_SOURCE), ("MODEL_FIT", MODEL_FIT_SOURCE), ("CONTEXT", CONTEXT_SOURCE), ("DISAGREEMENT", DISAGREEMENT_SOURCE), ("DECISION_REVIEW", DECISION_REVIEW_SOURCE), ("AGENT_TRUST", AGENT_TRUST_SOURCE), ("SIGNED_AGENT", SIGNED_AGENT_SOURCE), ("RUNNER_PREFLIGHT", RUNNER_PREFLIGHT_SOURCE)):
        if source.is_symlink() or source.parent.is_symlink() or not source.is_file():
            raise ValueError(name + "_SOURCE_INVALID")
        page_bytes = source.read_bytes()
        if (len(page_bytes) > 65536 or b"\x00" in page_bytes or
                b"connect-src 'none'" not in page_bytes or b"default-src 'none'" not in page_bytes or
                page_bytes.count(b"<script>") != 1 or b"<script src" in page_bytes or
                b"innerHTML" in page_bytes or b"XMLHttpRequest" in page_bytes or b"fetch(" in page_bytes):
            raise ValueError(name + "_SAFETY_CONTRACT")
    model_cost = MODEL_COST_SOURCE.read_bytes()
    model_fit = MODEL_FIT_SOURCE.read_bytes()
    context = CONTEXT_SOURCE.read_bytes()
    disagreement = DISAGREEMENT_SOURCE.read_bytes()
    decision_review = DECISION_REVIEW_SOURCE.read_bytes()
    agent_trust = AGENT_TRUST_SOURCE.read_bytes()
    signed_agent = SIGNED_AGENT_SOURCE.read_bytes()
    runner_preflight = RUNNER_PREFLIGHT_SOURCE.read_bytes()
    if (INTEGRATION_OFFER_SOURCE.is_symlink() or INTEGRATION_OFFER_SOURCE.parent.is_symlink()
            or not INTEGRATION_OFFER_SOURCE.is_file()):
        raise ValueError("INTEGRATION_OFFER_SOURCE_INVALID")
    offer = INTEGRATION_OFFER_SOURCE.read_bytes()
    offer_receipt = verify_integration_offer(offer)
    for source in (ROBOTS_SOURCE, SITEMAP_SOURCE):
        if source.is_symlink() or source.parent.is_symlink() or not source.is_file():
            raise ValueError("PUBLIC_DISCOVERY_SOURCE_INVALID")
    robots = ROBOTS_SOURCE.read_bytes()
    sitemap = SITEMAP_SOURCE.read_bytes()
    discovery_receipt = verify_public_discovery(robots, sitemap)
    support = render_support(load_channels(SUPPORT_CONFIG_SOURCE))
    if output.exists() or output.is_symlink():
        raise ValueError("OUTPUT_EXISTS")
    if not output.parent.exists() or output.parent.is_symlink():
        raise ValueError("OUTPUT_PARENT_MUST_EXIST")
    output.mkdir()
    try:
        (output / "index.html").write_bytes(data)
        (output / "mvp-wave.html").write_bytes(wave)
        (output / "agentops.html").write_bytes(agentops)
        (output / "agentproof.html").write_bytes(agentproof)
        (output / "agentcredits.html").write_bytes(agentcredits)
        (output / "model-cost.html").write_bytes(model_cost)
        (output / "model-fit.html").write_bytes(model_fit)
        (output / "context-preservation.html").write_bytes(context)
        (output / "model-disagreement.html").write_bytes(disagreement)
        (output / "decision-review.html").write_bytes(decision_review)
        (output / "agent-trust.html").write_bytes(agent_trust)
        (output / "signed-agent.html").write_bytes(signed_agent)
        (output / "runner-preflight.html").write_bytes(runner_preflight)
        (output / "support.html").write_bytes(support)
        (output / "integration-reliability.html").write_bytes(offer)
        (output / "robots.txt").write_bytes(robots)
        (output / "sitemap.xml").write_bytes(sitemap)
        (output / ".nojekyll").write_bytes(b"")
        if sorted(p.name for p in output.iterdir()) != [".nojekyll", "agent-trust.html", "agentcredits.html", "agentops.html", "agentproof.html", "context-preservation.html", "decision-review.html", "index.html", "integration-reliability.html", "model-cost.html", "model-disagreement.html", "model-fit.html", "mvp-wave.html", "robots.txt", "runner-preflight.html", "signed-agent.html", "sitemap.xml", "support.html"]:
            raise ValueError("STAGED_UNEXPECTED_FILE")
    except BaseException:
        shutil.rmtree(output)
        raise
    return {
        "schema": "esheen-oss-directory-stage-v1",
        "state": "STAGED_ONLY", "publicHostingVerified": False,
        "files": [".nojekyll", "agent-trust.html", "agentcredits.html", "agentops.html", "agentproof.html", "context-preservation.html", "decision-review.html", "index.html", "integration-reliability.html", "model-cost.html", "model-disagreement.html", "model-fit.html", "mvp-wave.html", "robots.txt", "runner-preflight.html", "signed-agent.html", "sitemap.xml", "support.html"],
        "additionalHostedToolCount": 11,
        "supportPageSha256": hashlib.sha256(support).hexdigest(),
        "integrationOfferSha256": offer_receipt["htmlSha256"],
        "integrationOfferSourceValidated": True,
        "publicDiscoverySitemapSha256": discovery_receipt["sitemapSha256"],
        "publicDiscoveryRobotsSha256": discovery_receipt["robotsSha256"],
        "publicDiscoveryListedPages": discovery_receipt["listedPages"],
        "originRootRobotsAuthority": False,
        "additionalLinkedPublicToolCount": len(EXTRA_TOOL_URLS),
        "mvpWaveSha256": hashlib.sha256(wave).hexdigest(),
        "agentOpsSha256": hashlib.sha256(agentops).hexdigest(),
        "agentProofSha256": hashlib.sha256(agentproof).hexdigest(),
        "agentCreditsSha256": hashlib.sha256(agentcredits).hexdigest(),
        "modelCostSha256": hashlib.sha256(model_cost).hexdigest(),
        "modelFitSha256": hashlib.sha256(model_fit).hexdigest(),
        "contextSha256": hashlib.sha256(context).hexdigest(),
        "modelDisagreementSha256": hashlib.sha256(disagreement).hexdigest(),
        "decisionReviewSha256": hashlib.sha256(decision_review).hexdigest(),
        "agentTrustSha256": hashlib.sha256(agent_trust).hexdigest(),
        "signedAgentSha256": hashlib.sha256(signed_agent).hexdigest(),
        "runnerPreflightSha256": hashlib.sha256(runner_preflight).hexdigest(), **summary
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Offline source-only OSS directory stage")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        receipt = stage_catalog(Path(args.output))
        print(json.dumps(receipt, sort_keys=True))
        return 0
    except (OSError, UnicodeError, ValueError):
        print(json.dumps({"schema": "esheen-oss-directory-stage-v1", "state": "REJECTED"}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
