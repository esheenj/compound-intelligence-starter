"""Real public Engineering Issue Challenger consumer qualification.

This is a read-only *supplement* to the existing authoritative Python
validation/planning path. It never changes validation, release authority, or
production behavior. Runs against original public synthetic example data.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import resource
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.compound_intelligence.issue_challenger import plan, validate
from reference import classify_ids as python_classify

FIXTURE = REPO_ROOT / "examples" / "engineering_issues.json"
SCHEMA = "issue-challenger-native-consumer-probe-v1"


def fixture(issue_count: int) -> dict:
    """Clone the existing fictional public example into a bounded consumer load."""
    if not 1 <= issue_count <= 12:
        raise ValueError("issue_count must be between 1 and 12")
    original = json.loads(FIXTURE.read_text(encoding="utf-8"))
    issues = []
    for index in range(issue_count):
        issue = copy.deepcopy(original["issues"][index % len(original["issues"])])
        issue["id"] = f"item-{index:02d}"
        issues.append(issue)
    result = {"version": 1, "issues": issues}
    validate(result)
    return result


def assess(document: dict, classifier=python_classify) -> dict:
    """Run the unmodified Python consumer, then test optional native-ID parity."""
    issues = validate(document)  # Never delegate security/schema validation.
    report = plan(document)
    issue_ids = [issue["id"] for issue in issues]
    if classifier(issue_ids) != (len(issues), 0, 0):
        raise AssertionError("issue ID scope/classification mismatch")
    for issue in issues:
        options = [entry["id"] for entry in issue["hypotheses"]]
        if classifier(options) != (len(options), 0, 0):
            raise AssertionError("hypothesis ID scope/classification mismatch")
    canonical = json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return {
        "report_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "issues": len(issues),
        "hypotheses": sum(len(x["hypotheses"]) for x in issues),
        "python_validation_retained": True,
        "source_evidence_status": "NOT_VERIFIED",
        "external_execution": False,
        "trading_authority": False,
    }


def probe(engine: str, issues: int, iterations: int) -> dict:
    if engine not in ("python", "rust") or not 1 <= iterations <= 2000:
        raise ValueError("invalid engine or iterations")
    document = fixture(issues)
    if engine == "python":
        classifier = python_classify
    else:
        from rust_ids import classify_ids as classifier
    expected = assess(document, python_classify)
    if assess(document, classifier) != expected:
        raise AssertionError("native consumer integration differs from Python")

    start = time.perf_counter_ns()
    for _ in range(iterations):
        if assess(document, classifier) != expected:
            raise AssertionError("consumer output was not deterministic")
    elapsed = time.perf_counter_ns() - start
    return {
        "schema": SCHEMA,
        "engine": engine,
        "issues": issues,
        "iterations": iterations,
        "ms_per_full_consumer_call": round(elapsed / iterations / 1e6, 5),
        "max_rss_kib_linux": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "consumer_result": expected,
        "limits": (
            "Separate host processes, Python validation and planning preserved; "
            "synthetic fixture, no external users or production workload"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", required=True, choices=["python", "rust"])
    parser.add_argument("--issues", type=int, default=12)
    parser.add_argument("--iterations", type=int, default=200)
    args = parser.parse_args()
    print(json.dumps(probe(args.engine, args.issues, args.iterations), sort_keys=True))


if __name__ == "__main__":
    main()
