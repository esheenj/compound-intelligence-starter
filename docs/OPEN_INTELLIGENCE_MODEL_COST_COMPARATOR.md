# Model Cost Comparator — original offline source

This is a small reproducible public AI cost-estimation utility. **All model prices and token counts are supplied by the caller.** No real AI model, provider billing, invoice, market price, latency or quality is measured.

Run from this repository using Python 3.10+ (standard library, offline):

    python -m src.compound_intelligence.model_cost_comparator --demo
    python -m src.compound_intelligence.model_cost_comparator --demo --html /tmp/model-cost.html
    python -m unittest discover -s tests -p 'test_model_cost_comparator.py' -v

The demo intentionally returns exit 1 because two entirely fictional models cost respectively USD 0.000380 and 0.000460 for their supplied usage and the budget is USD 0.000400. This illustrates the risk of treating an average or a cheap model as evidence of quality. An input using zero rates under the same budget can pass; the tool does not assess whether those rates are real.

A local JSON file can be passed using the --input argument. Its schema is model-cost-comparison.v1 and it includes a pinned price_book_revision label, a decimal string budget_usd, a rates array and a usage events array. Each rate contains model_id, input_usd_per_million, output_usd_per_million as decimal strings with up to six fractional digits. Each event has unique event_id, model_id, integer input_tokens and output_tokens. Decimal arithmetic produces exact 12-place output USD estimates for this bounded contract.

Every listed model must have at least one usage event; an unobserved model must not appear artificially free. The comparator ignores identical repeated event IDs; it rejects conflicting duplicates, unknown models, invalid rates and malformed events without publishing partial totals. Versioning the supplied prices helps reproducibility, but the revision label is not proof that a provider used those rates.

Return codes: 0 when all supplied scenarios are within the budget, 1 when any valid scenario exceeds it, and 2 for malformed inputs or output errors. The generated HTML file is local, escaped, without scripts or external assets.

**Limits:** Different workloads for different models cannot prove comparative efficiency, capability, latency or accuracy. Actual provider spend depends on authenticated metering, price tier, cached tokens, discounts, taxes and billing reconciliation that are deliberately excluded. This is not an independent repository or hosted web application yet. No private Cortex, Commander, SIGMA or financial access is involved; additional recurring spend R0. Work item: https://github.com/esheenj/compound-intelligence-starter/issues/42 .
