"""Public, offline engineering issue challenger: compare tests before building.

Original teaching example. No GitHub API, model inference, shell, code execution,
trusted evidence, private project access, or implied deployment authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

SCHEMA = "compound-engineering-challenger-v1"
MAX_INPUT_BYTES = 65_536
MAX_ISSUES = 12
MAX_OPTIONS = 4
IDENTIFIER = re.compile(r"[a-z][a-z0-9-]{1,39}\Z")
SENSITIVE = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY|Authorization:\s*Bearer|api[_-]?key\s*[:=]", re.I)
ISSUE_KEYS = frozenset(("id", "title", "impact", "effort", "risk", "hypotheses"))
OPTION_KEYS = frozenset(("id", "claim", "test", "counterexample", "cost"))


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def _no_constant(value: str):
    raise ValueError("INVALID_JSON_NUMBER")


def _text(value: object, field: str, limit: int) -> str:
    if (not isinstance(value, str) or not value.strip()
            or len(value) > limit or value != value.strip()
            or any(ord(ch) < 32 or ord(ch) == 127 for ch in value)
            or SENSITIVE.search(value)):
        raise ValueError("INVALID_" + field.upper())
    return value


def _id(value: object) -> str:
    if not isinstance(value, str) or IDENTIFIER.fullmatch(value) is None:
        raise ValueError("INVALID_IDENTIFIER")
    return value


def _rating(value: object, field: str) -> int:
    if type(value) is not int or not 1 <= value <= 5:
        raise ValueError("INVALID_" + field.upper())
    return value


def validate(document: object) -> list[dict]:
    """Require multiple falsifiable alternatives; reject unknown schema and keys."""
    if not isinstance(document, dict) or set(document) != {"version", "issues"}:
        raise ValueError("INVALID_DOCUMENT_SCHEMA")
    if type(document["version"]) is not int or document["version"] != 1:
        raise ValueError("INVALID_VERSION")
    issues = document["issues"]
    if not isinstance(issues, list) or not 1 <= len(issues) <= MAX_ISSUES:
        raise ValueError("INVALID_ISSUE_COUNT")
    names = set()
    for issue in issues:
        if not isinstance(issue, dict) or set(issue) != ISSUE_KEYS:
            raise ValueError("INVALID_ISSUE_SCHEMA")
        issue_id = _id(issue["id"])
        if issue_id in names:
            raise ValueError("DUPLICATE_ISSUE")
        names.add(issue_id)
        _text(issue["title"], "title", 120)
        for name in ("impact", "effort", "risk"):
            _rating(issue[name], name)
        hypotheses = issue["hypotheses"]
        if not isinstance(hypotheses, list) or not 2 <= len(hypotheses) <= MAX_OPTIONS:
            raise ValueError("NEED_COMPETING_HYPOTHESES")
        options = set()
        for entry in hypotheses:
            if not isinstance(entry, dict) or set(entry) != OPTION_KEYS:
                raise ValueError("INVALID_HYPOTHESIS_SCHEMA")
            option_id = _id(entry["id"])
            if option_id in options:
                raise ValueError("DUPLICATE_HYPOTHESIS")
            options.add(option_id)
            for name in ("claim", "test", "counterexample"):
                _text(entry[name], name, 240)
            _rating(entry["cost"], "cost")
            if entry["test"] == entry["counterexample"]:
                raise ValueError("TEST_CANNOT_EQUAL_COUNTEREXAMPLE")
    return issues


def plan(document: object) -> dict:
    """Return reproducible candidate tests; no proposed work is self-approved."""
    issues = validate(document)
    scored = []
    for issue in issues:
        # Deliberate heuristic from maintainer-assigned ordinal ratings.
        # Neither this ranking nor a proposed test proves factual confidence.
        score = 4 * issue["impact"] - 2 * issue["effort"] - 2 * issue["risk"]
        options = sorted(issue["hypotheses"], key=lambda option: (option["cost"], option["id"]))
        spec = {
            "issue_id": issue["id"],
            "title": issue["title"],
            "hypotheses": options,
            "impact": issue["impact"],
            "effort": issue["effort"],
            "risk": issue["risk"],
        }
        fingerprint = hashlib.sha256(json.dumps(
            spec, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")).hexdigest()
        scored.append({
            "issue_id": issue["id"],
            "title": issue["title"],
            "priority_hint": score,
            "brief_id": fingerprint[:24],
            "input_sha256": fingerprint,
            "chosen_next_test": {
                "hypothesis_id": options[0]["id"],
                "experiment": options[0]["test"],
                "falsifying_observation": options[0]["counterexample"],
                "estimated_cost_units": options[0]["cost"],
            },
            "competing_hypotheses": [
                {"hypothesis_id": option["id"], "claim": option["claim"],
                 "test": option["test"], "counterexample": option["counterexample"],
                 "estimated_cost_units": option["cost"]}
                for option in options
            ],
            "source_evidence_status": "NOT_VERIFIED",
            "build_execution_allowed": False,
            "required_next_action": "RUN_AND_REVIEW_FALSIFIABLE_TEST",
        })
    scored.sort(key=lambda entry: (-entry["priority_hint"], entry["issue_id"]))
    return {
        "schema": SCHEMA,
        "origin": "MAINTAINER_SUPPLIED_PROPOSALS",
        "ranked_issues": scored,
        "priority_rule": "4 * impact - 2 * effort - 2 * risk; ordinal hints only",
        "results_verified": False,
        "external_execution": False,
        "github_writes": False,
        "financial_or_trading_logic": False,
        "release_or_merge_authority": "NONE",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Compare competing engineering issue hypotheses offline")
    parser.add_argument("--input", required=True, help="Bounded JSON input containing original proposals")
    args = parser.parse_args(argv)
    try:
        path = Path(args.input)
        if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= MAX_INPUT_BYTES:
            raise ValueError("INVALID_INPUT_FILE")
        document = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_no_constant,
        )
        result = plan(document)
    except (ValueError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(json.dumps({"schema": SCHEMA, "state": "REJECTED",
                          "error_type": type(exc).__name__}, sort_keys=True))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
