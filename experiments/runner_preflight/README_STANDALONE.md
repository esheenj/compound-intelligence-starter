# Runner Preflight

Offline, read-only CI runner requirement matching with deterministic JSON reports.

Runner Preflight evaluates a **supplied** inventory against a declared job specification. It **does not** inspect a host automatically, register CI runners, diagnose GitHub scheduling or billing, install software, access credentials, or repair a server. It does not grant financial or agent execution authority.

## Quick start

Install Rust 1.100.0 with Cargo on Linux x86-64 or ARM64. From the extracted repository root:

```sh
cd rust
cargo fmt --all -- --check
cargo clippy --all-targets --locked -- -D warnings
cargo test --locked
cargo run --locked -- inspect --input ../fixtures/ready-x64.json --format json
```

Expected report status: `READY`. Other supplied synthetic fixtures produce `WARN` or `HOLD`. An incompatible inventory is a diagnostic finding, not permission to change the machine.

## Contract

The input JSON (maximum 64 KiB, regular file only, no symlinks) has `schema: "runner-preflight-input-v1"`, plus:

- `runner`: `os`, `arch`, `labels`, `disk_free_mb`, `memory_free_mb`, `tools`, and `rust_targets`
- `job`: `os`, `arch`, `required_labels`, `min_disk_mb`, `min_memory_mb`, `required_tools`, and optional `rust_target`

`os` is `linux`, `macos`, or `windows`. `arch` is `x86_64` or `aarch64`. Tool and target comparisons match exact identifiers; they do not discover installed versions. The output uses `runner-preflight-result-v1`, a status and generic machine-readable findings.

| Exit code | Meaning |
|---|---|
| 0 | READY: declared requirements matched |
| 1 | WARN: requirements matched, low resource headroom |
| 2 | HOLD: one or more requirements missing |
| 3 | Invalid input or CLI usage |

## Independent source and verification

This release-ready source tree was assembled from the explicitly allowlisted, original, **public** files in [Compound Intelligence Starter](https://github.com/esheenj/compound-intelligence-starter/tree/main/experiments/runner_preflight). The export contains no history, unrelated source, private instructions or account credentials. See `SOURCE_PROVENANCE.json` for the exact parent source commit and hashes of each included file. `rust/Cargo.lock` is committed. The included `.github/workflows/ci.yml` independently tests x86-64 and ARM64 and checks dependency advisories, licenses and sources.

MIT licensed (see `LICENSE`). Do not advertise an executable as signed, audited for all vulnerabilities, verified as running on Oracle, or commercially supported merely because source tests pass. The source archive can be imported into a new, functionally named GitHub repository after normal repository creation and final release checks.

No added recurring infrastructure spend or paid dependency is required.
