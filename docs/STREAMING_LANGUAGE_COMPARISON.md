# Python, Rust and Go: cross-architecture streaming experiment

Original, synthetic educational source only. No private project code, real event schemas, model prompts, credentials, customer data, financial strategy, or execution authority.

## Question

Does a CPU-heavy parse/deduplicate/aggregate task benefit from moving outside Python, and do the language trade-offs remain useful on **ARM64 as well as x86-64**?

## Input contract

Each newline-delimited ASCII record has exactly four tab-separated fields: event ID (E plus eight decimal digits), category (atlas/beacon/cobalt/delta), kind (PASS/FAIL/RETRY), canonical signed integer from -10000 to 10000. No leading plus, leading zero or negative zero; maximum 256 bytes per row. Invalid records are rejected; first valid record wins when IDs duplicate. The result reports accepted, duplicates and rejects plus twelve category/kind count and sum lines in stable order.

These fields are deliberately fictional. The program is not a durable broker, cryptographic validator, production analytics service or exchange/Commander adapter.

## Reproduce

Build and test with standard toolchains:

- `cargo test --manifest-path experiments/streaming_benchmark/rust/Cargo.toml`
- `cargo build --release --manifest-path experiments/streaming_benchmark/rust/Cargo.toml`
- `GO111MODULE=off go test ./experiments/streaming_benchmark/go`
- `go build -o experiments/streaming_benchmark/go/stream-aggregator experiments/streaming_benchmark/go/main.go`
- `python -m unittest tests/test_streaming_benchmark.py -v`
- `python -m experiments.streaming_benchmark.compare --rows 100000 --trials 5 --output local-data/streaming-benchmark.json`

No third-party runtime libraries or model inference are involved. The existing public GitHub Actions platform runs standard `ubuntu-24.04` and `ubuntu-24.04-arm` jobs on the exact proposed commit; no new paid runners or permanent services.

## What is measured

The generator introduces deterministic duplicates, unknown kinds, malformed IDs and bad amounts. A separate hand-checked golden fixture validates the reference's expected output. The benchmark then verifies **byte-identical output** for each run. It warms processes, rotates execution order, and reports five batch wall-time trials, median, nearest-rank p95, rows/second, SHA-256 of input and expected output, runner label, architecture and source SHA.

Process startup is included in timing. The test does **not** measure steady-state event latency, memory, CPU energy, network operations, WAL persistence or real-world systems. ARM and x86 hosted machines are not matched CPUs: compare the language ratios **within** each runner, never claim an architecture-level speedup from cross-machine absolute times.

## Adoption criteria

Prefer Python for research, inference, low-volume orchestration and workflow glue. Promote Rust into a bounded native component only after repeatable correctness and workload measurements justify build/maintenance overhead. Prefer Go for simple independent services when its ergonomics and resource profile beat the alternatives. Source-only measurements do not commission any production worker or grant finance/host authority. Require two permissioned project consumers before building a shared abstraction.

Rollback: revert this isolated experiment; no running systems or jobs depend on it.
