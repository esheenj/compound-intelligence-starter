# Runner Preflight — Rust prototype

An offline, read-only CLI that checks a **supplied** runner inventory against declared CI job requirements. It explains architecture mismatches, missing labels or tools, insufficient disk/memory, missing Rust targets, and low resource headroom.

**Maturity:** public source branch prototype, not an independent repository or released binary. Input declarations are not verified facts about a runner. This utility cannot provision, diagnose platform-level job scheduling failures, or repair a host.

## Build and run

```sh
cd experiments/runner_preflight/rust
cargo fmt --all -- --check
cargo clippy --all-targets --locked -- -D warnings
cargo test --locked
cargo run -- inspect --input ../fixtures/ready-x64.json --format json
```

The candidate uses Rust 1.100.0 (2024 edition). The tool has a committed Cargo.lock captured identically from x64 and ARM64 qualification jobs. The standalone release still requires dependency/license/advisory review and exact-head locked-source CI.

## Input

One versioned JSON file, no more than 64 KiB and not a symlink. See fixtures/ for examples. The schema is `runner-preflight-input-v1`.

- `runner`: `os`, `arch`, `labels`, `disk_free_mb`, `memory_free_mb`, `tools`, `rust_targets`.
- `job`: `os`, `arch`, `required_labels`, `min_disk_mb`, `min_memory_mb`, `required_tools` and optional `rust_target`.
- `os` is one of `linux`, `macos`, `windows`; `arch` is `x86_64` or `aarch64`. Tool/target comparisons use exact identifiers and **do not** verify installed tool versions.

## Output and exit code

The output schema is `runner-preflight-result-v1`, with a status and ordered findings. All messages are generic and do not echo supplied inventory values.

| Exit | Status | Meaning |
|---|---|---|
| 0 | READY | The declared inventory meets all specified requirements |
| 1 | WARN | Declared requirements met but resources have low headroom |
| 2 | HOLD | One or more declared requirements are unmet |
| 3 | invalid input | Usage, JSON, schema, invalid token, nonregular/oversized input |

Files are read-only. The default command performs no network access, mutation, runner restart, package installation, GitHub authentication or financial operation.

## Tests and release conditions

`cargo test`, `cargo clippy` and x64/ARM64 CI are required before this prototype can be promoted. Build artifacts, dependency auditing, exact-head CI, an independent capability-named repository, final name availability and clean release provenance remain separate gates. Additional recurring spend is R0.
