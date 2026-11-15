"""Static SEO discovery artifact checks, without inventing search engine indexing."""
import hashlib
import tempfile
import unittest
from pathlib import Path
import xml.etree.ElementTree as ET

from scripts.public_discovery import (
    ROOT, SITE_ROOT, PUBLIC_LOCATIONS, PUBLIC_PREFIX,
    PUBLISHED_HTML_PAGES, SITEMAP_URL,
    build_robots, build_sitemap, verify_public_discovery,
)
from scripts.stage_showcase import (
    ROBOTS_SOURCE, SITEMAP_SOURCE, SOURCE, stage_catalog, verify_catalog,
)

class PublicDiscoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.robots=ROBOTS_SOURCE.read_bytes()
        cls.sitemap=SITEMAP_SOURCE.read_bytes()

    def test_exact_static_robots_bytes(self):
        self.assertEqual(self.robots,build_robots())
        self.assertIn(b"User-agent: *\n",self.robots)
        self.assertIn(SITEMAP_URL.encode(),self.robots)

    def test_sitemap_exact_xml_vocabulary(self):
        root=ET.fromstring(self.sitemap)
        self.assertEqual(root.tag,"{http://www.sitemaps.org/schemas/sitemap/0.9}urlset")
        self.assertEqual(self.sitemap,build_sitemap())

    def test_sitemap_lists_all_fifteen_existing_pages(self):
        self.assertEqual(len(PUBLISHED_HTML_PAGES),15)
        self.assertEqual(len(PUBLIC_LOCATIONS),15)
        report=verify_public_discovery(self.robots,self.sitemap)
        self.assertEqual(report["listedPages"],15)
        self.assertEqual(len(set(PUBLIC_LOCATIONS)),15)
        self.assertTrue(all(x.startswith(PUBLIC_PREFIX) for x in PUBLIC_LOCATIONS))
        self.assertIn(PUBLIC_PREFIX+"integration-reliability.html",PUBLIC_LOCATIONS)

    def test_main_site_canonical_and_share_metadata(self):
        data=SOURCE.read_text()
        self.assertEqual(data.count('<link rel="canonical" href="'+PUBLIC_PREFIX+'">'),1)
        self.assertIn('<meta property="og:description"',data)
        self.assertIn('<meta property="og:url" content="'+PUBLIC_PREFIX+'">',data)
        self.assertEqual(data.count('href="sitemap.xml"'),1)
        catalog=verify_catalog(data.encode())
        self.assertEqual(catalog["repoCount"],22)

    def test_no_unpublished_or_external_project_pages(self):
        self.assertFalse(any("sigmacode.co.za" in x for x in PUBLIC_LOCATIONS))
        self.assertFalse(any("/integration-delivery-trace-inspector/" in x for x in PUBLIC_LOCATIONS))
        self.assertTrue(all(x=="index.html" or (SITE_ROOT/x).is_file() or x=="support.html"
                            for x in PUBLISHED_HTML_PAGES))

    def test_origin_root_robots_not_claimed(self):
        report=verify_public_discovery(self.robots,self.sitemap)
        self.assertFalse(report["originRootRobotsAuthority"])
        # This is /compound-intelligence-starter/robots.txt, not /robots.txt.
        self.assertIn("/compound-intelligence-starter/sitemap.xml",report["projectSitemapUrl"])

    def test_static_assets_are_only_reviewed_urls(self):
        bad=self.sitemap.replace(
            b"https://esheenj.github.io/compound-intelligence-starter/integration-reliability.html",
            b"https://unexpected.example.invalid/")
        with self.assertRaisesRegex(ValueError,"SOURCE_NOT_REVIEWED"):
            verify_public_discovery(self.robots,bad)

    def test_reject_unreviewed_robots_crawl_policy(self):
        with self.assertRaisesRegex(ValueError,"SOURCE_NOT_REVIEWED"):
            verify_public_discovery(self.robots.replace(b"Allow: /\n",b"Disallow: /\n"),
                                    self.sitemap)

    def test_reject_duplicates_in_sitemap(self):
        changed=self.sitemap.replace(
            b"<loc>"+PUBLIC_LOCATIONS[1].encode()+b"</loc>",
            b"<loc>"+PUBLIC_LOCATIONS[0].encode()+b"</loc>")
        with self.assertRaises(ValueError):
            verify_public_discovery(self.robots,changed)

    def test_staged_exact_bytes_and_receipts(self):
        with tempfile.TemporaryDirectory() as t:
            dst=Path(t)/"pages"
            report=stage_catalog(dst)
            self.assertEqual(report["publicDiscoveryListedPages"],15)
            self.assertFalse(report["originRootRobotsAuthority"])
            for source,name,receipt in (
                (ROBOTS_SOURCE,"robots.txt","publicDiscoveryRobotsSha256"),
                (SITEMAP_SOURCE,"sitemap.xml","publicDiscoverySitemapSha256"),
            ):
                data=(dst/name).read_bytes()
                self.assertEqual(data,source.read_bytes())
                self.assertEqual(hashlib.sha256(data).hexdigest(),report[receipt])
            self.assertEqual(report["repoCount"],22)
            self.assertEqual(report["githubDeployedUrlCount"],22)
            self.assertEqual(report["additionalHostedToolCount"],11)

    def test_noindex_page_is_disallowed(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as t:
            tmp=Path(t)
            for name in PUBLISHED_HTML_PAGES:
                if name!="support.html":
                    (tmp/name).write_text("<!doctype html><title>Fictional</title>")
            (tmp/"index.html").write_text("<meta name='robots' content='noindex'>")
            with patch("scripts.public_discovery.SITE_ROOT",tmp):
                with self.assertRaisesRegex(ValueError,"NOINDEX_index.html"):
                    verify_public_discovery(self.robots,self.sitemap)

    def test_sitemap_does_not_assume_indexing_or_lastmod(self):
        for disallowed in (b"<lastmod>",b"<priority>",b"<changefreq>"):
            self.assertNotIn(disallowed,self.sitemap)

if __name__=="__main__":
    unittest.main()
