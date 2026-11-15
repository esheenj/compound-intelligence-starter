"""Exact, deterministic GitHub Pages project discovery artifacts.

All URLs are public static pages deployed by this repository's guarded Pages workflow.
The project-scoped robots.txt cannot replace the origin-root robots.txt on GitHub Pages.
"""
from __future__ import annotations

from pathlib import Path
import hashlib
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
SITE_ROOT=ROOT/"site"
PUBLIC_ORIGIN="https://esheenj.github.io"
PUBLIC_PREFIX=PUBLIC_ORIGIN+"/compound-intelligence-starter/"
SITEMAP_NAMESPACE="http://www.sitemaps.org/schemas/sitemap/0.9"

# Stable reviewed pages only. Neither the 22 external projects nor unpublished
# directories are falsely claimed as hosted by this project.
PUBLISHED_HTML_PAGES=(
    "index.html",
    "integration-reliability.html",
    "agent-trust.html",
    "agentcredits.html",
    "agentops.html",
    "agentproof.html",
    "context-preservation.html",
    "decision-review.html",
    "model-cost.html",
    "model-disagreement.html",
    "model-fit.html",
    "mvp-wave.html",
    "runner-preflight.html",
    "signed-agent.html",
    "support.html",
)
PUBLIC_LOCATIONS=tuple(
    PUBLIC_PREFIX if p=="index.html" else PUBLIC_PREFIX+p
    for p in PUBLISHED_HTML_PAGES
)
SITEMAP_URL=PUBLIC_PREFIX+"sitemap.xml"

def build_robots()->bytes:
    # Project-file publication is for transparency/manual discovery.
    # Crawlers usually fetch robots.txt at the ORIGIN ROOT, not project subpaths.
    return ("User-agent: *\n"
            "Allow: /\n"
            "Sitemap: "+SITEMAP_URL+"\n").encode("ascii")

def build_sitemap()->bytes:
    ET.register_namespace("",SITEMAP_NAMESPACE)
    root=ET.Element(f"{{{SITEMAP_NAMESPACE}}}urlset")
    for loc in PUBLIC_LOCATIONS:
        u=ET.SubElement(root,f"{{{SITEMAP_NAMESPACE}}}url")
        ET.SubElement(u,f"{{{SITEMAP_NAMESPACE}}}loc").text=loc
    ET.indent(root,space="  ")
    return ET.tostring(root,encoding="utf-8",xml_declaration=True)+b"\n"

def verify_public_discovery(robots:bytes,sitemap:bytes)->dict:
    if robots!=build_robots() or sitemap!=build_sitemap():
        raise ValueError("PUBLIC_DISCOVERY_SOURCE_NOT_REVIEWED")
    root=ET.fromstring(sitemap)
    if root.tag!=f"{{{SITEMAP_NAMESPACE}}}urlset":
        raise ValueError("PUBLIC_DISCOVERY_SITEMAP_STRUCTURE")
    locs=[u.findtext(f"{{{SITEMAP_NAMESPACE}}}loc") for u in root]
    if tuple(locs)!=PUBLIC_LOCATIONS or len(set(locs))!=len(locs):
        raise ValueError("PUBLIC_DISCOVERY_SITEMAP_URLS")
    for name in PUBLISHED_HTML_PAGES:
        # The support page is safely generated from a reviewed configuration.
        if name=="support.html":
            continue
        path=SITE_ROOT/name
        if path.is_symlink() or not path.is_file():
            raise ValueError("PUBLIC_DISCOVERY_HTML_MISSING_"+name)
        if b"noindex" in path.read_bytes().lower():
            raise ValueError("PUBLIC_DISCOVERY_NOINDEX_"+name)
    return {
        "schema":"esheen-public-discovery-v1",
        "state":"REVIEWED_SOURCE_ONLY",
        "projectSitemapUrl":SITEMAP_URL,
        "listedPages":len(locs),
        "originRootRobotsAuthority":False,
        "robotsSha256":hashlib.sha256(robots).hexdigest(),
        "sitemapSha256":hashlib.sha256(sitemap).hexdigest(),
    }

def main():
    robots=build_robots()
    sitemap=build_sitemap()
    verify_public_discovery(robots,sitemap)
    (SITE_ROOT/"robots.txt").write_bytes(robots)
    (SITE_ROOT/"sitemap.xml").write_bytes(sitemap)
    print("Generated reviewed static public discovery assets:",
          len(PUBLIC_LOCATIONS),"existing pages.")

if __name__=="__main__":
    main()
