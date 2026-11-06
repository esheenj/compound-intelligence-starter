# Engineering Issue Challenger — test before you build

**From a vague issue to a falsifiable engineering experiment, without paying for an AI API.**

This is a small *public and original* implementation of two reusable intelligence
patterns: (1) **competing-hypothesis challenging** and (2) **stable,
executor-neutral task briefs**. It shows how a development agent could avoid
picking its favourite explanation prematurely.

## Try it

Python 3.10+ and the standard library are enough. From the repository root:

```sh
python -m src.compound_intelligence.issue_challenger --input examples/engineering_issues.json
python -m unittest tests.test_issue_challenger -v
```

The fictional input includes a focus-ring visibility issue and a dashboard
empty-state issue. Every issue has at least two explanations and an experiment
that would disprove each explanation. The CLI ranks *suggested* work from
maintainer-supplied 1–5 impact, effort and risk ratings, then picks the
cheapest next falsifiable test (ties are resolved by hypothesis ID).

## How to read the output

- `ranked_issues` — proposals in deterministic priority order, not a
  verified severity or impact measurement
- `competing_hypotheses` — explanations, proposed tests and clear
  counterexamples; **none has run**
- `chosen_next_test` — the smallest claimed cost experiment to test
  first; **not an instruction to execute automatically**
- `brief_id` / `input_sha256` — stable content-addressed identity.
  Repeating the same issue produces the same ID; a changed test or hypothesis
  creates a different ID, so a future execution worker can detect stale briefs
- `source_evidence_status: NOT_VERIFIED` — user-provided ratings and claims
  are not independently checked
- `build_execution_allowed: false` — an authorised worker must
  independently qualify scope, source HEAD, test plan and policy

The priority heuristic is `4 × impact − 2 × effort − 2 × risk`. This is an
explainable sorting hint, not scientific risk estimation, a trained model,
revenue prediction, or a recommendation for financial decisions.

## Example: how it supports autonomous engineering

1. Collect **public** GitHub issue references and classify their contents as
   untrusted inputs; never treat contributor text as executable commands.
2. A human or qualified tool proposes two or more explanations and
   counterexample-driven checks using the JSON input contract.
3. Run this CLI to create a stable test-first brief. Compare the competing
   hypotheses rather than leaping to a code patch.
4. A separately authorised engineering worker runs the selected bounded test,
   preserves failure evidence and creates a branch/PR only within its actual
   repository permissions.
5. Check exact-head CI and source-rights independently. Publish only reviewed,
   original and permitted artifacts; store success *and* rejected hypotheses.

The public teaching tool **does not** fetch GitHub, run shell commands, call a
model, build or publish code, contact a scheduler, operate money/trading systems,
or grant Commander authority. Importing the CLI into a private service doesn't
turn proposals into actions. An execution receipt must come from the real
authorised system, not this output.

## Input contract and failure cases

Use one JSON document containing exactly `version: 1` and `issues`.
A maximum of 12 issues is supported. Each issue has exactly `id`, `title`,
`impact`, `effort`, `risk`, and `hypotheses`. Each issue needs 2–4
hypotheses with exactly `id`, `claim`, `test`, `counterexample`,
and `cost`. All scores are integer 1–5; identifiers are simple lowercase
tokens. Duplicate keys, overlarge documents (64 KiB), symlink inputs, invalid
types, missing falsifiers and common secret-shaped fields fail closed. The
tool prints a redacted `REJECTED` status rather than echoing malformed input.

**Privacy:** use original, fictional or clearly public data. Do not place
employer/client artifacts, private models, trading algorithms, market
execution parameters, secrets or sensitive customer information into
examples or public issues. This project is MIT-licensed and has no
additional runtime dependencies.

## New: browse an accessible offline report

Turn the same fictional issue proposals into a self-contained static HTML page:

```sh
python -m src.compound_intelligence.issue_report --input examples/engineering_issues.json --output issue-challenger-report.html
```

Open `issue-challenger-report.html` in a local browser. The file contains a
clear unverified notice, issue titles, prioritisation hints, stable brief IDs,
the cheapest suggested test, explicit falsifying observations and *all*
competing explanations.

You can also render **already produced challenger JSON** (without changing the input):

```sh
python -m src.compound_intelligence.issue_challenger --input examples/engineering_issues.json > issue-brief.json
python -m src.compound_intelligence.issue_report --input issue-brief.json --output issue-brief-report.html
```

The renderer checks strict schemas and non-execution markers; it rejects
unrecognised fields, inconsistent test selection, invalid identifiers and
a claim that results are already verified or that build authority exists.
Contributor text is escaped as inert HTML text, not treated as tags. The
standalone report uses semantic headings, a keyboard skip link, responsive
CSS and a restrictive content-security policy. No JavaScript, remote assets,
third-party package, key, account or online service is involved.

**Limitations:** The report is static and does *not* verify the truth of issue
claims, prove that any experiments ran, grant engineering permissions, publish
a PR or certify browser/screen-reader accessibility. File creation is
exclusive: existing output files are not silently overwritten. Use fictional,
public or independently cleared inputs only.

### Real browser smoke coverage

The separate [Chrome/ChromeDriver QA guide](BROWSER_QA.md) describes an actual headless-browser check of keyboard skip-link navigation, responsive widths and light/dark computed styles. It runs in GitHub Actions alongside Python tests and reports the browser version. This is not a screen-reader certification.
