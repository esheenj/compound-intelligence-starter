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

A public source repository **is not itself a live hosted website**. GitHub requires an authorized repository administrator to configure **Settings → Pages → Build and deployment → Source → GitHub Actions** for `esheenj/compound-intelligence-starter`. The ordinary GitHub Actions token cannot enable this setting by itself.

Once Pages is enabled, the [Publish CI-verified public OSS directory](../.github/workflows/publish-showcase.yml) workflow runs only after the `Tests` workflow **successfully completes for a `main` push**. It checks out that exact revision, rejects outdated revisions when `main` has moved, confirms Pages is enabled with Actions as source, stages just `site/index.html` as `index.html` with `.nojekyll`, and deploys using GitHub's first-party Pages actions. Pull requests cannot publish.

If the Pages workflow reports an unavailable site, enable Pages once and trigger a subsequent tested `main` source change. Do not claim the site is live based solely on a successful source CI job or a guessed URL.

## Final HTTPS acceptance

After a real successful deploy, read the job's actual `page_url`. Open that HTTPS address in a browser, confirm seven repository cards, source and contribution links, accessible skip navigation, no external asset loads and narrow/desktop layouts. Only after this independent verification should the repository README advertise a clickable hosted URL.

**Limits:** The directory itself is a read-only gateway; it is not proof of package adoption, model capability, complete accessibility, security certification or paid production hosting. The bundled projects each have independent tests, rights and release states. Do not add private incubator history or company/client data to the directory.

No extra recurring infrastructure cost.
