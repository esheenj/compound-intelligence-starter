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


class SourceCatalog(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.articles = 0
        self.heading = 0
        self.main = 0
        self.links = []
        self.script = False
        self.remote_assets = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "article" and "card" in attrs.get("class", "").split():
            self.articles += 1
        if tag == "h1":
            self.heading += 1
        if tag == "main":
            self.main += 1
        if tag == "script":
            self.script = True
        if tag in ("img", "iframe", "link", "audio", "video", "source", "object"):
            self.remote_assets.append(tag)
        if tag == "a":
            self.links.append(attrs.get("href", ""))


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
    for link in parser.links:
        if not (link.startswith("#") or link.startswith("https://github.com/esheenj/")):
            raise ValueError("CATALOG_EXTERNAL_LINK_NOT_ALLOWED")
    if "public Github Pages live" in html or "WCAG certified" in html:
        raise ValueError("UNSUPPORTED_CATALOG_CLAIM")
    return {"repoCount": 7, "htmlSha256": hashlib.sha256(data).hexdigest()}


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
    if output.exists() or output.is_symlink():
        raise ValueError("OUTPUT_EXISTS")
    if not output.parent.exists() or output.parent.is_symlink():
        raise ValueError("OUTPUT_PARENT_MUST_EXIST")
    output.mkdir()
    try:
        (output / "index.html").write_bytes(data)
        (output / ".nojekyll").write_bytes(b"")
        if sorted(p.name for p in output.iterdir()) != [".nojekyll", "index.html"]:
            raise ValueError("STAGED_UNEXPECTED_FILE")
    except BaseException:
        shutil.rmtree(output)
        raise
    return {
        "schema": "esheen-oss-directory-stage-v1",
        "state": "STAGED_ONLY", "publicHostingVerified": False,
        "files": [".nojekyll", "index.html"], **summary
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
