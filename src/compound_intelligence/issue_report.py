"""Accessible, static HTML view of the public engineering issue challenger.

Offline only: no scripts, network, model inference, execution or permissions.
User-supplied text stays escaped. Submitted report claims are never trusted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from html import escape
from pathlib import Path

from .issue_challenger import (
    SCHEMA, MAX_ISSUES, _id, _no_constant, _rating, _text,
    _unique_object, plan,
)

MAX_REPORT_BYTES = 131_072
MAX_HTML_BYTES = 262_144
ISSUE_FIELDS = frozenset((
    "issue_id", "title", "priority_hint", "brief_id", "input_sha256",
    "chosen_next_test", "competing_hypotheses", "source_evidence_status",
    "build_execution_allowed", "required_next_action",
))
HYPOTHESIS_FIELDS = frozenset((
    "hypothesis_id", "claim", "test", "counterexample", "estimated_cost_units",
))
CHOSEN_FIELDS = frozenset((
    "hypothesis_id", "experiment", "falsifying_observation",
    "estimated_cost_units",
))
REPORT_FIELDS = frozenset((
    "schema", "origin", "ranked_issues", "priority_rule", "results_verified",
    "external_execution", "github_writes", "financial_or_trading_logic",
    "release_or_merge_authority",
))
PRIORITY_RULE = "4 * impact - 2 * effort - 2 * risk; ordinal hints only"
HEX = re.compile(r"[0-9a-f]{64}\Z")


def validate_report(report: object) -> list[dict]:
    """Fail closed on unknown/mutated claims, not just escaped markup."""
    if not isinstance(report, dict) or set(report) != REPORT_FIELDS:
        raise ValueError("INVALID_REPORT_SCHEMA")
    expected = {
        "schema": SCHEMA,
        "origin": "MAINTAINER_SUPPLIED_PROPOSALS",
        "priority_rule": PRIORITY_RULE,
        "results_verified": False,
        "external_execution": False,
        "github_writes": False,
        "financial_or_trading_logic": False,
        "release_or_merge_authority": "NONE",
    }
    if any(report[key] != value or type(report[key]) is not type(value)
           for key, value in expected.items()):
        raise ValueError("UNTRUSTED_REPORT_CLAIMS")
    issues = report["ranked_issues"]
    if not isinstance(issues, list) or not 1 <= len(issues) <= MAX_ISSUES:
        raise ValueError("INVALID_RANKED_ISSUES")
    ids = set()
    digests = set()
    for issue in issues:
        if not isinstance(issue, dict) or set(issue) != ISSUE_FIELDS:
            raise ValueError("INVALID_BRIEF_SCHEMA")
        ident = _id(issue["issue_id"])
        if ident in ids:
            raise ValueError("DUPLICATE_BRIEF")
        ids.add(ident)
        _text(issue["title"], "title", 120)
        score = issue["priority_hint"]
        if type(score) is not int or not -16 <= score <= 16:
            raise ValueError("INVALID_PRIORITY")
        digest = issue["input_sha256"]
        if not isinstance(digest, str) or not HEX.fullmatch(digest):
            raise ValueError("INVALID_DIGEST")
        if issue["brief_id"] != digest[:24] or digest in digests:
            raise ValueError("INVALID_BRIEF_ID")
        digests.add(digest)
        if (issue["source_evidence_status"] != "NOT_VERIFIED"
                or issue["required_next_action"] != "RUN_AND_REVIEW_FALSIFIABLE_TEST"
                or issue["build_execution_allowed"] is not False):
            raise ValueError("UNTRUSTED_BRIEF_CLAIMS")
        options = issue["competing_hypotheses"]
        if not isinstance(options, list) or not 2 <= len(options) <= 4:
            raise ValueError("INVALID_COMPETING_HYPOTHESES")
        hypothesis_ids = set()
        for hypothesis in options:
            if not isinstance(hypothesis, dict) or set(hypothesis) != HYPOTHESIS_FIELDS:
                raise ValueError("INVALID_HYPOTHESIS_SCHEMA")
            option_id = _id(hypothesis["hypothesis_id"])
            if option_id in hypothesis_ids:
                raise ValueError("DUPLICATE_HYPOTHESIS")
            hypothesis_ids.add(option_id)
            for key in ("claim", "test", "counterexample"):
                _text(hypothesis[key], key, 240)
            if hypothesis["test"] == hypothesis["counterexample"]:
                raise ValueError("INVALID_COUNTEREXAMPLE")
            _rating(hypothesis["estimated_cost_units"], "cost")
        if options != sorted(options, key=lambda h: (h["estimated_cost_units"], h["hypothesis_id"])):
            raise ValueError("UNSORTED_HYPOTHESES")
        chosen = issue["chosen_next_test"]
        if not isinstance(chosen, dict) or set(chosen) != CHOSEN_FIELDS:
            raise ValueError("INVALID_CHOSEN_TEST")
        cheapest = options[0]
        if chosen != {
            "hypothesis_id": cheapest["hypothesis_id"],
            "experiment": cheapest["test"],
            "falsifying_observation": cheapest["counterexample"],
            "estimated_cost_units": cheapest["estimated_cost_units"],
        }:
            raise ValueError("INCONSISTENT_TEST_SELECTION")
    if issues != sorted(issues, key=lambda issue: (-issue["priority_hint"], issue["issue_id"])):
        raise ValueError("UNSORTED_ISSUES")
    return issues


def _e(value: object) -> str:
    return escape(str(value), quote=True)


def render(report: object) -> str:
    """Render only a validated report; never interpolate unescaped input."""
    issues = validate_report(report)
    cards = []
    for index, issue in enumerate(issues, 1):
        chosen = issue["chosen_next_test"]
        explanations = "".join(
            "<li><h4>" + _e(hypothesis["hypothesis_id"]) + "</h4>"
            + "<p>" + _e(hypothesis["claim"]) + "</p>"
            + "<dl><dt>Proposed check</dt><dd>" + _e(hypothesis["test"]) + "</dd>"
            + "<dt>Would be disproved by</dt><dd>" + _e(hypothesis["counterexample"]) + "</dd>"
            + "<dt>Estimated test cost</dt><dd>" + _e(hypothesis["estimated_cost_units"]) + " / 5</dd></dl></li>"
            for hypothesis in issue["competing_hypotheses"]
        )
        cards.append(
            '<article class="card" aria-labelledby="issue-' + _e(issue["issue_id"]) + '">'
            + '<p class="eyebrow">Issue ' + str(index) + ' · Proposed priority '
            + _e(issue["priority_hint"]) + " (unverified)</p>"
            + '<h2 id="issue-' + _e(issue["issue_id"]) + '">' + _e(issue["title"]) + "</h2>"
            + '<p class="sub">Brief ID <code>' + _e(issue["brief_id"]) + "</code></p>"
            + '<section aria-label="Suggested next experiment" class="experiment">'
            + '<h3>Cheapest suggested next test</h3><p>' + _e(chosen["experiment"]) + "</p>"
            + '<p><strong>What would disprove it:</strong> ' + _e(chosen["falsifying_observation"]) + "</p>"
            + '<p>Hypothesis: <code>' + _e(chosen["hypothesis_id"]) + "</code> · Estimated cost "
            + _e(chosen["estimated_cost_units"]) + " / 5</p></section>"
            + "<h3>Competing explanations</h3><ol>" + explanations + "</ol>"
            + '<p class="sub">Evidence: NOT VERIFIED · Build authority: NONE</p></article>'
        )

    page = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'none'; connect-src 'none'; img-src 'none'; object-src 'none'; form-action 'none'; base-uri 'none'">
<title>Engineering Issue Challenger · Offline report</title>
<style>
:root{color-scheme:light dark;font-family:system-ui,-apple-system,sans-serif;line-height:1.6}
*{box-sizing:border-box}
body{max-width:70rem;margin:0 auto;padding:clamp(1rem,3vw,2.5rem);background:Canvas;color:CanvasText}
a:focus-visible{outline:3px solid #777;outline-offset:4px}
h1,h2,h3,h4{line-height:1.25}
h1{font-size:clamp(1.7rem,3vw,2.5rem)}
h2{font-size:1.4rem}
.banner,.card{border:1px solid GrayText;border-radius:1rem;padding:1.2rem;margin-block:1.5rem}
.banner{border-left:5px solid currentColor}
.eyebrow{font-weight:700;text-transform:uppercase;font-size:.82rem;letter-spacing:.03em}
.sub{opacity:.85;overflow-wrap:anywhere}
.experiment{border-left:4px solid currentColor;padding:.1rem 1rem;margin-block:1.25rem;background:Canvas}
ol{padding-left:1.4rem}
li{padding:.3rem .5rem .7rem .2rem;margin-bottom:1rem;border-bottom:1px solid GrayText}
dt{font-weight:700;margin-top:.4rem}
dd{margin-left:0;overflow-wrap:anywhere}
code{font-family:ui-monospace,monospace;overflow-wrap:anywhere}
.skip{position:absolute;left:1rem;top:-6rem;background:Canvas;color:CanvasText;padding:.5rem}
.skip:focus{top:.5rem}
@media(max-width:40rem){.card,.banner{padding:.85rem}h2{font-size:1.2rem}}
</style>
</head>
<body>
<a class="skip" href="#main">Skip to issue results</a>
<header><p class="eyebrow">Compound Intelligence Starter · Synthetic example</p>
<h1>Engineering Issue Challenger</h1>
<p>Compare explanations. Challenge assumptions. Test before building.</p></header>
<main id="main">
<section class="banner" aria-labelledby="warning">
<h2 id="warning">Proposals only — nothing has been executed</h2>
<p>All issue ratings, hypotheses and proposed tests are unverified user-supplied inputs.
No experiments, code builds, pull requests or independent accessibility checks were run by this report.
Priority scores are sorting hints, not measured impact or confidence.</p>
</section>
<p><strong>Suggested issue count:</strong> __COUNT__</p>
__CARDS__
</main>
<footer><p>Standalone offline HTML · no JavaScript, remote assets or analytics.
Source: original fictional examples · MIT-licensed public teaching tool.</p></footer>
</body>
</html>
"""
    page = page.replace("__COUNT__", str(len(issues))).replace("__CARDS__", "\n".join(cards))
    if len(page.encode("utf-8")) > MAX_HTML_BYTES:
        raise ValueError("OVERSIZED_HTML")
    return page


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Render a bounded offline issue report")
    parser.add_argument("--input", required=True, help="JSON issue proposals or challenger output")
    parser.add_argument("--output", required=True, help="New local HTML file (never overwritten)")
    args = parser.parse_args(argv)
    try:
        source, output = Path(args.input), Path(args.output)
        if (source.is_symlink() or not source.is_file()
                or not 0 < source.stat().st_size <= MAX_REPORT_BYTES):
            raise ValueError("INVALID_INPUT_FILE")
        document = json.loads(source.read_text(encoding="utf-8"),
                              object_pairs_hook=_unique_object, parse_constant=_no_constant)
        report = plan(document) if isinstance(document, dict) and "version" in document else document
        html = render(report)
        if not output.parent.is_dir() or output.parent.is_symlink() or output.is_symlink():
            raise ValueError("INVALID_OUTPUT_PATH")
        # 'x' refuses existing files, symlinks and silent overwrite.
        with output.open("x", encoding="utf-8", newline="\n") as target:
            target.write(html)
        digest = hashlib.sha256(html.encode("utf-8")).hexdigest()
        print(json.dumps({"schema": "compound-engineering-report-v1",
                          "state": "CREATED", "sha256": digest,
                          "issues": len(report["ranked_issues"]),
                          "external_execution": False}, sort_keys=True))
        return 0
    except (ValueError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(json.dumps({"schema": "compound-engineering-report-v1",
                          "state": "REJECTED", "error_type": type(exc).__name__},
                         sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
