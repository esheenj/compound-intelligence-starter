# Compound Intelligence Starter

**Challenge assumptions. Verify outcomes. Reuse what works.**

Turn an engineering problem into competing, falsifiable hypotheses and a reproducible test-first brief. Explore a small, offline reference implementation of evidence-backed AI experiments, durable memory and model comparisons.

[![Tests](https://github.com/esheenj/compound-intelligence-starter/actions/workflows/test.yml/badge.svg)](https://github.com/esheenj/compound-intelligence-starter/actions/workflows/test.yml)
[![Release](https://img.shields.io/github/v/release/esheenj/compound-intelligence-starter)](https://github.com/esheenj/compound-intelligence-starter/releases/tag/v1.1.0)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB)

**Zero required subscriptions · Python standard library · Runs offline · MIT licensed**

## See it in two minutes

```bash
git clone https://github.com/esheenj/compound-intelligence-starter.git
cd compound-intelligence-starter
python -m src.compound_intelligence.issue_challenger --input examples/engineering_issues.json
```

The bundled **fictional UX issues** have competing explanations and proposed counterexamples. The command returns structured JSON showing:

| Output | Why it matters |
| --- | --- |
| `ranked_issues` | Explainable priority *hints* from supplied scores |
| `competing_hypotheses` | Alternatives to test instead of prematurely choosing a fix |
| `chosen_next_test` | Smallest estimated falsifiable experiment |
| `brief_id` | Stable identity for a reproducible engineering handover |
| `build_execution_allowed: false` | Proposals never silently become actions |

**Want to see the output as a page?** Generate an accessible, standalone HTML report:

```bash
python -m src.compound_intelligence.issue_report \
  --input examples/engineering_issues.json \
  --output issue-challenger-report.html
```

Open `issue-challenger-report.html` locally. No JavaScript, login or network service is needed. The report marks proposed tests as **not yet executed**.

[Walkthrough](docs/ENGINEERING_ISSUE_CHALLENGER.md) · [Browser accessibility smoke coverage](docs/BROWSER_QA.md)

## Explore the compound intelligence loop

```text
Problem → Competing hypotheses → Independent checks
                                         ↓
                                  Durable evidence
                                         ↓
                           Retrieve verified examples
                                         ↓
                           Compare baseline vs assisted
```

Three runnable entry points:

| Try | Command | What you get |
| --- | --- | --- |
| Evidence and replay | `python -m src.compound_intelligence.demo --workspace ./local-data --iterations 3` | A rejection and verification example with locally saved results |
| Knowledge reuse | `python -m src.compound_intelligence.learning_loop --fixture` | A verified example retrieved for a different fictional task |
| Paired evaluation | `python -m src.compound_intelligence.ab_evaluation --fixture` | A baseline-versus-assisted comparison and durable receipt |

The offline `--fixture` demonstrations are **scripted simulations**. They show the *mechanics*, **not measured improvements in a real language model**. Optional local [Ollama](https://ollama.com) adapters can produce real model proposals on your machine; the repository does not download or start a model.

## What's included

- **Independent checking:** bounded typed extraction, static patch reference matching and explicit rejection paths; generated code is never executed.
- **Persistent knowledge:** local SQLite evidence, verified-only exemplars, replayable receipts and recoverable bounded fixture jobs.
- **Measured comparison:** multi-model experiment scaffolding, benchmark scores and paired memory-assisted evaluation with clear limitations.
- **Visible evidence:** read-only, self-contained HTML reports and an offline experiment dashboard.
- **Safe OSS workflow:** automated tests, actual headless-Chrome report smoke coverage, and read-only public feedback indexing.

<details>
<summary>Capabilities, limitations and more CLI examples</summary>

Read [the full version-by-version guide](docs/VERSION_GUIDE.md), [architecture](docs/ARCHITECTURE.md), [v1.0 knowledge retrieval](docs/V1.0.md) and [v1.1 evaluation](docs/V1.1.md).

To run the tests:

```bash
python -m unittest discover -s tests -v
```

To generate the separate offline dashboard:

```bash
python -m src.compound_intelligence.scheduler enqueue --id first-demo
python -m src.compound_intelligence.scheduler tick
python -m src.compound_intelligence.dashboard --queue-db local-data/v06/queue.sqlite3 --output local-data/dashboard.html
```

</details>

## Built for experimentation, not unchecked autonomy

This is an **educational open-source starter**, not an always-on engineering agent. Issue rankings use user-supplied ratings, model outputs are untrusted proposals, and no GitHub issue authorizes code execution, a merge or privileged infrastructure access. The example code does **not** demonstrate general AI intelligence, causal self-improvement or secure execution of submitted source.

[Security and public boundaries](docs/SECURITY.md) · [Release notes](RELEASE_NOTES.md) · [Tagged MVP release v1.1.0](https://github.com/esheenj/compound-intelligence-starter/releases/tag/v1.1.0)

## Get involved

Try an example, open a small reproducible issue, or propose a bounded improvement. Good contributions include counterexamples, independent validators, synthetic test data, documentation and accessibility improvements.

**[Contributing guide](CONTRIBUTING.md)** · **[Good first contributions](docs/GOOD_FIRST_ISSUES.md)** · **[Safe validator extensions](docs/EXTENDING.md)** · **[Discussions via GitHub issues](https://github.com/esheenj/compound-intelligence-starter/issues)**

Please don't publish employer or customer data, proprietary strategies, credentials or private infrastructure details. This project is independent of the AI services mentioned above and is licensed under [MIT](LICENSE).
