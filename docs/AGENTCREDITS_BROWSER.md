# AgentCredits Ledger Studio — fictional browser MVP

This public page explains the smallest end-to-end sequence for agent usage credits with entirely **synthetic integer units**. It is not a payment service, API provider billing integration, customer money wallet, real durable ledger or automatic agent authorization.

Direct static source: site/agentcredits.html. Its eventual GitHub Pages URL is https://esheenj.github.io/compound-intelligence-starter/agentcredits.html . The page contains its own example journal, accepts user-edited JSON locally and sends no data to an API.

## Explore the four stages

- **Grant:** give a fictional account 100 non-monetary units.
- **Reserve:** place 40 units on hold under a unique request ID.
- **Settle:** record 25 consumed units and release the unspent held balance.
- **Refund:** return five settled units to the available balance.

The resulting sample balance is 80 available, zero held and 20 spent. A repeated event ID with identical content is ignored, not charged twice.

Use the one-click controls to simulate overspending, conflicting duplicate IDs and oversized refunds. They must reject the entire submitted journal, clearing any displayed balances rather than showing a partial or misleading result. Reset restores the valid fixture. The browser rejects malformed/duplicate JSON keys, floats, boolean credit amounts, missing fields and invalid state transitions. This browser demo has a 64 KiB UTF-8 input limit and a maximum of 100 synthetic events.

See the original reference implementation in src/compound_intelligence/agentcredits.py and its unit tests in tests/test_agentcredits.py. The browser is a bounded teaching simulator and does not maintain data across page reloads. A real system additionally needs identity attestation, persistent serializable transactions, externally reconciled costs, price versioning, compliance and separate scoped execution authority.

The release should only be called live when actual source CI, GitHub Pages publishing and independent HTTPS Chrome acceptance are each verified at their own exact revisions. This tool belongs to the existing public repository, not a new independent repo. Zero additional recurring infrastructure spend (R0); no private SIGMA, Cortex, Commander, trading or employer/client content.
