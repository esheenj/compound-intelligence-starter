"""Consumer tests against the existing public issue-challenger contract."""
import copy
import unittest

from consumer_probe import assess, fixture, probe
from reference import classify_ids as python_classify
from rust_ids import classify_ids as native_classify
from src.compound_intelligence.issue_challenger import validate


class ConsumerQualificationTests(unittest.TestCase):
    def test_existing_public_consumer_unchanged(self):
        document = fixture(2)
        self.assertEqual(assess(document, native_classify), assess(document, python_classify))

    def test_bounded_maximum_consumer(self):
        document = fixture(12)
        result = assess(document, native_classify)
        self.assertEqual(result["issues"], 12)
        self.assertEqual(result["hypotheses"], 24)
        self.assertTrue(result["python_validation_retained"])
        self.assertFalse(result["external_execution"])

    def test_reject_untrusted_id_before_native_supplement(self):
        doc = fixture(2)
        doc["issues"][0]["id"] = "1bad"  # Rust allows this; real consumer disallows it.
        with self.assertRaises(ValueError):
            validate(doc)
        with self.assertRaises(ValueError):
            assess(doc, native_classify)

    def test_scope_hypotheses_per_issue_not_globally_deduplicated(self):
        # The original consumer permits the same hypothesis ID on different issues.
        document = fixture(12)
        self.assertEqual(assess(document, native_classify), assess(document, python_classify))

    def test_fallback_with_native_unavailable(self):
        document = fixture(12)
        self.assertEqual(assess(document), assess(document, native_classify))

    def test_invalid_count_held(self):
        for invalid in (0, 13):
            with self.assertRaises(ValueError):
                fixture(invalid)
        for invalid in (0, 2001):
            with self.assertRaises(ValueError):
                probe("python", 2, invalid)

    def test_native_consumer_actual_sample(self):
        report = probe("rust", 2, 1)
        self.assertEqual(report["schema"], "issue-challenger-native-consumer-probe-v1")
        self.assertTrue(report["consumer_result"]["python_validation_retained"])


if __name__ == "__main__":
    unittest.main()
