"""Offline interactive view of the validated public issue challenger.

Python computes every proposed priority and test. Small, fixed browser script
only filters already rendered fictional proposals; it never evaluates source,
calls a service, runs experiments or grants engineering permission.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
from html import escape
from pathlib import Path

from .issue_challenger import _no_constant, _unique_object, plan
from .issue_report import MAX_HTML_BYTES, MAX_REPORT_BYTES, validate_report


SCRIPT = """\
"use strict";
const selector = document.getElementById("issue-filter");
const status = document.getElementById("filter-status");
const cards = [...document.querySelectorAll("article[data-issue]")];
function applySelection() {
  const chosen = selector.value;
  let visible = 0;
  for (const card of cards) {
    const show = chosen === "all" || card.dataset.issue === chosen;
    card.hidden = !show;
    if (show) visible += 1;
  }
  status.textContent = String(visible) + " fictional issue" +
    (visible === 1 ? "" : "s") + " shown. All findings remain unverified.";
}
selector.addEventListener("change", applySelection);
applySelection();
"""


def _esc(value: object) -> str:
    return escape(str(value), quote=True)


def render_explorer(report: object) -> str:
    """Return one self-contained HTML page from validated, non-executing briefs."""
    issues = validate_report(report)
    controls = ['<option value="all">All fictional issues</option>']
    articles = []
    for order, issue in enumerate(issues, 1):
        identity = _esc(issue["issue_id"])
        controls.append(
            '<option value="' + identity + '">' + _esc(issue["title"]) + "</option>"
        )
        choices = []
        for index, candidate in enumerate(issue["competing_hypotheses"]):
            details = "<details" + (" open" if index == 0 else "") + ">"
            details += (
                "<summary><strong>" + _esc(candidate["claim"]) + "</strong>"
                + '<span class="pill">Estimated cost '
                + _esc(candidate["estimated_cost_units"]) + "/5</span></summary>"
                + '<dl><dt>Proposed check</dt><dd>' + _esc(candidate["test"]) + "</dd>"
                + "<dt>What would disprove it</dt><dd>"
                + _esc(candidate["counterexample"]) + "</dd></dl></details>"
            )
            choices.append(details)
        first = issue["chosen_next_test"]
        articles.append(
            '<article class="card" data-issue="' + identity + '" aria-labelledby="issue-'
            + identity + '">'
            + '<p class="eyebrow">Rank ' + str(order)
            + " · Proposed priority hint " + _esc(issue["priority_hint"]) + "</p>"
            + '<h2 id="issue-' + identity + '">' + _esc(issue["title"]) + "</h2>"
            + '<p class="sub">Stable brief: <code>' + _esc(issue["brief_id"])
            + "</code></p>"
            + '<section class="first"><h3>Cheapest proposed first test</h3><p>'
            + _esc(first["experiment"]) + "</p>"
            + "<p><strong>Falsified by:</strong> "
            + _esc(first["falsifying_observation"]) + "</p>"
            + '<p class="sub">Proposed test cost: '
            + _esc(first["estimated_cost_units"]) + "/5</p></section>"
            + "<h3>Compare competing explanations</h3>"
            + "".join(choices)
            + '<p class="footer">Source evidence: NOT VERIFIED · No build authority'
            + " · No experiment executed</p></article>"
        )
    hash_token = base64.b64encode(hashlib.sha256(SCRIPT.encode("utf-8")).digest()).decode("ascii")
    html = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'sha256-__SCRIPT_HASH__'; style-src 'unsafe-inline'; connect-src 'none'; img-src 'none'; object-src 'none'; form-action 'none'; base-uri 'none'">
<title>Compare engineering hypotheses · Compound Intelligence Starter</title>
<style>
:root{font:16px/1.55 system-ui,-apple-system,BlinkMacSystemFont,sans-serif;color-scheme:light dark}
*{box-sizing:border-box}
body{max-width:75rem;margin:0 auto;padding:clamp(1rem,3.6vw,2.8rem);background:Canvas;color:CanvasText}
h1,h2,h3{line-height:1.22}
h1{font-size:clamp(2rem,5vw,3.4rem);max-width:23ch;letter-spacing:-.03em}
h2{font-size:1.45rem;margin-top:.4rem}
h3{font-size:1.08rem;margin-bottom:.5rem}
p{margin:.7rem 0}
.eyebrow{font-size:.77rem;font-weight:800;letter-spacing:.09em;text-transform:uppercase}
.intro{font-size:1.1rem;max-width:65ch}
.notice,.card,.filters{border:1px solid GrayText;border-radius:1rem;padding:1.25rem;margin:1.3rem 0}
.notice{border-inline-start:5px solid currentColor}
.cards{display:grid;gap:1rem}
.card{margin:0;min-width:0}
.card[hidden]{display:none!important}
.first{border-inline-start:4px solid currentColor;padding:.2rem 1rem;margin:1rem 0}
details{border:1px solid GrayText;border-radius:.65rem;margin:.7rem 0;padding:.8rem}
summary{cursor:pointer;display:flex;gap:.5rem;flex-wrap:wrap;align-items:baseline}
summary strong{flex:1;min-width:12rem}
.pill{font-size:.82rem;border:1px solid GrayText;border-radius:2rem;padding:.1rem .6rem;white-space:nowrap}
dt{font-weight:700;margin-top:.5rem}
dd{margin-left:0;overflow-wrap:anywhere}
.sub,.footer{opacity:.83;font-size:.9rem;overflow-wrap:anywhere}
.filters label{display:block;font-weight:750;margin-bottom:.4rem}
select{font:inherit;color:CanvasText;background:Canvas;border:1px solid GrayText;padding:.7rem;border-radius:.5rem;max-width:100%;width:34rem;min-height:44px}
:focus-visible{outline:3px solid Highlight;outline-offset:4px}
.skip{position:absolute;left:1rem;top:-7rem;background:Canvas;color:CanvasText;padding:.6rem}
.skip:focus{top:.5rem}
@media(min-width:54rem){.cards{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:34rem){.notice,.card,.filters{padding:.9rem}summary strong{min-width:0}}
</style>
</head>
<body>
<a href="#main" class="skip">Skip to proposed experiments</a>
<header>
<p class="eyebrow">Compound Intelligence Starter · Offline scenario explorer</p>
<h1>One issue. Many explanations. One falsifiable next test.</h1>
<p class="intro">Browse competing explanations from original fictional engineering problems. Every suggested experiment comes from the same validated Python engine as the CLI, not a browser AI model.</p>
</header>
<main id="main">
<aside class="notice" aria-label="Research and execution limitations"><strong>Proposals only — not executed.</strong> Ratings, priorities and competing hypotheses are maintainer-supplied teaching inputs, not measured confidence. No code builds, tests of the hypotheses, GitHub writes, releases or external services are triggered by this page.</aside>
<section class="filters" aria-label="Select a fictional issue">
<label for="issue-filter">Explore an issue</label>
<select id="issue-filter">__ISSUE_OPTIONS__</select>
<p id="filter-status" role="status" aria-live="polite">All fictional issues shown. Nothing has been executed.</p>
</section>
<div class="cards">__ISSUE_CARDS__</div>
</main>
<footer><p class="footer">Self-contained, offline source-first educational tool · No API, account, telemetry or external assets. Expand each hypothesis to see its proposed falsifier. Screen-reader and physical-device certification are not claimed.</p></footer>
<script>__SCRIPT_CODE__</script>
</body>
</html>
"""
    html = (html.replace("__SCRIPT_HASH__", hash_token)
            .replace("__ISSUE_OPTIONS__", "\n".join(controls))
            .replace("__ISSUE_CARDS__", "\n".join(articles))
            .replace("__SCRIPT_CODE__", SCRIPT))
    if len(html.encode("utf-8")) > MAX_HTML_BYTES:
        raise ValueError("OVERSIZED_EXPLORER")
    return html


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Create a local interactive challenger report")
    parser.add_argument("--input", required=True, help="Fictional issue JSON or generated challenger brief")
    parser.add_argument("--output", required=True, help="New HTML path (exclusive write)")
    args = parser.parse_args(argv)
    try:
        source, destination = Path(args.input), Path(args.output)
        if (source.is_symlink() or not source.is_file()
                or not 0 < source.stat().st_size <= MAX_REPORT_BYTES):
            raise ValueError("INVALID_INPUT_FILE")
        document = json.loads(source.read_text(encoding="utf-8"),
                              object_pairs_hook=_unique_object, parse_constant=_no_constant)
        report = plan(document) if isinstance(document, dict) and "version" in document else document
        html = render_explorer(report)
        if (not destination.parent.is_dir() or destination.parent.is_symlink()
                or destination.is_symlink()):
            raise ValueError("INVALID_OUTPUT_FILE")
        with destination.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(html)
        print(json.dumps({
            "schema": "compound-issue-explorer-v1", "state": "CREATED",
            "issues": len(report["ranked_issues"]),
            "sha256": hashlib.sha256(html.encode("utf-8")).hexdigest(),
            "external_execution": False,
        }, sort_keys=True))
        return 0
    except (ValueError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(json.dumps({"schema": "compound-issue-explorer-v1",
                          "state": "REJECTED", "error_type": type(exc).__name__},
                         sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
