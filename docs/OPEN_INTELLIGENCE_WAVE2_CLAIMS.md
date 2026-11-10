# Wave 2 extension — Claim–Evidence Mapper

This is an original, offline **literal source-excerpt alignment** utility under [Open Intelligence roadmap #40](https://github.com/esheenj/compound-intelligence-starter/issues/40). It complements—not replaces—the already merged [AgentOps usage and replay](OPEN_INTELLIGENCE_WAVE2.md). No production AI, network retrieval, model calls or actual truth evaluation.

## Two-minute run

Requires Python 3.10+ and only the standard library, from the repository root:

    python -m src.compound_intelligence.claim_evidence_map --demo
    python -m src.compound_intelligence.claim_evidence_map --gap-demo   # expected exit 1
    python -m unittest tests.test_claim_evidence_map -v

The fictional fixture contains two source excerpts and two mapped claims. A correct demo yields ALL_QUOTES_FOUND_LITERAL_ONLY for both. A changed invented quote in the gap demo produces QUOTE_NOT_FOUND_IN_ALL_CITED_SOURCES and a failing exit.

## Local input contract

Schema claim-evidence.fixtures.v1:
- 1–100 sources: exact objects containing source_id and excerpt (1–2,000 characters)
- 1–100 claims: exact objects containing claim_id, text, quote and cited_source_ids
- Each claim may cite up to eight distinct source IDs. IDs are stable, bounded metadata.
- Any cited source that lacks the exact quote is flagged, even if another source contains the quote.
- Missing citation, unavailable source or empty quote are each distinct unresolved outcomes.
- JSON duplicate keys, non-finite numbers, forged fields, invalid IDs and oversized input are rejected.

    python -m src.compound_intelligence.claim_evidence_map --input ./fictional-claims.json

Input is capped at 256 kB; all processing is local. Exit 0 means all supplied quotes were found literally in every cited supplied excerpt; 1 means at least one claim remains unresolved; 2 means invalid input. Reports contain only IDs and statuses, not the raw source excerpts.

## Do not misrepresent verification

Matching text is NOT proof that:
- an author's identity or document provenance is genuine;
- an excerpt was quoted in its full surrounding context;
- a model's claim logically follows from a quotation;
- any asserted claim is correct, independently observed, unbiased or lawful.

The utility performs no semantic inference or external source retrieval. It does not attest an AI agent's actions, grant permissions or handle real private evidence. Never submit client/employer records, real secrets, private financial data, proprietary prompts or actual legal documents as public example fixtures.

Source change is MIT-compatible, fictional and has zero added recurring infrastructure expenditure (R0). GitHub Python 3.10/3.12 CI regression and public source merge are release gates; there is no hosted browser page or independent HTTPS UI for this CLI utility. A separate browser adaptation would require new tests and publication evidence.
