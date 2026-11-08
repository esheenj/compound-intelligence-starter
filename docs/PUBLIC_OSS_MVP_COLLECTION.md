# Esheen Labs — public open-source MVP collection

**Seven independent, source-first tools. No accounts, private backends or subscription required for their basic examples.** Every listed repository now provides a tested static Pages artifact and a guarded deployment workflow; GitHub Pages activation and live HTTPS checks are **not yet verified**. Each repository owns its own tests, license, limitations and release status. Public GitHub access is **not** a claim of a deployed website, published npm package, independent accessibility certification or real-world adoption.

## Developer-friendly public directory

The original [single-page OSS directory](../site/index.html) includes all seven source repos, reproducible command examples and contribution links. It is entirely static, offline-readable, without analytics or remote assets. [Source packaging, real Chrome QA and one-time GitHub Pages setup](PUBLIC_DIRECTORY_DEPLOY.md) are documented separately; **this does not yet certify a hosted website**.

## Start with a real runnable example

| Tool | Try it locally | Useful output |
| --- | --- | --- |
| [Compound Intelligence Starter](https://github.com/esheenj/compound-intelligence-starter) | `python -m src.compound_intelligence.issue_challenger --input examples/engineering_issues.json` | Hypotheses, counterexamples, an unexecuted next-test brief and evidence workflow |
| [Design System Foundations](https://github.com/esheenj/design-system-foundations-oss) | `node bin/compile.mjs examples/theme.json` | Validated tokens and an offline interactive CSS/contrast playground |
| [Mobile-first Flow Kit](https://github.com/esheenj/mobile-first-flow-kit-oss) | `npm test && npm run demo` | Responsive browser journey with guarded recovery and state-model tests |
| [Data Table Interactions](https://github.com/esheenj/data-table-interactions-oss) | `npm test && npm run demo` | Filtering, stable sorting, pagination and semantic table demo |
| [Flow State Machine](https://github.com/esheenj/flow-state-machine-oss) | `npm test && npm run replay` | Guarded transitions and replayable fictional workflow journals |
| [Form Experience Kit](https://github.com/esheenj/form-experience-kit-oss) | `npm test && npm run demo` | Multi-step fictional form with versioned local draft restore |
| [Visual Regression Starter](https://github.com/esheenj/visual-regression-starter-oss) | `npm test && npm run demo` | Fictional P3 comparison with a static script-free visual report and explicit review verdict |

Each command runs **inside the repository named in that row** after cloning it. Use Python 3.10+ for Compound Intelligence, Node 20+ for the JavaScript tools, and a local static-file server for browser demos as documented in each README. Tool-specific optional test dependencies are documented separately. No repository in this collection represents a live exchange, trading broker, payment platform or privileged AI agent.

## A practical product-development path

1. **Define what to test:** Use Compound Intelligence Starter to contrast plausible explanations and select a falsifiable experiment. It produces a proposal, not an authorized build.
2. **Model the interface:** Use Flow State Machine or Mobile-first Flow Kit to make state changes and invalid paths explicit.
3. **Build the interaction:** Study Form Experience Kit, Data Table Interactions and Design System Foundations for original synthetic patterns.
4. **Inspect results:** Use Visual Regression Starter's deliberately narrow offline pixel comparator. Actual accessibility and visual-product acceptance still require human/browser review.
5. **Record evidence:** Prefer linked tests, exact source revisions, honest limitations and small reproducible contributions rather than unverified performance claims.

## Public contribution rules

- Use fictional or openly reusable test data, with clear provenance. Never submit employer/client material, live customer details, passwords, private AI infrastructure, signing keys or proprietary financial strategies.
- Read each repository's `README.md`, `CONTRIBUTING.md` and `SECURITY.md` when present. Respect each project's boundaries; some are intentionally educational instead of production-ready.
- Treat an issue, model output or example workflow as an **untrusted proposal**. It does not authorize code execution, deployment, infrastructure access or a change to another project.
- Share an exact reproduction, expected versus actual behavior, a negative case, and the smallest measurable test. Avoid promises of adoption or future support that have not been evidenced.

**Distribution:** These are independently published GitHub source repositories. There is no implied shared runtime, dependency, hosted deployment or automatic release of any private incubator. The private Esheen Labs control plane and related financial systems remain outside this public collection.
