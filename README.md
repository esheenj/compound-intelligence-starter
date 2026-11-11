# Compound Intelligence Starter

**Challenge assumptions. Verify outcomes. Reuse what works.**

Turn an engineering problem into competing, falsifiable hypotheses and a reproducible test-first brief. Explore a small, offline reference implementation of evidence-backed AI experiments, durable memory and model comparisons.

[![Tests](https://github.com/esheenj/compound-intelligence-starter/actions/workflows/test.yml/badge.svg)](https://github.com/esheenj/compound-intelligence-starter/actions/workflows/test.yml)
[![Release](https://img.shields.io/github/v/release/esheenj/compound-intelligence-starter)](https://github.com/esheenj/compound-intelligence-starter/releases/tag/v1.1.0)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB)

**Zero required subscriptions · Python standard library · Runs offline · MIT licensed**

**Support Esheen Labs (pending recipient activation):** [See the no-script support page](https://esheenj.github.io/compound-intelligence-starter/support.html) and [fiat/crypto/Sponsors setup guide](docs/PAYMENT_CHANNELS.md). No payment links, receiving wallets, GitHub Sponsors recipient or product billing is currently activated; all public examples remain free.

**Wave 3 Signed Agent Challenge (real cryptographic primitive):** [Try genuine local P-256 Web Crypto signature checks](https://esheenj.github.io/compound-intelligence-starter/signed-agent.html) and [run the dependency-free Node.js verifier with durable local nonce replay tests](docs/OPEN_INTELLIGENCE_SIGNED_CHALLENGE.md): `node --test tests/test_agent_auth.mjs`. Valid signatures prove possession of an **already locally enrolled key**, not a verified real-world agent identity or execution authority. 7 independent public repos + 21 browser add-ons passed **28/28 independent HTTPS Chrome acceptance** on 11 November 2026 (merged-main [run 43064815195](https://github.com/esheenj/compound-intelligence-starter/actions/runs/43064815195)). No additional recurring infrastructure spend.

**Wave 3 Agent Trust & Identity Lab:** [Try the original offline public demo](https://esheenj.github.io/compound-intelligence-starter/agent-trust.html) and [read the bounded Python claim-checker tests](docs/OPEN_INTELLIGENCE_AGENT_TRUST.md): `python -m src.compound_intelligence.agent_trust_claims --demo`. Explores declared agent origin/fingerprint/capability, revocation, challenge nonce reuse and checksum tampering. Matching claims **never mean verified agent identity**. No private keys or real agent execution.

**Wave 3 Explainable Decision Review Lab:** [Try the offline interactive review tool](https://esheenj.github.io/compound-intelligence-starter/decision-review.html) or [run the fictional Python reference](docs/OPEN_INTELLIGENCE_EXPLAINABLE_REVIEW.md) using `python -m src.compound_intelligence.explainable_review --demo`. Shows source versions, opposing evidence, high-impact review and declared confidence-method limits. No model inference, human authorization or real execution.

**Wave 3 Model Disagreement Lab:** [Try the offline browser tool](https://esheenj.github.io/compound-intelligence-starter/model-disagreement.html) or [run the original Python reference](docs/OPEN_INTELLIGENCE_MODEL_DISAGREEMENT.md) with `python -m src.compound_intelligence.model_disagreement --demo`. It exposes false consensus, supplied-reference mismatch, missing responses and abstention; no live models or truth certification.

**Wave 3 Context Preservation Benchmark:** [Measure exact synthetic handover fidelity](docs/OPEN_INTELLIGENCE_CONTEXT_PRESERVATION.md) — `python -m src.compound_intelligence.context_preservation --demo`. Three fictional checkpoints expose missing critical facts, stale source versions, contradictory values, evidence-label promotion and invented claims. This does **not** measure real LLM understanding or grant execution authority.

**Wave 2 approval-gate simulation:** [Offline review, denial, expiry and action-report replay](docs/OPEN_INTELLIGENCE_WAVE2_APPROVALS.md) — `python -m src.compound_intelligence.agent_review_gate --demo`. Fictional actor claims only; `execution_authority: NONE`.


**Wave 2 AgentOps preview:** [Offline usage metering, trace reconciliation and retry-safe replay](docs/OPEN_INTELLIGENCE_WAVE2.md) — `python -m src.compound_intelligence.agentops_replay --demo`. Deterministic simulated receipts only: no private worker, real execution, provider billing or live exchange.



**More Wave 1 guard utilities:** [Prompt Regression Guard and Agent Budget Guard](docs/OPEN_INTELLIGENCE_WAVE1_PART2.md) demonstrate critical-case regression detection and duplicate-safe synthetic cap admission; examples are offline and do not evaluate real AI quality or spend real credits.

**Open Intelligence Wave 1 — original offline previews:** [AgentProof receipt verifier and AgentCredits synthetic ledger](docs/OPEN_INTELLIGENCE_WAVE1.md). Try `python -m src.compound_intelligence.agentproof --demo` and `python -m src.compound_intelligence.agentcredits --demo`. These are local educational tools, not factual-truth attestation, payment services or live autonomous execution. [Public roadmap](https://github.com/esheenj/compound-intelligence-starter/issues/40) · [Wave 1 issue](https://github.com/esheenj/compound-intelligence-starter/issues/41).

**[Open the GitHub-deployed seven-MVP directory](https://esheenj.github.io/compound-intelligence-starter/)** — All seven public repository entry pages and twenty interactive add-ons passed independent real-HTTPS Chrome acceptance on 11 November 2026: [Actions 43036020756 (merged-main attempt 2)](https://github.com/esheenj/compound-intelligence-starter/actions/runs/43036020756) **PASS**. See the [exact acceptance scope, preceding transient failure and limitations](docs/PUBLIC_DIRECTORY_DEPLOY.md#final-https-acceptance). This is 27 Pages URLs within seven repositories, not twenty-seven standalone repositories.

**[Support and sustainability](docs/SUPPORT_AND_SUSTAINABILITY.md)** · **[Public/private intelligence boundary](docs/PUBLIC_INTELLIGENCE_BOUNDARY.md)** — original, fictional open-source examples; no unverified payment links or private trading and finance disclosures.

**Explore the wider [Esheen Labs public MVP collection](docs/PUBLIC_OSS_MVP_COLLECTION.md)** — seven independent, runnable tools spanning AI experiments, interface flows, form UX, design tokens, tables and synthetic visual comparisons.

**New developer directory:** The [public OSS project directory source](site/index.html) offers a single browsable index of seven runnable tools and contribution paths. To preview the exact website bundle locally, run `mkdir -p dist && python scripts/stage_showcase.py --output dist/pages`, then serve `dist/pages` with Python's localhost server. [Pages deployment and live browser checks](docs/PUBLIC_DIRECTORY_DEPLOY.md) are recorded separately.

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

**New: explore alternatives interactively, still offline.** Generate a second self-contained report and filter between fictional issues, expand competing hypotheses and inspect what would disprove each one:

```bash
python -m src.compound_intelligence.issue_explorer \
  --input examples/engineering_issues.json \
  --output issue-explorer.html
```

Open `issue-explorer.html` locally. The **actual Python challenger** selects the cheapest proposed falsifiable test; a small browser script only shows and hides already-rendered information. Its content-security policy pins the exact script hash and blocks network connections. No AI API, telemetry or account is involved, and no experiment is executed. The existing script-free static report above remains available for strict no-JavaScript environments.

[Offline hypothesis explorer guide](docs/OFFLINE_HYPOTHESIS_EXPLORER.md) · [Explorer source](src/compound_intelligence/issue_explorer.py)

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

## Python versus Rust: a small evidence-driven experiment

See the [cross-language validator pilot](docs/CROSS_LANGUAGE_VALIDATOR_PILOT.md): original synthetic records, dependency-free Python and Rust implementations, invalid-input fixtures and a CI parity check. It is a **format demonstration**, not signature checking, operational authorization or a performance claim.

## New: offline public MVP wave planner

A small, independently runnable reference tool helps prioritize at most three fictional open-source MVP review candidates, with explainable scoring, invalid-input tests and explicit no-execution/no-publication boundaries. It uses a completely synthetic fixture; it does **not** verify GitHub, rights or deployed applications.

```sh
python -m src.compound_intelligence.mvp_portfolio --input examples/mvp_portfolio.json
python -m unittest tests.test_mvp_portfolio -v
```

See [the MVP Wave Planner guide](docs/MVP_WAVE_PLANNER.md). This is **one additional source-first tool inside this existing repository**, not a new standalone repository or an independently hosted MVP.
