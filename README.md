# Compound Intelligence Starter

**Don't just use intelligence. Compound it.**

A small, runnable, dependency-free demonstration of a persistent evidence-driven improvement loop:

**Discover → Reason → Challenge → Build → Validate → Learn → Improve → Repeat**

This public educational starter shows how independent roles and durable evidence can turn repeated experiments into accumulated, checkable knowledge. It intentionally does **not** include private infrastructure, credentials, production agent controls, or financial trading logic.

## Quick start

Requires Python 3.10+; no cloud account, API key, model subscription, or third-party Python package is required.

```bash
python -m src.compound_intelligence.demo --workspace ./local-data --iterations 3
python -m unittest discover -s tests -v
```

View the durable, append-only evidence at `local-data/evidence.jsonl`. Run the demo again with the same workspace: completed experiments are recognized, and new work continues without rewriting prior evidence.

## What this demonstrates

- **Discovery:** proposes small candidate changes to a generic task.
- **Reasoning:** records an explicit hypothesis and expected result.
- **Challenge:** independently checks for counterexamples and rejects an unsupported candidate.
- **Validation:** only a passing deterministic check can promote a finding.
- **Learning:** saves a timestamped record of every evaluation, including failures.
- **Continuation:** reruns are idempotent by candidate ID and use the existing knowledge ledger.

This is a deterministic reference implementation, **not** a continuously running general intelligence, an autonomous coding agent, or a guaranteed learning system. Model integrations are optional future adapters; a model's claims must never substitute for verification.

## Design

```text
Task → Candidate generation → Challenger → Deterministic validator
                                      ↓
                              Append-only evidence
                                      ↓
                          Verified knowledge / next iteration
```

See [Architecture](docs/ARCHITECTURE.md) and [Public release boundaries](docs/SECURITY.md).

## Optional tools you can connect later

- [Oracle Cloud Free Tier](https://www.oracle.com/cloud/free/) — optional persistent hosting (availability and eligibility vary).
- [Ollama](https://ollama.com) — local model serving.
- [Claude Code](https://code.claude.com/docs/en/overview) — software development assistance.
- [ChatGPT / Codex](https://chatgpt.com/codex) — interactive research and coding.
- [GitHub Actions](https://docs.github.com/en/actions) — reproducible automated checks.

No proprietary model or cloud service is required to run this starter. Tool names above describe independent products; this project is not affiliated with their providers.

## Next improvements

Add sandboxed model adapters, pluggable domain validators, explicit task authorization, bounded budgets, a job queue, reproducible experiment datasets, and human-reviewed promotion of higher-risk capabilities.

## Contributing

Issues and narrowly scoped PRs with passing tests are welcome. See [CONTRIBUTING](CONTRIBUTING.md). Licensed under [MIT](LICENSE).
