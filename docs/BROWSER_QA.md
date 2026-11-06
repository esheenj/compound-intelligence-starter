# Browser accessibility smoke for the offline Engineering Issue Report

Issue: [#17](https://github.com/esheenj/compound-intelligence-starter/issues/17). Original report: [issue #15](https://github.com/esheenj/compound-intelligence-starter/issues/15).

The report is generated from **fictional** UX issues. This is an actual headless-browser regression, not a statement of full WCAG conformance.

## What the automated browser job does

The existing GitHub Actions `Tests` workflow includes one `browser-smoke` job on `ubuntu-24.04`, which has Google Chrome and ChromeDriver. The test uses only the Python standard library to speak the W3C WebDriver protocol to ChromeDriver on `127.0.0.1`. It adds **no runtime or browser automation package** to the public project, no external API and no new scheduler.

The check creates the real offline HTML using the existing Python CLI and loads that file in headless Chrome. It observes:

| Check | Evidence required |
| --- | --- |
| Browser and semantics | Real browser version, English document language, exactly one main landmark and top heading |
| Clear status | Unverified/no-experiment notice visible, two original synthetic issues, two or more hypotheses per issue |
| Keyboard | Tab reaches the skip link, the link becomes visible, Enter navigates to `#main` |
| Responsive | At 375 × 812 and 1440 × 900, no unexpected horizontal document overflow; warning remains visible |
| Light/dark | Emulate both preferences and observe a real computed background change |
| Safe offline report | No active script, image, iframe, form or remote-reference elements; CSP disallows network and scripts |

## Reproduce

From repository root on a machine with a matching headless Chrome and ChromeDriver installed:

```sh
python -m unittest discover -s tests -v
python tests/browser_check_issue_report.py
```

The browser script prints `compound-browser-qa-v1` JSON with observed checks, the actual browser version, and explicit `screen_reader_tested: false` and `wcag_certified: false`. All checks must succeed or the job exits nonzero. No persistent HTML, screenshots or third-party telemetry are generated.

## Limitations and follow-up

Browser automation exercises a real browser but **cannot prove screen-reader usability, visual appearance on all devices, or full accessibility standard conformance**. The issue should only be closed when real Chrome CI evidence is checked; a future independent assistive-technology or mobile-device check remains useful. Do not upload real customer/client information as test fixtures or publish credentials. Private Cortex, trading strategy and Commander code remain excluded.
