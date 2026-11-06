# Compound Intelligence Starter

**What if AI could build on yesterday's progress instead of starting over every time?**

Today, we often ask an AI a question, get an answer, and start again. **Compound Intelligence** is a different idea: connect AI models, tools, automation, and shared memory so each experiment helps make the next one better.

Imagine a small team of AI helpers: one explores an idea, another spots problems, tools check what actually works, and the useful lessons are saved for next time.

**Why it matters:** less repeated work, fewer unchecked guesses, faster experiments, and knowledge that grows with every verified result.

**Discover → Challenge → Test → Learn → Improve → Repeat.**

**Don't just use intelligence. Compound it.**

### Try the idea in minutes

This repo includes a **free, runnable Python example** showing the core loop: test ideas, reject mistakes, save evidence, and pick up where you left off. No paid AI account, cloud setup, or API key needed.

**A starting point, not a finished autonomous AI platform:** the example uses simple, deterministic tests. Connecting real AI models and automatic development tools is the next step.

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

## v0.2 — Try the experiment runner

```bash
python -m src.compound_intelligence.runner --input examples/experiments.json
python -m src.compound_intelligence.runner --input examples/experiments.json
python -m unittest discover -s tests -v
```

The first execution records verified **and** rejected claims in local SQLite. The second reuses that evidence without duplicating experiments.

Optionally connect a local Ollama model for an independent **advisory critique**:

```bash
python -m src.compound_intelligence.runner --ollama-model YOUR_LOCAL_MODEL
```

This is a bounded arithmetic experiment runner, not a free-roaming agent. See [v0.2 setup and limits](docs/V0.2.md).

## v0.3 — Compare model proposals

**See how competing ideas become measured evidence, not just more AI output.**

Start with a free offline demonstration of two simulated proposals:

```bash
python -m src.compound_intelligence.tournament --fixture
python -m src.compound_intelligence.tournament --fixture
```

The first run records one accepted and one rejected answer. The second reuses that evidence. For **real local model proposals**, install Ollama, download two models and run:

```bash
python -m src.compound_intelligence.tournament --models YOUR_MODEL_A YOUR_MODEL_B --values 8 13
```

Results are checked by a separate deterministic validator; model claims cannot self-approve. This release benchmarks **integer addition only**, and does not claim general autonomous reasoning. [Setup, examples and limitations](docs/V0.3.md).

## v0.4 — Practical, independently checked challenges

**Go beyond arithmetic:** compare model proposals for extracting useful facts and proposing a narrowly scoped code fix, with reference answers withheld from model prompts.

```bash
python -m src.compound_intelligence.problem_runner --fixture
python -m src.compound_intelligence.problem_runner --fixture
```

The offline demonstration uses two simulated proposers. With Ollama running locally, use `--models MODEL_A MODEL_B` for real model-generated proposals. A verifier checks exact data extraction and static code patches without running model-generated source. Results are saved, replayable and scoped to the exact task/model/version.

Read [the v0.4 guide](docs/V0.4.md) for real-model setup, custom challenge files, and limitations.

## v0.5 — Measure what works

Move from individual examples to **clear capability comparisons**. The benchmark shows which simulated or local model proposals passed independent checks, which were rejected, and which produced no usable answer. Metrics are broken down by extraction versus static patching and tied to a dataset fingerprint.

```bash
python -m src.compound_intelligence.benchmark --fixture --output local-data/report.json
python -m src.compound_intelligence.benchmark --fixture --output local-data/report.json
```

For locally running Ollama models replace `--fixture` with `--models MODEL_A MODEL_B`. Fixture results are **simulated**, and tiny exact-match datasets cannot establish general intelligence or model reliability. [Guide and interpretation](docs/V0.5.md).

## v0.6 — Run bounded experiments and recover after restarts

Queue a safe offline experiment, run one controlled batch, and inspect the durable receipt:

```bash
python -m src.compound_intelligence.scheduler enqueue --id first-demo
python -m src.compound_intelligence.scheduler tick
python -m src.compound_intelligence.scheduler status
```

