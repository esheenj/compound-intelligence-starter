# Agent Review Gate — synthetic approval and event replay

This is original public reference software. It helps developers **model** approval processes, negative cases and incomplete decisions with fictional data. It never authorizes real execution or signs a grant.

## Run offline (Python 3.10+, standard library)

    python -m src.compound_intelligence.agent_review_gate --demo
    python -m src.compound_intelligence.agent_review_gate --pending-demo
    python -m src.compound_intelligence.agent_review_gate --denied-demo
    python -m unittest discover -s tests -p 'test_agent_review_gate.py' -v

The approved example demonstrates a REQUESTED → APPROVED → ACTION_REPORTED transition. That final status means an *input event claims the action happened*; it is NOT independently verified or executed. The same approval event repeats and is deduplicated.

The pending example exits 1, and the denied example exits 0 with status DENIED; neither grants any real authority. Invalid examples or file parse errors exit 2.

A local input journal is an object with schema \`agent-review.journal.v1\` and an \`events\` list. Event fields: stable \`event_id\`, \`request_id\`, consecutive \`sequence\` per request, claimed \`actor\`, \`kind\`, immutable \`scope\` and deterministic integer \`tick\`. APPROVED also contains a future \`expires_tick\`; actions reported past that expiry are rejected.

Event kinds: REQUESTED, APPROVED, DENIED, REVOKED and ACTION_REPORTED. A reviewer cannot equal the requester string. Expiry is checked against supplied ticks, never the real wall clock. Duplicate identical event IDs do not apply twice; conflicting duplicates fail without partial output. Denial or revocation is terminal. Any request lacking a final denial, revocation or action report remains unresolved.

Provide a local file with:

    python -m src.compound_intelligence.agent_review_gate --input ./fictional-approval-events.json

## Important security boundary

All actor names and timestamps are supplied by the input. This is not authentication, cryptographic signing, legal compliance, human identity validation, secure quorum, live policy enforcement, exchange permission or a production approval service. It has no real execution tool, wallet or network access. Do not wire it to a private Cortex/Commander/SIGMA executor without separately scoped verified grants, actor identity and actual financial authorization.

No recurring infrastructure spending; R0 additional. Source/test/Pages/external browser verification remain separate. Work tracked in [Wave 2 issue #42](https://github.com/esheenj/compound-intelligence-starter/issues/42).
