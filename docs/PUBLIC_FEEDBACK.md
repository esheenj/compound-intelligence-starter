# Public feedback intake — v0.8 incremental research signal

**What this does:** records issue URLs, update times and opaque content hashes for four selected *already-public* Esheen Labs projects. It does not reproduce issue text, scrape private repositories, change code, merge PRs, call trading systems, train a model or decide which suggestions are true.

The collector is separate from the private Cortex agent and does **not** prove Cortex was commissioned on Oracle. Public issue content is untrusted; a maintainer or a scoped Cortex research worker must inspect original sources, competing hypotheses, licenses and actual test results before using a report.

## Run completely offline
```sh
python3 -m src.compound_intelligence.community_intake --fixture examples/public_feedback_fixture.json --output local-data/feedback.json
python3 -m unittest tests.test_community_intake -v
```

## Fetch only the four listed public repositories
```sh
python3 -m src.compound_intelligence.community_intake --live --output local-data/public-feedback.json
```

The live command uses unauthenticated public GitHub API GET requests, bounded responses and a 12-second timeout per source. No API key, private repository, automation grant or paid model is needed. GitHub API outages or rate limits fail the run rather than creating an invented report. Output is local, contains no raw title/comment/body, and marks all observations unreviewed.

## Automatic collection

The `Read-only public feedback intake` GitHub Actions workflow is scheduled once daily on the default branch, with a manual trigger and a one-time push trigger when collector files change. It uses a standard public GitHub-hosted runner, reads public issues only and retains its tiny report artifact for two days. If the workflow is disabled or fails, no collection occurred; verify **Actions runs** before claiming it works.

The job does not make public issues into private validated knowledge. A separate authenticated Cortex ingestion adapter is still needed to preserve reusable evidence, challenge hypotheses, create scoped coding tasks and verify PR outcomes.

If you have a reproducible problem or improvement idea, please open a public issue with only synthetic data and public links. Do not paste private source, customer data, credentials or employer screenshots.

Related: [MVP milestone issue #7](https://github.com/esheenj/compound-intelligence-starter/issues/7).
