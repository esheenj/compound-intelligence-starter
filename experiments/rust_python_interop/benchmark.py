"""Reproducible, informative same-process Python/PyO3 timing; no performance gate."""

import argparse
import hashlib
import json
import math
import platform
import random
import statistics
import time

from reference import classify_ids as python_classify
from rust_ids import classify_ids as rust_classify


def benchmark(size=50_000, trials=7):
    if not 1 <= size <= 100_000 or not 3 <= trials <= 15:
        raise ValueError("size must be 1..100000 and trials 3..15")
    rng = random.Random(20261115)
    values = []
    for index in range(size):
        item = f"id-{rng.randrange(9000):04d}"
        if index % 17 == 0:
            item = "bad value"
        values.append(item)

    payload = json.dumps(values, separators=(",", ":"), ensure_ascii=True).encode()
    expected = python_classify(values)
    if rust_classify(values) != expected:
        raise RuntimeError("native result differs from Python baseline")

    for _ in range(3):
        python_classify(values)
        rust_classify(values)

    measurements = {"python": [], "rust": []}
    for i in range(trials):
        # Alternate invocation order to reduce systematic first-call advantage.
        order = ("python", "rust") if i % 2 else ("rust", "python")
        for name in order:
            fn = python_classify if name == "python" else rust_classify
            before = time.perf_counter_ns()
            result = fn(values)
            elapsed = time.perf_counter_ns() - before
            if result != expected:
                raise RuntimeError(f"{name} result changed during benchmark")
            measurements[name].append(elapsed / 1_000_000)

    def stats(samples):
        ordered = sorted(samples)
        return {
            "median_ms": round(statistics.median(ordered), 3),
            "p95_ms": round(ordered[math.ceil(0.95 * len(ordered)) - 1], 3),
        }

    python_stats = stats(measurements["python"])
    rust_stats = stats(measurements["rust"])
    return {
        "schema": "rust-python-interop-benchmark-v1",
        "qualification_only": True,
        "workload": "synthetic bounded ID classification",
        "records": size,
        "trials": trials,
        "input_sha256": hashlib.sha256(payload).hexdigest(),
        "architecture": platform.machine(),
        "python_version": platform.python_version(),
        "counts": expected,
        "python": python_stats,
        "rust": rust_stats,
        "relative_python_over_rust_median": round(
            python_stats["median_ms"] / rust_stats["median_ms"], 3
        ),
        "limits": "Single shared process, synthetic data; no peak-RSS, wheel-install overhead, model quality, or production throughput claim",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--size", type=int, default=50_000)
    parser.add_argument("--trials", type=int, default=7)
    args = parser.parse_args()
    print(json.dumps(benchmark(args.size, args.trials), sort_keys=True))
