# Offline hypothesis explorer — compare before you build

This is an original educational **browser view of the same validated issue-challenger output** as the command-line tool. It does not run an AI model or engineering experiment.

## One-minute walkthrough

From the repository root, with Python 3.10+ and no dependencies:

```sh
python -m src.compound_intelligence.issue_explorer --input examples/engineering_issues.json --output issue-explorer.html
```

Open `issue-explorer.html` directly in a browser. The page shows two *fictional* UX bugs: a weak keyboard focus outline and a confusing empty result. For each issue it shows a proposed rank, the least-cost initial check and its explicit counterexample. Change **Explore an issue** to focus on one problem, expand alternatives with the native disclosure controls and return to **All fictional issues** to compare.

The filter changes **visibility only**. It does not reprioritize an issue, simulate evidence, edit the input, write to GitHub, call an API or mark a hypothesis tested. The report makes non-execution and absent release authority prominent.

For a strictly script-free export, use the separate [static issue report](ENGINEERING_ISSUE_CHALLENGER.md#new-browse-an-accessible-offline-report). Both tools depend on the same Python challenger and reject a claim of verified evidence or build authority.

## Privacy and security constraints

- Inputs are local JSON with existing bounded, strict source or brief validation. The generator uses `plan()` for fictional issue proposals and `validate_report()` for previously generated briefs; it never trusts an arbitrary suggested priority.
- Every title, claim, test, identifier and falsifier becomes **escaped HTML text**, not a script or attribute injection. Only the fixed, source-controlled filter script runs.
- CSP allows that fixed inline script **by SHA-256 hash**, disallows network connections and external assets, and has no forms, persistence, code execution or third-party services.
- The HTML is written using exclusive creation, refusing existing output files and symlinks. It makes no source modifications and returns a redacted `REJECTED` receipt on malformed input.
- Source proposals and ordinal impact/cost figures are unverified. Replacing a hypothesis or editing its cost changes a proposal; it does not provide statistical confidence or an autonomous build command.

## Tests

```sh
python -m unittest tests.test_issue_explorer -v
python -m unittest discover -s tests -v
```

The standard GitHub Actions workflow also runs `python tests/browser_check_issue_explorer.py` with real Chrome/ChromeDriver. It asserts the fixed CSP script starts, the issue filter and reset work, and 320/375/1440 px layouts fit without page overflow. Chrome automation is **not** screen-reader testing, physical-device QA or WCAG certification.

No production deployment, hosted URL, paid runtime, daemon, credential or trade permission is implied.
