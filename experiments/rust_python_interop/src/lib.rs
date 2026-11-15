//! Original synthetic Rust/Python interoperability experiment.
//! This module performs no file I/O, network access, or external execution.

use pyo3::exceptions::{PyTypeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyList, PyString, PyTuple};
use std::collections::HashSet;

const MAX_ITEMS: usize = 200_000;
const MAX_TOTAL_BYTES: usize = 8_000_000;

#[derive(Default)]
struct Classifier {
    seen: HashSet<String>,
    accepted: usize,
    duplicate: usize,
    rejected: usize,
    total_bytes: usize,
}

impl Classifier {
    fn push(&mut self, value: &str) -> Result<(), &'static str> {
        self.total_bytes = self
            .total_bytes
            .checked_add(value.len())
            .ok_or("batch bytes too large")?;
        if self.total_bytes > MAX_TOTAL_BYTES {
            return Err("batch bytes too large");
        }
        let valid = (1..=64).contains(&value.len())
            && value
                .as_bytes()
                .iter()
                .all(|&b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'_' || b == b'-');
        if !valid {
            self.rejected += 1;
        } else if self.seen.insert(value.to_owned()) {
            self.accepted += 1;
        } else {
            self.duplicate += 1;
        }
        Ok(())
    }

    fn counts(self) -> (usize, usize, usize) {
        (self.accepted, self.duplicate, self.rejected)
    }
}

#[cfg(test)]
fn classify_core(values: &[String]) -> Result<(usize, usize, usize), &'static str> {
    if values.len() > MAX_ITEMS {
        return Err("batch too large");
    }
    let mut classifier = Classifier::default();
    for value in values {
        classifier.push(value)?;
    }
    Ok(classifier.counts())
}

fn classify_sequence<'py>(
    items: impl Iterator<Item = Bound<'py, PyAny>>,
    item_count: usize,
) -> PyResult<(usize, usize, usize)> {
    // Check the Python container before allocating/copying any element in Rust.
    if item_count > MAX_ITEMS {
        return Err(PyValueError::new_err("batch too large"));
    }
    let mut classifier = Classifier::default();
    for item in items {
        let text = item
            .cast::<PyString>()
            .map_err(|_| PyTypeError::new_err("all values must be strings"))?;
        // Unicode character count is a lower bound on UTF-8 byte count.
        // Reject a very large Python string before converting it to Rust UTF-8.
        if text.len()? > MAX_TOTAL_BYTES - classifier.total_bytes {
            return Err(PyValueError::new_err("batch bytes too large"));
        }
        classifier
            .push(text.to_str()?)
            .map_err(PyValueError::new_err)?;
    }
    Ok(classifier.counts())
}

/// Count accepted unique, duplicate valid, and rejected invalid identifiers.
///
/// Accept Python lists or tuples of strings. Iterate without cloning an
/// untrusted entire input sequence into an unbounded native vector.
#[pyfunction]
fn classify_ids(values: &Bound<'_, PyAny>) -> PyResult<(usize, usize, usize)> {
    if let Ok(list) = values.cast::<PyList>() {
        classify_sequence(list.iter(), list.len())
    } else if let Ok(tuple) = values.cast::<PyTuple>() {
        classify_sequence(tuple.iter(), tuple.len())
    } else {
        Err(PyTypeError::new_err(
            "values must be a list or tuple of strings",
        ))
    }
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
