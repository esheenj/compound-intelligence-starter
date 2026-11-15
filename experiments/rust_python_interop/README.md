# Rust/Python parity qualification — private-product prerequisite, public research only

This **isolated, original educational experiment** tests whether a Rust function packaged with
PyO3/maturin has the same behavior as a pure Python reference. It does not create a new repo,
convert arbitrary Python code, modify Oracle/Commander/Cortex, or publish a package.

## Contract

`classify_ids(["a", "a", "A", "a-b", ""])` returns `(2, 1, 2)`.

- Valid identifiers: 1–64 bytes of ASCII lowercase letters, digits, underscore or hyphen.
- First valid occurrence counts as accepted; later occurrences count as duplicates.
- Other string values count as rejected; invalid member types raise `TypeError`.
- Lists/tuples are accepted. Maximum 200,000 entries and 8,000,000 UTF-8 bytes.
- Oversized batches raise `ValueError`. Counts, not timings, are compared.

## Qualification (requires Rust 1.100, Python 3.10+ and maturin)

From this directory:

```sh
cargo fmt --all -- --check
cargo clippy --all-targets -- -D warnings
cargo test
python -m pip install "maturin==1.16.0"
maturin build --release --out dist --interpreter python --compatibility off
python -m pip install --no-index --find-links dist rust-id-interop-pilot
python -m unittest discover -s tests -v
```

The `--compatibility off` wheel is **host-specific test evidence**, not a portable manylinux
release. Cargo.lock was generated independently on x64 and ARM64 and matched byte-for-byte (SHA-256 `64ccd24daeb8a53f113258a79a0b1f32f7503e250358776293022db374604c43`), then committed. Exact-head CI must now prove locked builds. Before external package release, perform dependency/license review, portable wheel-target qualification and meaningful benefit measurement. Do not publish to PyPI or claim a production speedup from this experiment.

## Evidence boundaries

The Python baseline was initially checked locally with six pure-Python unit tests.
Initial native compilation, wheel imports and 10 Python/Rust parity tests passed in the 15 November CI matrix (x64 Python 3.10/3.12 and ARM64 Python 3.12); exact-head locked requalification remains separate. This experiment is a capability prerequisite, not one of the proposed 30
developer-magnet products. Added recurring infrastructure spend R0.
