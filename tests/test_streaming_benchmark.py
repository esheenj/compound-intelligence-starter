"""Golden and cross-language tests using wholly fictional aggregation records."""
from __future__ import annotations

import shutil
import subprocess
import sys
import unittest
from pathlib import Path

from experiments.streaming_benchmark.generate import generate
from experiments.streaming_benchmark.python_stream import aggregate, parse_record

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / "experiments" / "streaming_benchmark" / "python_stream.py"
RUST = ROOT / "experiments" / "streaming_benchmark" / "rust" / "target" / "release" / "synthetic-stream-aggregator"
GO = ROOT / "experiments" / "streaming_benchmark" / "go" / "stream-aggregator"

FIXTURE = (
    b"E00000001\tatlas\tPASS\t5\n"
    b"E00000002\tatlas\tPASS\t-5\n"
    b"E00000001\tatlas\tPASS\t5\n"
    b"E00000003\tbeacon\tFAIL\t10\n"
    b"E00000004\tdelta\tRETRY\t10001\n"
    b"E00000005\tdelta\tRETRY\t0\n"
    b"E00000006\tcobalt\tPASS\t+5\n"
    b"bad\n"
    b"E00000007\tcobalt\tFAIL\t-0\n"
)
EXPECTED = (
    b"ACCEPTED\t4\nDUPLICATES\t1\nREJECTED\t4\n"
    b"GROUP\tatlas\tPASS\t2\t0\n"
    b"GROUP\tatlas\tFAIL\t0\t0\nGROUP\tatlas\tRETRY\t0\t0\n"
    b"GROUP\tbeacon\tPASS\t0\t0\nGROUP\tbeacon\tFAIL\t1\t10\nGROUP\tbeacon\tRETRY\t0\t0\n"
    b"GROUP\tcobalt\tPASS\t0\t0\nGROUP\tcobalt\tFAIL\t0\t0\nGROUP\tcobalt\tRETRY\t0\t0\n"
    b"GROUP\tdelta\tPASS\t0\t0\nGROUP\tdelta\tFAIL\t0\t0\nGROUP\tdelta\tRETRY\t1\t0\n"
)


def execute(command: list[str], data: bytes) -> bytes:
    return subprocess.run(command, input=data, capture_output=True, timeout=60, check=True).stdout


class StreamingBenchmarkTests(unittest.TestCase):
    def test_golden(self) -> None:
        self.assertEqual(aggregate(FIXTURE.splitlines()), EXPECTED)
        self.assertEqual(execute([sys.executable, str(PYTHON)], FIXTURE), EXPECTED)

    def test_invalid_cases(self) -> None:
        for data in (
            b"E00000001\tatlas\tPASS\t+1",
            b"E00000001\tatlas\tPASS\t01",
            b"E00000001\tatlas\tPASS\t-0",
            b"E00000001\tatlas\tPASS\t10001",
            b"E00000001\tatlas\tPASS\t-10001",
            b"E00000001\tatlas\tPASS\t0\textra",
            b"E00000001\tatlas\tPASS\t0" + b" " * 300,
            b"\xff",
        ):
            self.assertIsNone(parse_record(data))

    def test_generator(self) -> None:
        self.assertEqual(generate(1000), generate(1000))
        self.assertEqual(len(generate(1000).splitlines()), 1000)
        for n in (0, -1, 250001):
            with self.assertRaises(ValueError):
                generate(n)

    @unittest.skipUnless(shutil.which("go"), "Go toolchain unavailable")
    def test_go_parity(self) -> None:
        subprocess.run(["go", "build", "-o", str(GO), str(GO.parent / "main.go")], check=True, timeout=120)
        self.assertEqual(execute([str(GO)], FIXTURE), EXPECTED)
        stream = generate(1000)
        self.assertEqual(execute([str(GO)], stream), execute([sys.executable, str(PYTHON)], stream))

    @unittest.skipUnless(shutil.which("cargo"), "Rust toolchain unavailable locally; mandatory in CI")
    def test_rust_parity(self) -> None:
        manifest = RUST.parents[2] / "Cargo.toml"
        subprocess.run(["cargo", "build", "--release", "--manifest-path", str(manifest)], check=True, timeout=150)
        self.assertEqual(execute([str(RUST)], FIXTURE), EXPECTED)
        stream = generate(1000)
        self.assertEqual(execute([str(RUST)], stream), execute([sys.executable, str(PYTHON)], stream))


if __name__ == "__main__":
    unittest.main()
