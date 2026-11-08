"""Source-only public directory staging must be deterministic and safe."""
import hashlib
import tempfile
import unittest
from pathlib import Path

from scripts.stage_showcase import SOURCE, stage_catalog, verify_catalog


class ShowcaseStageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.output = self.root / "pages"

    def test_exact_public_collection_stage_and_receipt(self):
        report = stage_catalog(self.output)
        self.assertEqual(report["state"], "STAGED_ONLY")
        self.assertEqual(report["repoCount"], 7)
        self.assertFalse(report["publicHostingVerified"])
        self.assertEqual(report["files"], [".nojekyll", "index.html"])
        content = self.output.joinpath("index.html").read_bytes()
        self.assertEqual(content, SOURCE.read_bytes())
        self.assertEqual(report["htmlSha256"], hashlib.sha256(content).hexdigest())
        self.assertEqual(sorted(x.name for x in self.output.iterdir()), [".nojekyll", "index.html"])
        self.assertNotIn(b"<script", content)
        self.assertNotIn(b"<img", content)
        self.assertNotIn(b"https://esheenj.github.io/", content)

    def test_repeated_stage_never_overwrites(self):
        stage_catalog(self.output)
        first = (self.output / "index.html").read_bytes()
        with self.assertRaisesRegex(ValueError, "OUTPUT_EXISTS"):
            stage_catalog(self.output)
        self.assertEqual((self.output / "index.html").read_bytes(), first)

    def test_source_html_needs_all_seven_public_repo_links(self):
        source = SOURCE.read_bytes()
        self.assertEqual(verify_catalog(source)["repoCount"], 7)
        with self.assertRaisesRegex(ValueError, "PUBLIC_REPOSITORY_LINK_MISSING"):
            verify_catalog(source.replace(b"visual-regression-starter-oss", b"broken-repo-name"))
        with self.assertRaisesRegex(ValueError, "CATALOG_EXTERNAL_LINK_NOT_ALLOWED"):
            verify_catalog(source.replace(b'href="#projects"', b'href="https://example.invalid/projects"'))
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
