# Worked example: from a service request to a reviewable handoff

**A Sigma Code UX Engineering capability study · fictional reference, not a client case study**

> Status: illustrative design and test plan. This repository does **not** connect the five separate OSS examples, deploy a CRM, collect customer data, measure conversion, or implement this workflow end-to-end. No client results, accessibility conformance, revenue or return on investment are claimed.

## The hypothetical business problem

A small repair-services business receives requests from different channels. An incomplete request can be lost, a repeated click can create conflicting instructions, and an operations colleague may struggle to find records requiring attention. The proposed experience should make the customer’s next step clear and the staff handoff inspectable.

**Completely invented scenario:** one fictional customer requests repair of a kettle; the UI uses non-identifying reference **SERVICE-104**. No names, addresses, contact details or real orders are needed to explore the patterns.

### A cross-product UX storyboard

| Stage | What a customer or employee sees | Reusable public example | Proposed acceptance check |
| --- | --- | --- | --- |
| 1. Guided intake | Service type, issue summary and an error summary if incomplete; draft can be restored | [Form Experience Patterns](https://esheenj.github.io/form-experience-kit-oss/) | An empty required issue stays on the step, gives actionable feedback and preserves other valid fields; a valid fictional draft survives local export and restore |
| 2. Reviewable state | A fictional request moves from DRAFT to REVIEW_REQUIRED and only then to CONFIRMED when its guard is satisfied | [UI Workflow State Machine](https://esheenj.github.io/flow-state-machine-oss/) | A disallowed direct transition is rejected without mutating the saved state; an accepted transition is present in the replayable journal |
| 3. Staff review | An invented `SERVICE-104` row can be filtered to items awaiting review; the chosen ordering applies to CSV export | [Data Table Interaction Toolkit](https://esheenj.github.io/data-table-interactions-oss/) | Filtering plus stable sorting yields a predictable row order; export includes the matching fictional records across pages without silently changing the filter |
| 4. Consistent expression | The same abstract hierarchy and status treatment could appear in the form, review and list views | [Design System Foundations](https://esheenj.github.io/design-system-foundations-oss/) | Token aliases resolve to the expected CSS output; calculate an example text/background contrast ratio, then perform separate human and accessibility review |
| Supporting mobile pattern | Small-screen step labels, focus placement, error recovery and back-navigation | [Mobile Journey Patterns](https://esheenj.github.io/mobile-first-flow-kit-oss/) | Review focus after validation failure, layout at narrow widths and safe return to the previous step; never claim physical-device certification from this example |

**Important integration boundary:** the five demonstrations use their own fictional fixtures and APIs. The names `SERVICE-104`, `DRAFT`, `REVIEW_REQUIRED` and `CONFIRMED` below are **illustrative design vocabulary**, not a published shared JSON schema. The linked demos do not currently exchange a record, share storage, or run together. Building and checking those interfaces would be a separate project.

## Illustrative journey acceptance scenarios

These are *requirements to evaluate*, not executed cross-product test results.

1. **Missing customer information:** the user attempts Next without an issue description. Expected: inline guidance plus error summary, no submitted record, focus directed to the error. Actual behaviour must be evaluated in a future integrated prototype.
2. **Controlled state progression:** an invented `SERVICE-104` request cannot move directly from DRAFT to CONFIRMED. Expected: a deterministic guard denies the action and leaves the journal unchanged.
3. **Idempotent retry hypothesis:** a duplicate Next or confirm action should not create duplicate work. The current public examples do not implement an integrated backend or durable exactly-once workflow; a production specification would require request identity, persistence and reconciliation.
4. **Staff triage:** a user selects `REVIEW_REQUIRED` and sorts by age. Expected: an auditable, stable order and export of only matching fictional rows. The existing table example has a different supported sample schema; this scenario is a proposed adaptation, not a demonstrated table integration.
5. **Design consistency:** the same role-based colour and spacing tokens should be used across mobile and desktop views, without relying on colour alone to communicate status.
6. **Evidence before launch:** run automated acceptance tests, real keyboard and assistive-technology review, data-handling review and actual-user observation on a future integrated version. Synthetic checks alone cannot prove usability or accessibility.

## Smallest honest implementation slice

**Proposed**, not implemented in this case study:

- Build one local-only fictional repair-request prototype with a defined `SERVICE-104` data contract.
- Reuse or adapt the patterns from the five MIT examples only after checking license and actual compatibility.
- Add tests for incomplete intake, stale/duplicate transitions, recovery, filtered staff review and safe text rendering.
- Record what was tested in source, automated CI, deployed preview and independent browser review **separately**.
- Run user research with consenting participants before making claims about conversion, user satisfaction or saved labour.

## How this connects to a commercial enquiry

The free examples are a source-first engineering portfolio, not a commercial SaaS subscription. A separately scoped Sigma Code engagement might start with a UX friction review of an **authorized** customer journey, a prototype and a measurable implementation handoff. Customer information should be provided privately, not in public GitHub issues.

**Potential customer question:** “Where do people abandon your intake, where do staff lose context, and which transitions are not recoverable?”

**Proposed output of a paid engagement:** a scoped UX findings brief, a validated prototype and acceptance criteria; pricing and availability are not represented here.

## Sources and preservation

Public examples (independent demonstrations, no shared backend):

- https://github.com/esheenj/form-experience-kit-oss
- https://github.com/esheenj/flow-state-machine-oss
- https://github.com/esheenj/data-table-interactions-oss
- https://github.com/esheenj/design-system-foundations-oss
- https://github.com/esheenj/mobile-first-flow-kit-oss

No new dependencies, API credentials, telemetry, automated submissions, private trading/control-plane code, additional subscriptions or recurring infrastructure spend are required for this document.
