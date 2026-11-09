"""Informational Python/Rust batch benchmark for fixed fictional records.

The timing result is not proof of a production speedup or authorization.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path

from experiments.receipt_validator.python_validator import validate_line

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FIXTURE = ROOT / "examples" / "receipt_validator_cases.tsv"
RUST = ROOT / "experiments" / "receipt_validator" / "rust" / "target" / "debug" / "receipt-validator-pilot"
PYTHON = ROOT / "experiments" / "receipt_validator" / "python_validator.py"


def build_stream(fixture: bytes, rows: int) -> tuple[bytes, bytes]:
    if not 1 <= rows <= 1_000_000:
        raise ValueError("rows outside bounded benchmark range")
    source = fixture.splitlines()
    if not source or any(not item for item in source):
        raise ValueError("fixture must contain nonempty lines")
    labels = []
    for item in source:
        try:
            labels.append(b"VALID\n" if validate_line(item.decode("utf-8")) else b"INVALID\n")
        except UnicodeDecodeError as exc:
            raise ValueError("fixture must be UTF-8") from exc
    repeats, remainder = divmod(rows, len(source))
    data = (b"\n".join(source) + b"\n") * repeats + b"".join(item + b"\n" for item in source[:remainder])
    expected = b"".join(labels) * repeats + b"".join(labels[:remainder])
    return data, expected


def measure(command: list[str], data: bytes, expected: bytes) -> float:
    started = time.perf_counter_ns()
    result = subprocess.run(command, input=data, capture_output=True, check=True, timeout=90)
    elapsed = (time.perf_counter_ns() - started) / 1_000_000
    if result.stdout != expected:
        raise RuntimeError("Validator output differed from the fixed expected result")
    return elapsed


def percentile_95(values: list[float]) -> float:
    return sorted(values)[math.ceil(0.95 * len(values)) - 1]


def run_benchmark(rust_binary: Path, fixture_path: Path, rows: int, trials: int) -> dict:
    if not 2 <= trials <= 15:
        raise ValueError("trials outside bounded benchmark range")
    if not rust_binary.is_file():
        raise FileNotFoundError(f"Rust binary missing: {rust_binary}")
    fixture = fixture_path.read_bytes()
    data, expected = build_stream(fixture, rows)
    commands = {"python": [sys.executable, str(PYTHON)], "rust": [str(rust_binary)]}
    warmup_data, warmup_expected = build_stream(fixture, min(rows, 1000))
    for command in commands.values():
        measure(command, warmup_data, warmup_expected)
    samples = {"python": [], "rust": []}
    for i in range(trials):
        for name in (("python", "rust") if i % 2 == 0 else ("rust", "python")):
            samples[name].append(round(measure(commands[name], data, expected), 3))
    results = {}
    for name, values in samples.items():
        median = statistics.median(values)
        results[name] = {
            "batch_times_ms": values,
            "median_batch_ms": round(median, 3),
            "nearest_rank_p95_batch_ms": round(percentile_95(values), 3),
            "rows_per_second_at_median": round(rows * 1000 / median, 1),
        }
    return {
        "schema": "synthetic-cross-language-benchmark-v1",
        "interpretation": "informational; not a guaranteed speedup or production benchmark",
        "fixture_sha256": hashlib.sha256(fixture).hexdigest(),
        "input_sha256": hashlib.sha256(data).hexdigest(),
        "rows": rows,
        "trials": trials,
        "platform": platform.platform(),
        "architecture": platform.machine(),
        "python_version": platform.python_version(),
        "ci_checkout_sha": os.environ.get("GITHUB_SHA", "local-unpinned"),
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--rust-binary", type=Path, default=RUST)
    parser.add_argument("--rows", type=int, default=100_000)
    parser.add_argument("--trials", type=int, default=5)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run_benchmark(args.rust_binary, args.fixture, args.rows, args.trials)
    message = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(message, encoding="utf-8")
    print(message, end="")


if __name__ == "__main__":
    main()
