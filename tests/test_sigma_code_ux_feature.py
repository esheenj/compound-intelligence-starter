"""Guard the public Sigma Code Sites embed against accidental site/runtime claims."""
from html.parser import HTMLParser
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "SIGMA_CODE_UX_FEATURE_EMBED.html"


class FeatureParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.links = []
        self.sections = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags.append(tag)
        if tag == "a":
            self.links.append(attrs.get("href", ""))
        if tag == "section":
            self.sections.append(attrs)


class SigmaCodeUXFeatureTests(unittest.TestCase):
    def test_bounded_static_embed_and_two_expected_destinations(self):
        data = SOURCE.read_text(encoding="utf-8")
        self.assertLess(len(data.encode("utf-8")), 16_000)
        self.assertTrue(data.startswith("<style>"))
        self.assertTrue(data.rstrip().endswith("</section>"))
        parser = FeatureParser()
        parser.feed(data)
        parser.close()
        for forbidden in ("script", "iframe", "form", "img", "link", "meta", "html", "body", "input"):
            self.assertNotIn(forbidden, parser.tags)
        self.assertEqual(parser.tags.count("style"), 1)
        self.assertEqual(parser.tags.count("section"), 1)
        self.assertEqual(parser.tags.count("h2"), 1)
        self.assertEqual(parser.tags.count("li"), 4)
        self.assertEqual(len(parser.sections), 1)
        self.assertEqual(parser.sections[0].get("id"), "sigma-code-ux-engineering")
        self.assertEqual(parser.sections[0].get("aria-labelledby"), "scux-heading")
        self.assertEqual(parser.links, [
            "https://esheenj.github.io/compound-intelligence-starter/#ux-case-study",
            "mailto:info@sigmacode.co.za?subject=UX%20Engineering%20Enquiry",
        ])

    def test_scope_and_accessibility_cues(self):
        data = SOURCE.read_text(encoding="utf-8")
        for required in (
            "#sigma-code-ux-engineering",
            "scux-cta:focus-visible",
            "@media (max-width: 900px)",
            "@media (max-width: 520px)",
            "prefers-reduced-motion: reduce",
            "Fictional business scenario",
            "not a live CRM integration",
            "Project scope and pricing are agreed separately",
        ):
            # The focus selector carries the scoped element ID in the source.
            if required == "scux-cta:focus-visible":
                self.assertIn("a:focus-visible", data)
            else:
                self.assertIn(required, data)
        self.assertNotIn("@import", data)
        self.assertNotIn("https://fonts", data)
        self.assertNotIn("<script", data.lower())


if __name__ == "__main__":
    unittest.main()
