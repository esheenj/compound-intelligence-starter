"""Read-only exact-source public sitemap verification after the existing Pages release.

Publishing a project path robots.txt is not evidence of root robots.txt ownership,
search-engine sitemap submission, indexing, ranking, traffic or lead conversions.
"""
from __future__ import annotations
import hashlib
import json
import time
import urllib.error
import urllib.request
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.public_discovery import (
    PUBLIC_LOCATIONS, PUBLIC_PREFIX, SITEMAP_URL,
    build_robots,build_sitemap,verify_public_discovery,
)

def get_http(url,limit=150000,timeout=12):
    if not url.startswith(PUBLIC_PREFIX):
        raise AssertionError("URL_NOT_IN_OWN_PROJECT")
    req=urllib.request.Request(url,headers={
        "User-Agent":"Esheen-Labs-ReadOnly-Public-Discovery-Acceptance",
        "Accept":"*/*",
    })
    with urllib.request.urlopen(req,timeout=timeout) as response:
        if response.status!=200 or not response.url.startswith(PUBLIC_PREFIX):
            raise AssertionError("PAGE_ORIGIN_OR_STATUS")
        body=response.read(limit+1)
        if len(body)>limit:
            raise AssertionError("UNEXPECTED_LARGE_PUBLIC_PAGE")
        return body

def run():
    expected_robots=build_robots()
    expected_sitemap=build_sitemap()
    source=verify_public_discovery(expected_robots,expected_sitemap)
    robots_url=PUBLIC_PREFIX+"robots.txt"
    for attempt in range(26):
        try:
            online_sitemap=get_http(SITEMAP_URL,limit=16000)
            online_robots=get_http(robots_url,limit=5000)
        except (urllib.error.URLError,TimeoutError,OSError,AssertionError):
            if attempt==25:raise
            time.sleep(.7)
            continue
        if (online_sitemap==expected_sitemap and
                online_robots==expected_robots):
            break
        if attempt==25:
            raise AssertionError("PUBLISHED_SITEMAP_OR_ROBOTS_SOURCE_MISMATCH")
        time.sleep(.7)
    if hashlib.sha256(online_sitemap).hexdigest()!=source["sitemapSha256"]:
        raise AssertionError("SITEMAP_HASH_INCONSISTENT")
    if hashlib.sha256(online_robots).hexdigest()!=source["robotsSha256"]:
        raise AssertionError("ROBOTS_HASH_INCONSISTENT")
    checked=[]
    for url in PUBLIC_LOCATIONS:
        body=get_http(url,limit=180000)
        if not body.lower().startswith(b"<!doctype html"):
            raise AssertionError("LISTED_NON_HTML_PAGE_"+url)
        checked.append(url)
    index=get_http(PUBLIC_PREFIX,limit=180000)
    if (b'<link rel="canonical" href="'+PUBLIC_PREFIX.encode()+b'">' not in index or
            index.count(b'href="sitemap.xml"')!=1):
        raise AssertionError("HOMEPAGE_CANONICAL_SITEMAP_LINK_MISSING")
    return {
        "schema":"esheen-public-discovery-live-v1",
        "state":"PASS",
        "publishedProjectSitemap":SITEMAP_URL,
        "listedAndRetrievedHttpsPages":len(checked),
        "sitemapSha256":source["sitemapSha256"],
        "robotsSha256":source["robotsSha256"],
        "sourceBytesMatchLive":True,
        "originRootRobotsAuthority":False,
        "searchConsoleSubmitted":False,
        "indexingVerified":False,
        "trafficOrLeadConversionVerified":False,
        "scope":"15 approved project pages; no impact on esheenj.github.io origin-root robots.txt or other repositories."
    }

if __name__=="__main__":
    try:print(json.dumps(run(),sort_keys=True))
    except (AssertionError,ValueError,OSError,TimeoutError) as exc:
        print(json.dumps({"schema":"esheen-public-discovery-live-v1","state":"FAIL",
                          "error":str(exc)[:170]},sort_keys=True))
        raise SystemExit(1)
