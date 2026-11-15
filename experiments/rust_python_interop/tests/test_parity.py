"""Cross-language tests: run after wheel install; cannot pass without Rust module."""

import unittest
from reference import classify_ids as python_classify
from rust_ids import classify_ids as rust_classify


class CrossLanguageParity(unittest.TestCase):
    def assert_parity(self, values):
        self.assertEqual(rust_classify(values), python_classify(values))

    def test_empty(self):
        self.assert_parity([])

    def test_duplicates_and_rejections(self):
        self.assert_parity(["a", "b", "a", "A", "_", "a-b", "c1", ""])

    def test_utf8_ascii_boundary(self):
        self.assert_parity(["x" * 64, "x" * 65, "é", "x" * 64])

    def test_empty_and_dash(self):
        self.assert_parity(["", "-", "_", "9", "abc", "ab c", "ABC", "hello-world"])

    def test_repeatability(self):
        values = ["ok", "ok", "invalid space", "a_b", "", "é"]
        self.assertEqual(rust_classify(values), rust_classify(values))
        self.assert_parity(values)

    def test_limit_count(self):
        values = ["a"] * 200_001
        with self.assertRaises(ValueError):
            rust_classify(values)
        with self.assertRaises(ValueError):
            python_classify(values)

    def test_limit_bytes(self):
        values = ["x" * 64] * 125_001
        with self.assertRaises(ValueError):
            rust_classify(values)
        with self.assertRaises(ValueError):
            python_classify(values)

    def test_invalid_member_type(self):
        for fn in (python_classify, rust_classify):
            with self.assertRaises(TypeError):
                fn(["a", 3])

    def test_tuple_input(self):
        self.assert_parity(("a", "a", "abc", "é"))

    def test_deterministic_seeded_batches(self):
        import random

        rng = random.Random(20261115)
        alphabet = "abcdefghijklmnopqrstuvwxyz0123456789_-é À"
        for size in (1, 9, 1024, 5000):
            values = [
                "".join(rng.choice(alphabet) for _ in range(rng.randrange(0, 67)))
                for _ in range(size)
            ]
            self.assert_parity(values)


if __name__ == "__main__":
    unittest.main()
