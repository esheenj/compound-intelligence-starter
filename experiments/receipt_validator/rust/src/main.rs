//! Synthetic receipt-format experiment. It does not verify signatures or hashes.
use std::io::{self, BufRead, Write};

fn validate_line(line: &str) -> bool {
    if line.len() > 512 {
        return false;
    }
    let mut fields = line.split('\t');
    let (Some(id), Some(state), Some(digest)) = (fields.next(), fields.next(), fields.next()) else {
        return false;
    };
    if fields.next().is_some() {
        return false;
    }
    if id.is_empty()
        || id.len() > 64
        || !id.bytes().all(|b| b.is_ascii_alphanumeric() || b == b'_' || b == b'-')
    {
        return false;
    }
    if !matches!(state, "ACCEPTED" | "REJECTED" | "INCONCLUSIVE") {
        return false;
    }
    digest.len() == 64 && digest.bytes().all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
}

fn main() -> io::Result<()> {
    let stdin = io::stdin();
    let mut stdout = io::stdout().lock();
    for line in stdin.lock().lines() {
        let line = line?;
        writeln!(stdout, "{}", if validate_line(&line) { "VALID" } else { "INVALID" })?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::validate_line;

    #[test]
    fn accepts_synthetic_receipts() {
        assert!(validate_line(&format!("test_01\tACCEPTED\t{}", "0".repeat(64))));
        assert!(validate_line(&format!("test-02\tINCONCLUSIVE\t{}", "abcdef09".repeat(8))));
    }

    #[test]
    fn rejects_malformed_input() {
        let digest = "0".repeat(64);
        for record in [
            format!("\tACCEPTED\t{digest}"),
            format!("bad id\tACCEPTED\t{digest}"),
            format!("x\tUNKNOWN\t{digest}"),
            format!("x\tACCEPTED\t{}", "A".repeat(64)),
            format!("x\tACCEPTED\t{digest}\textra"),
            format!("{}\tACCEPTED\t{digest}", "x".repeat(65)),
            format!("x\tACCEPTED\t{digest} "),
            "💡\tACCEPTED\t0000".to_string(),
        ] {
            assert!(!validate_line(&record), "unexpected valid: {record:?}");
        }
    }
}
