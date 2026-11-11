# Public open-source MVP directory

The original [static directory source](../site/index.html) presents **seven verified public OSS MVP repositories** with commands, GitHub source links and contribution paths. It contains no images, external assets, JavaScript, visitor analytics or private integrations.

## Run locally

```sh
mkdir -p dist
python scripts/stage_showcase.py --output dist/pages
python3 -m http.server 8000 --directory dist/pages --bind 127.0.0.1
```

Open `http://127.0.0.1:8000` locally. The directory is static; it does not execute the seven tools in the browser or collect information about you. Each command is intended for its respective **cloned public repository**. `stage_showcase.py` refuses overwriting an existing output folder and validates that the links refer to all seven approved public repositories. CI checks this source stage with Python tests and real headless Chrome at 320/375/812/1440px.

## GitHub Pages deployment readiness

**Deployment update, 9 November 2026:** The already-installed GitHub Actions publishing workflow successfully deployed the seven-MVP directory at [the GitHub-returned Pages address](https://esheenj.github.io/compound-intelligence-starter/) after the owner enabled Pages. Exact publish run: [42485873469, attempt 2](https://github.com/esheenj/compound-intelligence-starter/actions/runs/42485873469). The separate live HTTPS smoke on 10 November is recorded below. A public source repository **is not itself proof that its hosted site was independently verified**. GitHub requires an authorized repository administrator to configure **Settings → Pages → Build and deployment → Source → GitHub Actions** for `esheenj/compound-intelligence-starter`. The ordinary GitHub Actions token cannot enable this setting by itself.

Once Pages is enabled, the [Publish CI-verified public OSS directory](../.github/workflows/publish-showcase.yml) workflow runs only after the `Tests` workflow **successfully completes for a `main` push**. It checks out that exact revision, rejects outdated revisions when `main` has moved, confirms Pages is enabled with Actions as source, stages the exact allowlisted seven HTML files (`index.html`, `mvp-wave.html`, `agentops.html`, `agentproof.html`, `agentcredits.html`, `model-cost.html`, `model-fit.html`) plus `.nojekyll`, and deploys using GitHub's first-party Pages actions. Pull requests cannot publish.

If the Pages workflow reports an unavailable site, enable Pages once and trigger a subsequent tested `main` source change. Do not claim the site is live based solely on a successful source CI job or a guessed URL.

## Final HTTPS acceptance

**Latest complete check, 11 November 2026:** Original offline browser Model Cost Comparator and Local Model Fit Planner [source PR #61](https://github.com/esheenj/compound-intelligence-starter/pull/61) merged `0693a89dbee5083b26c64511d040377d2fc2f75b`; exact main Python 3.10/3.12 and Chrome [CI run 42987496897](https://github.com/esheenj/compound-intelligence-starter/actions/runs/42987496897) **PASS** and first-party Pages [42987504800](https://github.com/esheenj/compound-intelligence-starter/actions/runs/42987504800) **SUCCESS**. Exact source checks isolated a stage variable-shadowing defect and a stale inventory assertion, both corrected before merge.

The independent fixed-URL HTTPS acceptance [PR #62](https://github.com/esheenj/compound-intelligence-starter/pull/62) checks **23 published URLs**: seven public repository homepages and sixteen interactive add-ons. Exact PR head `621c46aae60f67ceea6edbc2e1bbbcbaae407870` [Chrome run 42988815837](https://github.com/esheenj/compound-intelligence-starter/actions/runs/42988815837) **PASS** with source CI [42988815809](https://github.com/esheenj/compound-intelligence-starter/actions/runs/42988815809) PASS. Merged main `a59bd2b541d7ee317a89932d39060005349971c8` independent HTTPS [42988973386](https://github.com/esheenj/compound-intelligence-starter/actions/runs/42988973386) **PASS** and Python/Chrome [42988973443](https://github.com/esheenj/compound-intelligence-starter/actions/runs/42988973443) **PASS**, and Pages [42989030927](https://github.com/esheenj/compound-intelligence-starter/actions/runs/42989030927) **SUCCESS**. The log explicitly reports `pages_tested: 23` and `state: PASS`. The acceptance script's own wrong button-selector syntax was repaired before merge; no test was bypassed.

These are **23 independently checked browser URLs, not 23 repositories or production AI services**. Model costs derive from user-supplied fictional token prices; local-model fit derives from user-supplied fictional memory/storage/context estimates. Chrome tests do not certify model quality, actual provider invoices, device performance, screen readers, WCAG conformance, independent identity or financial execution authority.



**11 November 2026 consolidated check:** [Independent public HTTPS Chrome acceptance run 42985295917](https://github.com/esheenj/compound-intelligence-starter/actions/runs/42985295917) **PASS** on the exact PR head of [#52](https://github.com/esheenj/compound-intelligence-starter/pull/52). The emitted machine-readable report records `pages_tested: 21`, `state: PASS`: seven distinct public repository homepage URLs and fourteen interactive add-on URLs. Browser interactions include positive and negative synthetic scenarios, with 320px and 1440px viewports for add-ons. The reviewed PR was merged at source `79f44452893628fe48ba49bfafa03733084bda9b`. An exact separate merged-main acceptance run is still a distinct evidence item and should be inspected before claiming that run also passed.

The count refers to **21 hosted URL pages, seven independent public repositories, fourteen browser add-ons**. It is not 21 packages or AI marketplace agents. Chrome checks are not physical-device acceptance, complete feature exploration, a screen-reader test, WCAG certification, producer attestation or actual financial/agent authority.



**10 November 2026 smoke:** An external Chrome browser loaded all seven linked project entry pages and all four add-on URLs over HTTPS. For the directory and planner, the deployment under review was [run 42753978570](https://github.com/esheenj/compound-intelligence-starter/actions/runs/42753978570) at `a8b8aa073cb8e5c18b3ccc931dc1d6b8bbd9f5be`. The planner proposed three fictional reviews and rejected malformed JSON. Error Recovery stopped after three failed attempts and recovered in a separate run. Control Audit rejected malformed JSON and restored the default findings. The Experiment Worksheet held an apparent conversion improvement when errors exceeded its fictional threshold. This smoke does not cover assistive technology, physical devices or every flow in each project.

For future releases, after a real successful deploy, read the job's actual `page_url`. Open that HTTPS address in a browser, confirm seven repository cards, source and contribution links, accessible skip navigation, no external asset loads and narrow/desktop layouts. Only after this independent verification should the repository README advertise a clickable hosted URL.

**Limits:** The directory itself is a read-only gateway; it is not proof of package adoption, model capability, complete accessibility, security certification or paid production hosting. The bundled projects each have independent tests, rights and release states. Do not add private incubator history or company/client data to the directory.

No extra recurring infrastructure cost.
