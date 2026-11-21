//! Educational aggregation only; no operational authority or real-event schemas.
use std::collections::HashSet;
use std::io::{self, BufRead, Write};

const CATEGORIES: [&str; 4] = ["atlas", "beacon", "cobalt", "delta"];
const KINDS: [&str; 3] = ["PASS", "FAIL", "RETRY"];

fn parse_record(line: &[u8]) -> Option<(&str, usize, usize, i64)> {
    if line.len() > 256 || !line.is_ascii() {
        return None;
    }
    let line = std::str::from_utf8(line).ok()?;
    let parts: Vec<&str> = line.split('\t').collect();
    if parts.len() != 4 {
        return None;
    }
    let id = parts[0];
    if id.len() != 9 || !id.starts_with('E') || !id.as_bytes()[1..].iter().all(u8::is_ascii_digit) {
        return None;
    }
    let category = CATEGORIES.iter().position(|s| *s == parts[1])?;
    let kind = KINDS.iter().position(|s| *s == parts[2])?;
    let text = parts[3];
    let digits = text.strip_prefix('-').unwrap_or(text);
    if digits.is_empty() || !digits.bytes().all(|b| b.is_ascii_digit())
       || (digits.len() > 1 && digits.starts_with('0')) || text == "-0" {
        return None;
    }
    let amount = text.parse::<i64>().ok()?;
    if !(-10_000..=10_000).contains(&amount) {
        return None;
    }
    Some((id, category, kind, amount))
}

fn aggregate<R: BufRead>(mut reader: R) -> io::Result<Vec<u8>> {
    let mut seen: HashSet<String> = HashSet::new();
    let mut counts = [[0u64; 3]; 4];
    let mut sums = [[0i64; 3]; 4];
    let (mut accepted, mut duplicates, mut rejected) = (0u64, 0u64, 0u64);
    let mut line = Vec::new();
    loop {
        line.clear();
        if reader.read_until(b'\n', &mut line)? == 0 {
            break;
        }
        if line.last() == Some(&b'\n') {
            line.pop();
        }
        if let Some((id, category, kind, amount)) = parse_record(&line) {
            if !seen.insert(id.to_string()) {
                duplicates += 1;
                continue;
            }
            accepted += 1;
            counts[category][kind] += 1;
            sums[category][kind] += amount;
        } else {
            rejected += 1;
        }
    }
    let mut output = format!("ACCEPTED\t{accepted}\nDUPLICATES\t{duplicates}\nREJECTED\t{rejected}\n");
    for (ci, category) in CATEGORIES.iter().enumerate() {
        for (ki, kind) in KINDS.iter().enumerate() {
            output.push_str(&format!("GROUP\t{category}\t{kind}\t{}\t{}\n", counts[ci][ki], sums[ci][ki]));
        }
    }
    Ok(output.into_bytes())
}

fn main() -> io::Result<()> {
    let result = aggregate(io::stdin().lock())?;
    io::stdout().lock().write_all(&result)
}

#[cfg(test)]
mod tests {
    use super::{aggregate, parse_record};

    #[test]
    fn canonical_input() {
        assert!(parse_record(b"E00000001\tatlas\tPASS\t-10000").is_some());
        for line in [
            &b"E00000001\tatlas\tPASS\t+5"[..],
            &b"E00000001\tatlas\tPASS\t-0"[..],
            &b"E00000001\tatlas\tPASS\t01"[..],
            &b"E00000001\tatlas\tPASS\t10001"[..],
            &b"E00000001\tatlas\tPASS\t0\textra"[..],
            &b"E00000001\tunknown\tPASS\t0"[..],
        ] {
            assert!(parse_record(line).is_none());
        }
    }

    #[test]
    fn duplicates_and_rejections() {
        let input = b"E00000001\tatlas\tPASS\t5\nE00000001\tatlas\tPASS\t7\nbad\n";
        let result = String::from_utf8(aggregate(&input[..]).unwrap()).unwrap();
        assert!(result.starts_with("ACCEPTED\t1\nDUPLICATES\t1\nREJECTED\t1\n"));
    }
}
