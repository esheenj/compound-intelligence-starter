//! Original synthetic Rust/Python interoperability experiment.
//! This module performs no file I/O, network access, or external execution.

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use std::collections::HashSet;

const MAX_ITEMS: usize = 200_000;
const MAX_TOTAL_BYTES: usize = 8_000_000;

fn classify_core(values: &[String]) -> Result<(usize, usize, usize), &'static str> {
    if values.len() > MAX_ITEMS {
        return Err("batch too large");
    }
    let (mut accepted, mut duplicate, mut rejected) = (0, 0, 0);
    let mut bytes = 0usize;
    let mut seen = HashSet::<&str>::new();
    for item in values {
        bytes = bytes
            .checked_add(item.len())
            .ok_or("batch bytes too large")?;
        if bytes > MAX_TOTAL_BYTES {
            return Err("batch bytes too large");
        }
        let valid = (1..=64).contains(&item.len())
            && item
                .as_bytes()
                .iter()
                .all(|&b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'_' || b == b'-');
        if !valid {
            rejected += 1;
        } else if seen.insert(item.as_str()) {
            accepted += 1;
        } else {
            duplicate += 1;
        }
    }
    Ok((accepted, duplicate, rejected))
}

/// Return (accepted unique, duplicate valid, rejected invalid) counts.
///
/// The Python boundary accepts a sequence of strings. Invalid identifiers are
/// counted, while invalid input types and excessive batches raise exceptions.
#[pyfunction]
fn classify_ids(values: Vec<String>) -> PyResult<(usize, usize, usize)> {
    classify_core(&values).map_err(PyValueError::new_err)
}

#[pymodule]
fn rust_ids(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(classify_ids, m)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::classify_core;

    #[test]
    fn mixed_and_repeatable() {
        let values = ["a", "b", "a", "A", "_", "a-b", "c1", ""]
            .into_iter()
            .map(String::from)
            .collect::<Vec<_>>();
        assert_eq!(classify_core(&values), Ok((5, 1, 2)));
        assert_eq!(classify_core(&values), Ok((5, 1, 2)));
    }

    #[test]
    fn unicode_is_not_ascii() {
        let values = ["x".repeat(64), "x".repeat(65), "é".into(), "x".repeat(64)];
        assert_eq!(classify_core(&values), Ok((1, 1, 2)));
    }

    #[test]
    fn batch_count_guard() {
        let values = vec!["x".to_string(); 200_001];
        assert_eq!(classify_core(&values), Err("batch too large"));
    }

    #[test]
    fn total_bytes_guard() {
        let values = vec!["x".repeat(64); 125_001];
        assert_eq!(classify_core(&values), Err("batch bytes too large"));
    }
}
