"""Bounded, informational same-host language comparison on synthetic events."""
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

from experiments.streaming_benchmark.generate import generate
from experiments.streaming_benchmark.python_stream import aggregate

ROOT = Path(__file__).resolve().parents[2]
PYTHON = ROOT / "experiments" / "streaming_benchmark" / "python_stream.py"
RUST = ROOT / "experiments" / "streaming_benchmark" / "rust" / "target" / "release" / "synthetic-stream-aggregator"
GO = ROOT / "experiments" / "streaming_benchmark" / "go" / "stream-aggregator"


def measure(command: list[str], data: bytes, expected: bytes) -> float:
    start = time.perf_counter_ns()
    result = subprocess.run(command, input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=90)
    elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000
    if result.stdout != expected:
        raise RuntimeError(f"{command[0]} yielded inconsistent aggregation")
    return elapsed_ms


def compare(rows: int, trials: int) -> dict:
    if not 100 <= rows <= 250_000:
        raise ValueError("rows outside 100..250000")
    if not 3 <= trials <= 9:
        raise ValueError("trials outside 3..9")
    if not RUST.is_file() or not GO.is_file():
        raise FileNotFoundError("Build Rust release and Go binaries before benchmarking")
    data = generate(rows)
    expected = aggregate(data.splitlines())
    commands = {"python": [sys.executable, str(PYTHON)], "rust": [str(RUST)], "go": [str(GO)]}
    warm = generate(500)
    warm_expected = aggregate(warm.splitlines())
    for cmd in commands.values():
        measure(cmd, warm, warm_expected)
    names = list(commands)
    samples = {name: [] for name in names}
    for index in range(trials):
        ordered = names[index % 3:] + names[:index % 3]
        if index % 2:
            ordered.reverse()
        for name in ordered:
            samples[name].append(round(measure(commands[name], data, expected), 3))
    results = {}
    for name, values in samples.items():
        median = statistics.median(values)
        results[name] = {
            "batch_ms": values,
            "median_batch_ms": round(median, 3),
            "p95_batch_ms_nearest_rank": round(sorted(values)[math.ceil(.95 * len(values)) - 1], 3),
            "rows_per_sec_at_median": round(rows * 1000 / median, 1),
        }
    return {
        "schema": "original-synthetic-stream-compare-v1",
        "limitations": "Single CI runner, synthetic data; not memory, CPU-only or production throughput",
        "source_commit": os.environ.get("GITHUB_SHA", "LOCAL_UNPINNED"),
        "runner_label": os.environ.get("RUNNER_LABEL", "local"),
        "arch": platform.machine(),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "rows": rows,
        "trials": trials,
        "input_sha256": hashlib.sha256(data).hexdigest(),
        "expected_output_sha256": hashlib.sha256(expected).hexdigest(),
        "results": results,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=100_000)
    parser.add_argument("--trials", type=int, default=5)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = json.dumps(compare(args.rows, args.trials), indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result, encoding="utf-8")
    print(result, end="")
