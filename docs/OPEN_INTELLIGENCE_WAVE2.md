# Open Intelligence — Wave 2: agent traces and claim evidence

Two original, source-only, offline Python reference add-ons under the [public roadmap](https://github.com/esheenj/compound-intelligence-starter/issues/40). Input and output are fictional educational metadata. These are not standalone packages or repos, hosted pages, live agent observability services or factual-truth verifiers.

Python 3.10+, standard library only; no login, provider API, downloads, database or account.

## Agent Flight Recorder — metadata-only lifecycle replay

From repository root:

    python -m src.compound_intelligence.agent_flight_recorder --demo
    python -m src.compound_intelligence.agent_flight_recorder --gap-demo  # deliberately exits 1
    python -m unittest tests.test_agent_flight_recorder -v

Schema agentflight.events.v1: object with "schema" and 1–500 "events". Each event has exactly "event_id", "job_id", "attempt" (integer 1–30) and "phase" (STARTED, SUCCESS, FAILURE, CANCELLED). There is deliberately NO field for free-form prompts, outputs, credentials, full logs or tool inputs. Data minimization is not arbitrary-secret redaction.

Deterministic replay rejects terminals without matching starts, overlapping attempts, noncontiguous retries, conflicting duplicate event IDs, unrecognized fields and malformed types. Repeated identical event IDs count once. Unfinished starts report MISSING_TERMINAL_RECEIPT; retry after success reports RETRY_AFTER_SUCCESS. Output is a stable JSON summary of distinct events, duplicates and ordered per-job states without raw tool payloads.

This reconstructs the supplied list; it does not confirm whether a real action occurred, authenticate its producer, prevent external side effects, restore from a production database or guarantee exactly-once delivery. The input file is local-only, limited to 256 kB. Exit 0: valid with no review observations; 1: review observations; 2: invalid input.

## Claim–Evidence Mapper — exact excerpt match

    python -m src.compound_intelligence.claim_evidence_map --demo
    python -m src.compound_intelligence.claim_evidence_map --gap-demo  # deliberately exits 1
    python -m unittest tests.test_claim_evidence_map -v

Schema claim-evidence.fixtures.v1: 1–100 "sources" with "source_id" and "excerpt" plus 1–100 "claims" with "claim_id", "text", "quote", "cited_source_ids". It does not fetch URLs or inspect remote documents.

Each supplied quoted string must literally occur within every cited supplied excerpt; the report distinguishes NO_CITATION, SOURCE_NOT_SUPPLIED, NO_TESTABLE_QUOTE and QUOTE_NOT_FOUND_IN_ALL_CITED_SOURCES. ALL_QUOTES_FOUND_LITERAL_ONLY verifies only literal text presence. It cannot verify semantic entailment, interpretation, contextual completeness, authorship, provenance, consent or whether the claim is true. The output contains statuses and source/claim IDs, not raw source text.

The local CLI uses strict duplicate-key and non-finite JSON rejection with a 256 kB input cap. Exit 0: all literal quotes found; 1: unresolved claims; 2: invalid input.

## Reproducibility, limits and release definition

    python -m unittest discover -s tests -v
    python -m src.compound_intelligence.agent_flight_recorder --demo
    python -m src.compound_intelligence.claim_evidence_map --demo

GitHub Actions checks Python 3.10/3.12, existing staging and Chrome regressions. Require exact PR-head green tests, merged source SHA and publicly visible source. These CLI modules are not Pages UIs, so a GitHub Pages workflow does not certify their behavior. A later accessible browser preview would need separate staging and browser acceptance.

Original MIT-licensed implementations use fictional identifiers only. Never publish private control-plane data, customer/employer source, actual agent logs, secrets, financial strategies, proprietary prompts or exchange execution interfaces. No recurring infrastructure cost increase (R0).

Follow-on roadmap: synthetic approval-gate state-machine, usage metering and a user-friendly browser playground, all without production execution privileges.
