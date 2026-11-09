"""Tests for benchmark reproducibility and output validation."""
from __future__ import annotations

import sys
import unittest

from experiments.receipt_validator.benchmark import (
    PYTHON, build_stream, measure, percentile_95,
)


class BenchmarkTests(unittest.TestCase):
    def test_deterministic_stream(self) -> None:
        fixture = b"x\tACCEPTED\t" + b"0" * 64 + b"\n" + b"oops\n"
        stream, expected = build_stream(fixture, 5)
        self.assertEqual(stream.count(b"\n"), 5)
        self.assertEqual(expected, b"VALID\nINVALID\nVALID\nINVALID\nVALID\n")
        self.assertEqual(build_stream(fixture, 5), (stream, expected))

    def test_rejects_unbounded_work(self) -> None:
        for n in (0, 1_000_001):
            with self.assertRaises(ValueError):
                build_stream(b"x\n", n)

    def test_process_output_is_checked(self) -> None:
        data = b"abc\tACCEPTED\t" + b"0" * 64 + b"\n"
        self.assertGreaterEqual(measure([sys.executable, str(PYTHON)], data, b"VALID\n"), 0)
        with self.assertRaises(RuntimeError):
            measure([sys.executable, str(PYTHON)], data, b"INVALID\n")

    def test_nearest_rank_percentile(self) -> None:
        self.assertEqual(percentile_95([1.0, 2.0, 3.0, 4.0, 5.0]), 5.0)


if __name__ == "__main__":
    unittest.main()
