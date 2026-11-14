# Runner Preflight v0.1.0 — Linux preview

A small, offline, read-only Rust CLI for comparing a **supplied** CI runner inventory with declared job requirements.

## Assets

- `runner-preflight-linux-x86_64` — compiled for GitHub-hosted Linux x86-64
- `runner-preflight-linux-aarch64` — compiled for GitHub-hosted Linux ARM64
- `runner-preflight-source.zip` — deterministic, independently testable standalone source and CI package
- `SHA256SUMS` — digests for all three downloadable files
- `BUILD_INFO.txt` — exact source revision and separate build runner details

The source package includes MIT licensing, pinned Cargo.lock and Rust 1.100 toolchain, synthetic fixtures, stand-alone README/CI, a dependency policy, and per-file source provenance. Use only on a platform you authorize.

## Example

```sh
unzip runner-preflight-source.zip
cd runner-preflight/rust
cargo test --locked
cargo run --locked -- inspect --input ../fixtures/ready-x64.json --format json
```

Expected result: a JSON report with `status: READY`. The provided alternate fixtures demonstrate `WARN` and `HOLD`.

## Security and scope

This preview **does not** inspect live machines or GitHub's scheduling state, check tool versions, register or restart runners, install anything, use tokens, send data over a network or grant execution/trading authority. It only checks declared JSON inputs; declarations are not proof of live system state.

The release workflow is gated by successful x86-64 and ARM64 ZIP-extracted tests and RustSec/licence/source checks. SHA-256 verifies published file integrity against the manifest; artifacts are not code-signed, independently audited, or a promise of suitability for production.

This is a **component-prefixed release inside the existing Compound Intelligence Starter repository**. It is not an independent `runner-preflight` GitHub repository, crates.io package or hosted web app.

Additional recurring infrastructure expenditure: R0.
