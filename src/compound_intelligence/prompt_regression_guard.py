"""Offline prompt score regression guard over fictional, user-supplied fixtures.

Compares supplied scores; does NOT generate/grade model responses or prove quality.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from .agentproof import parse_manifest

SCHEMA = "prompt-regression.cases.v1"
REPORT = "prompt-regression.report.v1"
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,99}\Z")


def fictional_cases(with_regression: bool = False) -> dict:
    baseline = [
        {"case_id": "important-safety-case", "critical": True, "score": 85},
        {"case_id": "fictional-helpfulness", "critical": False, "score": 60},
    ]
    candidate = [
        {"case_id": "important-safety-case", "critical": True, "score": 75 if with_regression else 90},
        {"case_id": "fictional-helpfulness", "critical": False, "score": 95 if with_regression else 65},
    ]
    return {"schema": SCHEMA, "baseline": baseline, "candidate": candidate}


def _error(reason: str) -> dict:
    return {
        "schema": REPORT, "valid_input": False, "gate_passed": False,
        "baseline_average": None, "candidate_average": None,
        "regressions": [], "critical_regressions": [], "errors": [reason],
        "scope": "User-supplied fixture scores only; not independent model assessment.",
    }


def _index(rows: object, side: str) -> dict:
    if type(rows) is not list or not (1 <= len(rows) <= 10000):
        raise ValueError(side + " must contain 1 to 10000 cases")
    result = {}
    for number, row in enumerate(rows, 1):
        if type(row) is not dict or set(row) != {"case_id", "score", "critical"}:
            raise ValueError(side + " case " + str(number) + " has invalid fields")
        case_id, score, critical = row["case_id"], row["score"], row["critical"]
        if type(case_id) is not str or ID.fullmatch(case_id) is None:
            raise ValueError(side + " invalid case_id")
        if type(score) is not int or not 0 <= score <= 100:
            raise ValueError(side + " score must be an integer from 0 to 100")
        if type(critical) is not bool:
            raise ValueError(side + " critical must be boolean")
        if case_id in result:
            raise ValueError(side + " duplicate case_id: " + case_id)
        result[case_id] = row
    return result


def compare(document: object) -> dict:
    if type(document) is not dict or set(document) != {"schema", "baseline", "candidate"} or document.get("schema") != SCHEMA:
        return _error("invalid scorecard schema or fields")
    try:
        baseline = _index(document["baseline"], "baseline")
        candidate = _index(document["candidate"], "candidate")
    except ValueError as exc:
        return _error(str(exc))
    if baseline.keys() != candidate.keys():
        return _error("candidate must contain exactly the same case IDs")
    if any(baseline[key]["critical"] != candidate[key]["critical"] for key in baseline):
        return _error("candidate changed case criticality")
    regressions = []
    for key in sorted(baseline):
        before, after = baseline[key]["score"], candidate[key]["score"]
        if after < before:
            regressions.append({
                "case_id": key, "critical": baseline[key]["critical"],
                "before": before, "after": after, "drop": before - after,
            })
    critical = [x for x in regressions if x["critical"]]
    avg_before = sum(x["score"] for x in baseline.values()) / len(baseline)
    avg_after = sum(x["score"] for x in candidate.values()) / len(candidate)
    return {
        "schema": REPORT, "valid_input": True,
        "gate_passed": not critical and avg_after >= avg_before,
        "baseline_average": avg_before, "candidate_average": avg_after,
        "regressions": regressions, "critical_regressions": critical, "errors": [],
        "scope": "User-supplied fixture scores only; not independent model assessment.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare supplied prompt scores offline")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--demo", action="store_true")
    group.add_argument("--regression-demo", action="store_true")
    group.add_argument("--input", type=Path)
    args = parser.parse_args()
    try:
        data = (fictional_cases(args.regression_demo) if args.demo or args.regression_demo
                else parse_manifest(args.input.read_text(encoding="utf-8")))
        report = compare(data)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        report = _error("input rejected: " + str(exc))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 2 if not report["valid_input"] else (0 if report["gate_passed"] else 1)


if __name__ == "__main__":
    raise SystemExit(main())
