# Runner Preflight v0.2.0 — Linux preview with opt-in observation

**Runner Preflight** is a small, offline, read-only Rust CLI for comparing declared CI-job requirements with a runner inventory. This release adds a complementary **Python 3 standard-library observer for an authorized local Linux machine**, making it practical to produce an inventory rather than invent every field.

## What's new from v0.1.0

- New `scripts/collect_linux_runner.py` accepts a strict `runner-preflight-job-v1` requirements document (64 KiB maximum) and observes Linux OS/architecture, free disk on the selected workspace filesystem, `/proc/meminfo` available memory and presence of only the requested executable names.
- x86-64 and ARM64 example job requirements under `fixtures/`.
- Duplicate-key, nonfinite JSON, invalid-token, oversized input and symlink rejection with deterministic tests; no shell, subprocess, network request or host mutation.
- Output is a `runner-preflight-input-v1` manifest accepted by the same Rust evaluator. **Labels and installed Rust targets remain unverified and empty**, and tools are checked for name presence, not versions or competence. A READY result is not actual GitHub runner registration or scheduling readiness.
- Updated Rust source package version `0.2.0`, committed lockfile, Linux x64/ARM64 extracted-source CI and dependency licence/advisory checks.

## Assets

- `runner-preflight-linux-x86_64` — Rust executable for GitHub-hosted Linux x86-64
- `runner-preflight-linux-aarch64` — Rust executable for GitHub-hosted Linux ARM64
- `runner-preflight-source.zip` — complete original, standalone Rust and Python source, tests, synthetic fixtures and independent CI
- `SHA256SUMS` — digests of both executables and source ZIP
- `BUILD_INFO.txt` — source commit and build runner receipts

## Run locally

From the downloaded source ZIP on your own Linux x86-64 host (use `job-linux-arm64.json` on ARM64):

```sh
unzip runner-preflight-source.zip
cd runner-preflight
python3 scripts/collect_linux_runner.py --job fixtures/job-linux-x64.json --workspace . > observed.json
cd rust
cargo test --locked
cargo run --locked -- inspect --input ../observed.json --format json
```

You may instead evaluate a manually prepared synthetic inventory with `inspect --input FILE --format json`. Exit codes are 0 READY, 1 WARN, 2 HOLD, 3 invalid input/usage.

## Scope and assurance

This is a **component-prefixed GitHub prerelease** inside Compound Intelligence Starter, **not** a separate `runner-preflight` repository, crates.io publication, Rust/WASM web app, signed binary, live Oracle runner deployment or commercial service. The collector never reads credentials, hostnames, user names, IP addresses, private runner labels, environmental secrets or process inventories; no output leaves the local machine unless you deliberately redirect/share it.

GitHub-hosted CI tests the **extracted ZIP on both x86-64 and ARM64** and validates the Rust CLI, observed manifest, synthetic negative cases, cargo-deny RustSec advisories, dependency licence/source constraints and release integrity. The hashes prove contents match the release assets; these binaries are not code-signed or independently audited. The existing v0.1.0 release remains available and unchanged.

R0 added recurring infrastructure expenditure; no trading, Oracle or control-plane authority.
