# Two offline AI decision-support browser tools

This release productizes the existing **original, source-level** Model Cost Comparator (Wave 2) and Local Model Fit Planner (Wave 3) as static, educational browser pages. These are **not** two new GitHub repositories, external model services, cloud calculators or real performance benchmarks. Both are intentionally standalone HTML files, local-only, and do not send requests, store inputs or require subscriptions.

## Model Cost Comparator

Open `site/model-cost.html` locally or, **only after Pages deploy**, the hosted URL `https://esheenj.github.io/compound-intelligence-starter/model-cost.html`.

The editable `model-cost-comparison.v1` sample contains an invented two-model price book, a pinned revision label, a US-dollar budget string, and three fictional token events, one of which repeats an identical ID. The browser calculates exact decimal amounts using BigInt: rate USD per million tokens is normalized to integer millionths and multiplied by integer token counts, yielding exact USD values with 12 decimals. The sample costs are 0.000380000000 and 0.000460000000 USD; under the supplied 0.000400000000 budget, the second is **over**.

Try the **Raise sample budget**, **Conflicting retry**, **Remove model usage**, and **Reset** controls. Conflicting repeat IDs and listed models without any observed events are rejected without publishing partial results. Rates use nonnegative decimal strings (at most six fractional digits), token counts are bounded integers, and the browser supports up to 100 events and 64 KiB UTF-8. The reference CLI in `src/compound_intelligence/model_cost_comparator.py` supports larger documents and has separate unit tests.

### Boundary

These are **caller-supplied fictional rates and workloads**, not live OpenAI/Anthropic/provider prices or invoices. Price-book revision IDs are mere labels, not signed provenance. The browser does not measure model quality, speed, context success, discounts, cached tokens, tax or paid usage. Comparable costs require representative workloads and authenticated real billing before making spending decisions.

## Local Model Fit Planner

Open `site/model-fit.html` locally or, **only after Pages deploy**, `https://esheenj.github.io/compound-intelligence-starter/model-fit.html`.

The editable `local-model-fit.v1` fixture has a completely fictional 3072 MiB RAM device, 512 MiB reserved, 2048 MiB free storage and a 4096-token context requirement. Its invented small model needs 1750 MiB estimated runtime RAM and 850 MiB storage, so its calculated memory headroom is 810 MiB. The invented large model fails memory and storage constraints. Try **Constrained device**, **Require longer context**, **Duplicate model ID**, and **Reset**. Invalid or contradictory profiles fail closed; all outputs are labeled as *supplied estimate*, not measured hardware compatibility.

The actual device may require more RAM for KV cache, framework, GPU offload, operating-system activity and model-specific runtime behavior. No downloads, runtime benchmarking, hardware probes, licensing review, neural inference or device enrollment happen. The Python reference remains in `src/compound_intelligence/local_model_fit.py`.

## Acceptance and safety

Both pages are statically allowlisted by `scripts/stage_showcase.py`, which independently hashes and checks CSP/source safety, and the existing Chrome CI tests their positive and negative paths and narrow/desktop layout. Source CI and actual GitHub Pages publishing are **separate** from independent live HTTPS Chrome acceptance; do not claim the page is live based only on the existence of its URL. The previous public collection had seven repositories and fourteen browser add-ons (21 URLs). When both new pages have **actually passed** Pages and live Chrome checks, it will have seven repositories, sixteen add-ons and 23 public URLs.

No private SIGMA, Cortex or Commander data, real trading/payment or infrastructure authority, client/employer IP, model credentials or external network calls. Additional recurring spend **R0**.

Source roadmap: [Wave 2 #42](https://github.com/esheenj/compound-intelligence-starter/issues/42), [Wave 3 #43](https://github.com/esheenj/compound-intelligence-starter/issues/43), [master #40](https://github.com/esheenj/compound-intelligence-starter/issues/40).
