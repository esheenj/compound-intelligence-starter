# Public MVP Wave Planner — original offline reference

This is a small, **runnable public open-source MVP tool** hosted within Compound Intelligence Starter, not a newly created standalone repository or a deployed website. It offers deterministic planning of at most three review candidates from fictional self-declared metadata. No GitHub access, AI model, CI runner, paid service, private source, credentials or backend is needed.

Run from the repository root:

```sh
python -m src.compound_intelligence.mvp_portfolio --input examples/mvp_portfolio.json
python -m unittest tests.test_mvp_portfolio -v
```

The JSON response includes a sorted review wave, clear next falsifiable step, input digest, unsupported gates, and explicit \`external_execution: false\`, \`publication_authority: NONE\`, \`results_verified: false\`. Self-reported \`status\` and flags **are never validated GitHub, rights, browser or CI evidence**. Candidates marked source-published or Pages-deployed still require independent provider verification.

## Input contract

Root: \`version: 1\`, \`max_active: 1..3\`, \`candidates: 1..100\`. Each candidate has exactly seven fields: \`id\` (lowercase slug), \`status\` (scaffold, implemented, source_published, pages_deployed, browser_verified), \`value\`, \`effort\`, \`risk\` (integers 0..5, not booleans), \`rights_reviewed\` and \`tests_verified\` (booleans). Duplicate IDs, extra fields, invalid values, symlinks and files over 64 KiB are rejected, exit code 2, without echoing input. The fixture uses deliberately invented names.

## Selection algorithm and limitations

Recommend the most mature **unverified** release stages first, then prioritize by \`3 × value − 2 × effort − risk\`, breaking ties by slug. Already browser-verified entries stay in the explanatory output but are not selected. The score is an explainable educational heuristic, not market evidence or proof of value. Every selected item is still only a review recommendation.

A real public release separately requires original clean source, compatible licensing, rights review, negative tests, exact-head CI, publisher receipt, real browser acceptance and a distinct GitHub repository if independently branded. **Do not publish private incubator history, financial tools, employer/customer data, internal control-plane source or privileged agent code.**

This example belongs to the public domain of *methods*, not a private Cortex orchestration capability. It creates no jobs, issues, branches, releases, orders or tasks.
