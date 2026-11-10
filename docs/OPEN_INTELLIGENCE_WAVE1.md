# Open Intelligence — Wave 1 original offline previews

Issue #40 is the umbrella, and issue #41 is Wave 1 execution. This is a source-level **proposed add-on** in Compound Intelligence Starter, not an independent package/repository, a production AI identity attestation system or financial billing platform.

## Two-minute evaluation (Python 3.10+, no dependencies or accounts)

Run at the repository root:

    python -m src.compound_intelligence.agentproof --demo
    python -m src.compound_intelligence.agentcredits --demo
    python -m unittest tests.test_agentproof tests.test_agentcredits -v

Each command is offline. Both demonstrations use original, fictional data. Structured JSON output separates result status from the scope of what was actually tested.

## AgentProof receipt verifier

AgentProof tests a simple manifest with schema agentproof.receipts.v1. Each event carries a contiguous integer sequence, unique event ID, claimed producer string, state, JSON payload and lowercase SHA-256 hash over canonical JSON bytes. It rejects tampering, missing producer declarations, duplicate IDs, gaps and invalid fields. Its parser rejects duplicate JSON keys and non-finite constants.

This checks *the consistency of the supplied data*, not the truth of a model claim, the identity of its producer, whether a purported action happened, external signature authority or whether the hash was created by someone trustworthy. Unsigned manifests can be fabricated or edited along with their hashes.

To validate your own local manifest (the JSON schema is illustrated by the built-in fictional_manifest function):

    python -m src.compound_intelligence.agentproof --input ./manifest.json

Exit code 0 means the supplied receipt manifest was internally consistent, 1 means structural/integrity failure, and 2 means failed parsing or file read. Keep sensitive data out of input and logs.

## AgentCredits synthetic accounting

AgentCredits applies a fully local in-memory event journal, schema agentcredits.journal.v1. All credits are *synthetic integers*, not money or actual provider credits.

- Grant increases available credits.
- Reserve moves available credits into held credits for a unique request ID.
- Settle releases any unspent held credits and books actual spent credits.
- Refund reclaims no more than previously settled and unrefunded credits.
- Replaying the same event ID with identical fields has no additional effect; conflicting duplicate IDs fail closed.
- Insufficient credits, repeat settlements, oversized refunds and malformed events fail without publishing a partial balance.

The demo journal grants 100 fictional credits, reserves 40, repeats that event, settles 25, then refunds 5. The final balance is 80 available, zero held and 20 spent. The process is stateless; passing the exact journal again deterministically regenerates the same result. It is **not** a concurrent database, financial ledger, API billing product, or guarantee of exactly-once delivery. Production use requires persistent storage, transaction isolation, authentication, price versioning and independent reconciliation.

To replay a local journal:

    python -m src.compound_intelligence.agentcredits --input ./journal.json

## Extraction and release gates

1. Review source and limitations in a pull request; keep this work independent from private Cortex/Commander and SIGMA.
2. Confirm unit tests pass at exact PR head under Python 3.10 and 3.12, including negative cases.
3. Document new repository names and license review before extracting standalone source histories. Never publish private prototype histories or secrets.
4. Record the promoted SHA and, if a browser interface is built, separately verify the deployed HTTPS UI.
5. Maintain R0 additional recurring spend.

Public education and composable standards first; no live execution permissions, real credits or hidden infrastructure.
