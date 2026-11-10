# Open Intelligence — Wave 2 AgentOps replay and usage ledger

This first Wave 2 source slice is a local **educational simulation** built from wholly fictional events. It does not use private Cortex, Commander, SIGMA or any privileged execution capability. It does **not** prove that an AI action occurred, that a producer identity is genuine, or that credits represent real API-provider charges.

## Try the smallest complete working slice

Python 3.10+, repository root, no dependencies or subscriptions:

    python -m src.compound_intelligence.agentops_replay --demo

The example emits deterministic JSON with one completed synthetic task, one usage record of seven made-up units and one repeated identical event ID. The repeat is ignored, rather than double-counted.

Make an offline HTML report:

    python -m src.compound_intelligence.agentops_replay --demo --html /tmp/agentops-demo.html

Open the resulting local HTML file. It is script-free and escapes untrusted content. It is **not** a remotely hosted dashboard.

## Recover uncertainty, not fictional success

Try the truncated journal:

    python -m src.compound_intelligence.agentops_replay --truncated-demo

This intentionally exits **1**: the supplied journal contains STARTED and USAGE but has **no terminal event**. The run is recorded as INCOMPLETE, not COMPLETED. An actual autonomous worker would need a separately authenticated durable receipt source before resuming or declaring an operation successful.

The input contract is \`agentops.event-journal.v1\`. An object contains a schema string and ordered events. Each event has a stable \`event_id\`, \`run_id\`, per-run consecutive integer \`sequence\`, \`agent_id\` and \`kind\`: STARTED, USAGE, COMPLETED, FAILED. USAGE also requires integer \`units\` from 1 to one billion. Run IDs and event IDs are restricted to simple bounded identifiers; malformed or contradictory events fail closed and reveal no partial accounting.

Repeated **identical** event IDs are ignored. A repeat with conflicting content, sequence gap, changed agent, missing STARTED, or event after a terminal status is rejected. Events from separate runs may interleave. Failed runs remain FAILED, not successful.

Provide a local JSON event journal:

    python -m src.compound_intelligence.agentops_replay --input ./fictional-events.json

Exit 0: schema valid and every supplied run has a terminal status. Exit 1: valid but at least one run is incomplete. Exit 2: malformed inputs or report write failure.

## Engineering limits and next steps

The test suite includes retry/restart replay without double charging, conflicting duplicates, sequence gaps, tampering, unknown types, failed terminals, interleaved runs and HTML escaping. Test it with:

    python -m unittest discover -s tests -p 'test_agentops_replay.py' -v

This is **not** a persistent transaction store, recovery supervisor, exact-once delivery protocol, production money ledger, provider token meter, or authentication system. Before production integration, add durable storage, transaction isolation, externally verifiable producer identities, receipt signatures, rate limits, independent billing reconciliation and operational authorization.

The tool is proposed as a source-level public add-on in the existing repository. It is not a separate release/package, nor a newly published Pages app. Source and GitHub CI evidence must be recorded independently from any deployment and browser acceptance.

No new recurring cloud spend; additional budget R0. Track progress at [Wave 2 issue #42](https://github.com/esheenj/compound-intelligence-starter/issues/42).
