# Esheen Labs — launch and website embed kit

The historical **11 November 2026** baseline was **7 public repositories + 21 hosted add-ons = 28 demo pages**, with 28/28 public HTTPS Chrome acceptance. As of **12 November 2026**, the published collection has **11 independent open-source repositories + 21 additional browser add-ons = 32 demo pages**. This is not 32 separately published repositories. The four newer standalone repositories passed their own source/Chrome tests and successful GitHub Pages publication, while the older 28 deep-interaction browser sweep is a separate test. Live HTTPS Chrome acceptance [run 43064815195](https://github.com/esheenj/compound-intelligence-starter/actions/runs/43064815195) recorded 28/28 PASS on the tested interactions; merged release [PR #83](https://github.com/esheenj/compound-intelligence-starter/pull/83), source checks [43065431211](https://github.com/esheenj/compound-intelligence-starter/actions/runs/43065431211) and publisher [43065506885](https://github.com/esheenj/compound-intelligence-starter/actions/runs/43065506885) succeeded. That does not certify real-world agent identity, user-device coverage, accessibility, production safety or adoption.

**Directory:** https://esheenj.github.io/compound-intelligence-starter/

**Code:** https://github.com/esheenj

## Value proposition

**Esheen Labs builds practical open-source AI, UX and developer experiments you can run, inspect, challenge and improve—with reproducible tests and no accounts for the included examples.**

Make every public post about one demonstrated problem, not a large demo count. Link to a runnable example first, the collection second. Do not claim synthetic identity or receipt experiments verify real actors.

## Website feature card

Copy-paste for a possible "From Esheen Labs" section on the separate Sigma Code website (https://sigmacode.co.za/). **This code is not deployed there**, and the site's source/hosting repository is not verified. Integrate with the existing design system instead of replacing site styling or product messaging.

~~~html
<section aria-labelledby="esheen-labs-title" style="padding:1.5rem;border:1px solid currentColor;border-radius:1rem;max-width:48rem">
  <p>From Esheen Labs · Open Source</p>
  <h2 id="esheen-labs-title">Useful tools. Open source. Real tests.</h2>
  <p>Explore 32 public demo pages across agent experiments, UX journeys, design systems and testing. Run an example, inspect source, and help improve it—without signing in for the included examples.</p>
  <p><a href="https://esheenj.github.io/compound-intelligence-starter/" rel="noopener noreferrer">Explore the public tools</a>
  · <a href="https://github.com/esheenj/compound-intelligence-starter" rel="noopener noreferrer">Contribute on GitHub</a></p>
  <small>Educational examples, not certified services or real agent authorization.</small>
</section>
~~~

Prefer native linked cards, not an iframe: accessible, mobile-friendly, indexable, no extra embeds or data collection. The figure 28 is point-in-time, not automatically updated; use "Explore our open-source tools" if the site cannot track changes. A standalone /labs route can introduce three featured tools, with direct demo/source/contribute links and the full directory as a secondary navigation target.

## Six shareable story angles

| Theme | Direct demo | Clear scope |
| --- | --- | --- |
| Signed agent challenge | https://esheenj.github.io/compound-intelligence-starter/signed-agent.html | Real P-256 demo signatures on disposable local keys; no trusted identity |
| AgentProof | https://esheenj.github.io/compound-intelligence-starter/agentproof.html | Synthetic receipt integrity, not proof of action |
| AgentOps replay | https://esheenj.github.io/compound-intelligence-starter/agentops.html | Illustrates missing terminal receipt and duplicate replay |
| Approval gates | https://esheenj.github.io/flow-state-machine-oss/approval.html | Fictional approve, deny and reopen; no real permissions |
| Journey mapping | https://esheenj.github.io/flow-state-machine-oss/journey.html | Fictional UX friction and handoffs, not measured users |
| Experiment worksheet | https://esheenj.github.io/data-table-interactions-oss/experiment.html | Descriptive guardrails, not causal proof |

## Copy for a first technical launch

### Public one-liner

"Open-source AI and UX experiments with reproducible tests, honest limitations and browser demos you can try immediately."

### LinkedIn / developer community

"What happens when an AI agent claims it finished work, but never produces a completion receipt? Esheen Labs has a runnable offline replay demo that makes missing evidence visible, plus approval-gate examples that demonstrate denial and recovery. Try the public tools, inspect source and tell me which edge case we should test next: https://esheenj.github.io/compound-intelligence-starter/"

### Demo clip, approximately 40 seconds

Show one fictional agent receipt -> trigger an intentionally missing/duplicate receipt -> show the visible rejection or hold -> show the source/test link -> invite a reproducible issue, not an upvote.

## Distribution order

1. **GitHub:** pin up to six meaningful repositories on the personal profile; enhance an optional public profile README, repository descriptions/topics, genuine good-first issues, release notes and repository social preview images.
2. **Website:** Sigma Code homepage feature and optional dedicated Labs page, linking to the existing no-login public directory. Preserve the separate commercial brand and do not embed private repositories.
3. **Teaching posts:** publish a code-backed lesson on DEV Community/Hashnode and a concise LinkedIn demonstration; link to the exact tool in context rather than repeating a generic announcement.
4. **Hacker News Show HN:** nominate one substantial, independently usable demo rather than the directory. Engage genuinely and never solicit votes.
5. **Product Hunt:** hold for a narrow, polished product with demonstrable user value, images and a product story; do not count each toy demo as a separate business.
6. **Curated open-source lists and relevant communities:** submit only to places with a genuine topical fit and acceptable self-promotion rules, one helpful contribution at a time.
7. **Packaging only when ready:** GitHub Action, CLI, npm or PyPI packages should be real published, versioned, tested products with maintained installation instructions. A static playground is not proof of a package.

## Conversion and measurement

Discovery -> direct demo -> inspect source/evidence -> open an issue or contribute -> optional voluntary support (only after verified payout setup) or separately scoped UX/integration consulting. Keep original MIT educational examples accessible for free.

The existing OSS controller and GitHub Actions can produce one weekly release-evidence report from actual merged work. Social post publication is separate, only where the account connection/permission exists. Avoid mass autoposting and new paid schedulers (R0 new recurring infrastructure cost). Track exact demo URL, campaign/source post URL, CI and public-browser receipt, genuine feedback/first external PR and qualified enquiries. GitHub aggregate traffic may help where authorized, but do not imply comprehensive visitor attribution or add surveillance to a no-tracking site.

Never share client/employer source, private AI controls, secrets, SIGMA trading or financial intelligence, or unverified safety/performance claims in marketing material.
