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

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "site" / "index.html"
MVP_WAVE_SOURCE = ROOT / "site" / "mvp-wave.html"
AGENTOPS_SOURCE = ROOT / "site" / "agentops.html"
AGENTPROOF_SOURCE = ROOT / "site" / "agentproof.html"
AGENTCREDITS_SOURCE = ROOT / "site" / "agentcredits.html"
MODEL_COST_SOURCE = ROOT / "site" / "model-cost.html"
MODEL_FIT_SOURCE = ROOT / "site" / "model-fit.html"
CONTEXT_SOURCE = ROOT / "site" / "context-preservation.html"
DESTINATION = ROOT / "dist" / "pages"
REPOS = {
    "compound-intelligence-starter",
    "design-system-foundations-oss",
    "mobile-first-flow-kit-oss",
    "data-table-interactions-oss",
    "flow-state-machine-oss",
    "form-experience-kit-oss",
    "visual-regression-starter-oss",
}
DEPLOYED_PAGES = {"https://esheenj.github.io/" + repo + "/" for repo in REPOS}
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
    if parser.script or parser.remote_assets or parser.articles != 7 or parser.main != 1 or parser.heading != 1:
        raise ValueError("INVALID_CATALOG_STRUCTURE")
    if "connect-src 'none'" not in html or "script-src 'none'" not in html:
        raise ValueError("CATALOG_CSP_REQUIRED")
    expected_links = set()
    for repo in REPOS:
        base = "https://github.com/esheenj/" + repo
        expected_links.update((base, base + "/issues"))
    observed = set(parser.links)
    if not expected_links.issubset(observed):
        raise ValueError("PUBLIC_REPOSITORY_LINK_MISSING")
    if not EXTRA_TOOL_URLS.issubset(observed) or parser.links.count("mvp-wave.html") != 1 or parser.links.count("agentops.html") != 1 or parser.links.count("agentproof.html") != 1 or parser.links.count("agentcredits.html") != 1 or parser.links.count("model-cost.html") != 1 or parser.links.count("model-fit.html") != 1 or parser.links.count("context-preservation.html") != 1:
        raise ValueError("ADDITIONAL_TOOL_LINK_MISSING")
    for link in parser.links:
        if not (link.startswith("#") or link.startswith("https://github.com/esheenj/") or link in DEPLOYED_PAGES or link in EXTRA_TOOL_URLS or link in {"mvp-wave.html", "agentops.html", "agentproof.html", "agentcredits.html", "model-cost.html", "model-fit.html", "context-preservation.html"}):
            raise ValueError("CATALOG_EXTERNAL_LINK_NOT_ALLOWED")
    # Verify exact source, issues and GitHub-deployed URL on each card.
    # A swapped destination or unrelated host must not be published.
    expected_cards = {
        ("https://github.com/esheenj/" + repo,
         "https://github.com/esheenj/" + repo + "/issues",
         "https://esheenj.github.io/" + repo + "/")
        for repo in REPOS
    }
    if {tuple(card) for card in parser.card_links} != expected_cards or len(parser.card_links) != 7:
        raise ValueError("PUBLIC_CARD_LINK_MISMATCH")
    if "WCAG certified" in html or "commercially adopted" in html:
        raise ValueError("UNSUPPORTED_CATALOG_CLAIM")
    return {"repoCount": 7, "githubDeployedUrlCount": 7,
            "independentBrowserVerified": False,
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
    for name, source in (("MODEL_COST", MODEL_COST_SOURCE), ("MODEL_FIT", MODEL_FIT_SOURCE), ("CONTEXT", CONTEXT_SOURCE)):
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
        (output / ".nojekyll").write_bytes(b"")
        if sorted(p.name for p in output.iterdir()) != [".nojekyll", "agentcredits.html", "agentops.html", "agentproof.html", "context-preservation.html", "index.html", "model-cost.html", "model-fit.html", "mvp-wave.html"]:
            raise ValueError("STAGED_UNEXPECTED_FILE")
    except BaseException:
        shutil.rmtree(output)
        raise
    return {
        "schema": "esheen-oss-directory-stage-v1",
        "state": "STAGED_ONLY", "publicHostingVerified": False,
        "files": [".nojekyll", "agentcredits.html", "agentops.html", "agentproof.html", "context-preservation.html", "index.html", "model-cost.html", "model-fit.html", "mvp-wave.html"],
        "additionalHostedToolCount": 7,
        "additionalLinkedPublicToolCount": len(EXTRA_TOOL_URLS),
        "mvpWaveSha256": hashlib.sha256(wave).hexdigest(),
        "agentOpsSha256": hashlib.sha256(agentops).hexdigest(),
        "agentProofSha256": hashlib.sha256(agentproof).hexdigest(),
        "agentCreditsSha256": hashlib.sha256(agentcredits).hexdigest(),
        "modelCostSha256": hashlib.sha256(model_cost).hexdigest(),
        "modelFitSha256": hashlib.sha256(model_fit).hexdigest(),
        "contextSha256": hashlib.sha256(context).hexdigest(), **summary
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