The scheduler currently permits **only** the simulated fixture benchmark. It does not automatically run as a daemon or execute arbitrary code; a separate scheduler can invoke one bounded tick when explicitly configured. [v0.6 usage and safety boundaries](docs/V0.6.md).

## v0.7 — See experiments and results in a visual dashboard

Generate an offline HTML evidence report from the existing local scheduler:

```bash
python -m src.compound_intelligence.scheduler enqueue --id dashboard-demo
python -m src.compound_intelligence.scheduler tick
python -m src.compound_intelligence.dashboard --queue-db local-data/v06/queue.sqlite3 --output local-data/dashboard.html
```

Open `local-data/dashboard.html` to see which jobs ran, what succeeded or failed, and which proposals passed validation. The report does not call external services or execute commands. Fixture results are visibly marked as simulated. [v0.7 guide](docs/V0.7.md).

## Next improvements

Add sandboxed model adapters, pluggable domain validators, explicit task authorization, bounded budgets, a job queue, reproducible experiment datasets, and human-reviewed promotion of higher-risk capabilities.

## Contributing

Issues and narrowly scoped PRs with passing tests are welcome. See [CONTRIBUTING](CONTRIBUTING.md). Licensed under [MIT](LICENSE).

## v0.8 — Gather public feedback without copying private data

Use a tiny read-only public GitHub issue index as the **discovery** step in the learning loop. It records source links, update times and content digests, not user comments or private repository content. Observations must still be challenged and tested before becoming knowledge or code changes.

```sh
python -m src.compound_intelligence.community_intake --fixture examples/public_feedback_fixture.json --output local-data/feedback.json
python -m unittest tests.test_community_intake -v
```

The independent scheduled GitHub Actions workflow gathers references from four explicitly listed public repos on standard public runners, with no paid service or repository-write token. It does not run Cortex on Oracle, write code or auto-promote a claim. [Read the feedback guide](docs/PUBLIC_FEEDBACK.md).

## v0.9 — Repeated experiments, measured carefully

The existing daily public-feedback GitHub Actions workflow now also stores a tiny **simulated** capability benchmark and a provenance receipt. It reuses the same schedule rather than adding infrastructure. Reports can be compared across runs, but identical fixtures should report **UNCHANGED**, never invented learning.

```bash
python -m src.compound_intelligence.benchmark --fixture --output local-data/benchmark.json
python -m src.compound_intelligence.progress receipt --report local-data/benchmark.json --run-id 123 --output local-data/receipt.json
```

The public runner has no persistent cross-run memory. Download reports from separate GitHub runs and use the [comparison guide](docs/CONTINUOUS_EXPERIMENTS.md) to inspect score changes on the same dataset. The scheduled fixture is not a running local LLM.

## v1.0 — Reuse verified knowledge on a new problem

Test the integrated example-memory loop, without subscriptions or a hosted service:

```bash
python -m src.compound_intelligence.learning_loop --fixture
python -m src.compound_intelligence.learning_loop --fixture
```

A validated extraction example becomes reusable context for a separate task. The new result is independently checked, and the run is saved for deterministic recovery. The fixture is **simulated**, not a measured improvement in a real AI. With a locally running Ollama model, replace `--fixture` with `--model YOUR_LOCAL_MODEL`.

[Full walkthrough, safety boundaries and limitations](docs/V1.0.md).

## v1.1 — Measure whether verified examples actually help

Compare the same held-out task **without** memory (baseline) and **with** previously verified examples (assisted):

```bash
python -m src.compound_intelligence.ab_evaluation --fixture
python -m src.compound_intelligence.ab_evaluation --fixture
```

The offline fixture deliberately responds only when it sees an example, demonstrating A/B plumbing—not a real AI breakthrough. With local Ollama running, use `--model YOUR_LOCAL_MODEL --run-id real-001` instead. Both arms are independently checked, and their paired results are saved for recovery. See [v1.1 evaluation guide](docs/V1.1.md).
