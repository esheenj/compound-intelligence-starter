//! Offline, read-only CI runner requirement matching on declared JSON inventories.
//! An input claim is not proof of live runner state.
use serde::{Deserialize, Serialize};
use std::collections::BTreeSet;
use std::fs;
use std::path::Path;
use std::process::ExitCode;

const IN_SCHEMA: &str = "runner-preflight-input-v1";
const OUT_SCHEMA: &str = "runner-preflight-result-v1";
const MAX_BYTES: u64 = 65_536;

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct Inventory {
    schema: String,
    runner: Runner,
    job: Job,
}
#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct Runner {
    os: String,
    arch: String,
    #[serde(default)]
    labels: Vec<String>,
    disk_free_mb: u64,
    memory_free_mb: u64,
    #[serde(default)]
    tools: Vec<String>,
    #[serde(default)]
    rust_targets: Vec<String>,
}
#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct Job {
    os: String,
    arch: String,
    #[serde(default)]
    required_labels: Vec<String>,
    min_disk_mb: u64,
    min_memory_mb: u64,
    #[serde(default)]
    required_tools: Vec<String>,
    #[serde(default)]
    rust_target: Option<String>,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
enum Status {
    Ready,
    Warn,
    Hold,
}

#[derive(Debug, Serialize)]
struct Finding {
    code: &'static str,
    severity: Status,
    message: &'static str,
}
#[derive(Debug, Serialize)]
struct Report {
    schema: &'static str,
    status: Status,
    findings: Vec<Finding>,
}
fn token_ok(v: &str) -> bool {
    !v.is_empty()
        && v.len() <= 64
        && v.bytes()
            .all(|b| b.is_ascii_alphanumeric() || matches!(b, b'-' | b'_' | b'.' | b'+' | b'/'))
}
fn list_ok(values: &[String]) -> bool {
    values.len() <= 64 && values.iter().all(|v| token_ok(v))
}
fn platform_ok(os: &str, arch: &str) -> bool {
    matches!(os, "linux" | "macos" | "windows") && matches!(arch, "x86_64" | "aarch64")
}
fn validate(input: &Inventory) -> Result<(), &'static str> {
    if input.schema != IN_SCHEMA {
        return Err("Unsupported schema");
    }
    let r = &input.runner;
    let j = &input.job;
    if !platform_ok(&r.os, &r.arch) || !platform_ok(&j.os, &j.arch) {
        return Err("Unknown OS or architecture");
    }
    if !list_ok(&r.labels)
        || !list_ok(&r.tools)
        || !list_ok(&r.rust_targets)
        || !list_ok(&j.required_labels)
        || !list_ok(&j.required_tools)
        || !j.rust_target.as_deref().is_none_or(token_ok)
    {
        return Err("Invalid or oversized inventory value");
    }
    if [
        r.disk_free_mb,
        r.memory_free_mb,
        j.min_disk_mb,
        j.min_memory_mb,
    ]
    .iter()
    .any(|&value| value > 1_000_000)
    {
        return Err("Resource quantity out of range");
    }
    Ok(())
}
fn add(findings: &mut Vec<Finding>, code: &'static str, severity: Status, message: &'static str) {
    findings.push(Finding {
        code,
        severity,
        message,
    });
}
fn evaluate(input: &Inventory) -> Result<Report, &'static str> {
    validate(input)?;
    let r = &input.runner;
    let j = &input.job;
    let mut findings = Vec::new();
    if r.os != j.os {
        add(
            &mut findings,
            "OS_MISMATCH",
            Status::Hold,
            "Runner operating system differs from job.",
        );
    }
    if r.arch != j.arch {
        add(
            &mut findings,
            "ARCH_MISMATCH",
            Status::Hold,
            "Runner architecture differs from job.",
        );
    }
    let labels: BTreeSet<&str> = r.labels.iter().map(String::as_str).collect();
    let required: BTreeSet<&str> = j.required_labels.iter().map(String::as_str).collect();
    for label in required {
        if !labels.contains(label) {
            add(
                &mut findings,
                "LABEL_MISSING",
                Status::Hold,
                "Required label is absent.",
            );
        }
    }
    if r.disk_free_mb < j.min_disk_mb {
        add(
            &mut findings,
            "DISK_INSUFFICIENT",
            Status::Hold,
            "Free disk below requirement.",
        );
    } else if j.min_disk_mb > 0 && r.disk_free_mb < j.min_disk_mb * 5 / 4 {
        add(
            &mut findings,
            "DISK_HEADROOM_LOW",
            Status::Warn,
            "Free disk headroom below 25%.",
        );
    }
    if r.memory_free_mb < j.min_memory_mb {
        add(
            &mut findings,
            "MEMORY_INSUFFICIENT",
            Status::Hold,
            "Free memory below requirement.",
        );
    } else if j.min_memory_mb > 0 && r.memory_free_mb < j.min_memory_mb * 5 / 4 {
        add(
            &mut findings,
            "MEMORY_HEADROOM_LOW",
            Status::Warn,
            "Free memory headroom below 25%.",
        );
    }
    let tools: BTreeSet<&str> = r.tools.iter().map(String::as_str).collect();
    for tool in j
        .required_tools
        .iter()
        .map(String::as_str)
        .collect::<BTreeSet<_>>()
    {
        if !tools.contains(tool) {
            add(
                &mut findings,
                "TOOL_MISSING",
                Status::Hold,
                "Required tool was not declared.",
            );
        }
    }
    if let Some(target) = &j.rust_target
        && !r.rust_targets.iter().any(|available| available == target)
    {
        add(
            &mut findings,
            "RUST_TARGET_MISSING",
            Status::Hold,
            "Required Rust target was not declared.",
        );
    }
    let status = if findings.iter().any(|f| f.severity == Status::Hold) {
        Status::Hold
    } else if !findings.is_empty() {
        Status::Warn
    } else {
        Status::Ready
    };
    Ok(Report {
        schema: OUT_SCHEMA,
        status,
        findings,
    })
}
fn inspect(path: &Path) -> Result<u8, &'static str> {
    // Refuse symlinks; no host probing, GitHub network access or privileged mutations.
    let info = fs::symlink_metadata(path).map_err(|_| "Input cannot be inspected")?;
    if !info.file_type().is_file() || info.len() > MAX_BYTES {
        return Err("Input must be a regular file no larger than 64 KiB");
    }
    let bytes = fs::read(path).map_err(|_| "Input cannot be read")?;
    if bytes.len() as u64 > MAX_BYTES {
        return Err("Input file too large");
    }
    let input: Inventory = serde_json::from_slice(&bytes).map_err(|_| "Invalid JSON schema")?;
    let report = evaluate(&input)?;
    let rc = match report.status {
        Status::Ready => 0,
        Status::Warn => 1,
        Status::Hold => 2,
    };
    println!(
        "{}",
        serde_json::to_string(&report).map_err(|_| "Output serialization failed")?
    );
    Ok(rc)
}
fn run() -> Result<u8, &'static str> {
    let mut a = std::env::args().skip(1);
    if a.next().as_deref() != Some("inspect") || a.next().as_deref() != Some("--input") {
        return Err("Usage: runner-preflight inspect --input FILE --format json");
    }
    let input = a.next().ok_or("Missing input file")?;
    if a.next().as_deref() != Some("--format")
        || a.next().as_deref() != Some("json")
        || a.next().is_some()
    {
        return Err("Usage: runner-preflight inspect --input FILE --format json");
    }
    inspect(Path::new(&input))
}
fn main() -> ExitCode {
    match run() {
        Ok(code) => ExitCode::from(code),
        Err(message) => {
            eprintln!("runner-preflight: {message}");
            ExitCode::from(3)
        }
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    fn valid() -> Inventory {
        serde_json::from_str(include_str!("../../fixtures/ready-x64.json")).unwrap()
    }
    #[test]
    fn ready_fixture() {
        let r = evaluate(&valid()).unwrap();
        assert_eq!(r.status, Status::Ready);
        assert!(r.findings.is_empty());
    }
    #[test]
    fn architecture_mismatch_fixture() {
        let m: Inventory =
            serde_json::from_str(include_str!("../../fixtures/hold-arch.json")).unwrap();
        let r = evaluate(&m).unwrap();
        assert_eq!(r.status, Status::Hold);
        assert!(r.findings.iter().any(|f| f.code == "ARCH_MISMATCH"));
    }
    #[test]
    fn low_disk_headroom_fixture() {
        let m: Inventory =
            serde_json::from_str(include_str!("../../fixtures/warn-disk.json")).unwrap();
        let r = evaluate(&m).unwrap();
        assert_eq!(r.status, Status::Warn);
        assert!(r.findings.iter().any(|f| f.code == "DISK_HEADROOM_LOW"));
    }
    #[test]
    fn missing_label_tool_target_memory() {
        let mut m = valid();
        m.job.required_labels.push("gpu".into());
        m.job.required_tools.push("docker".into());
        m.job.rust_target = Some("wasm32-unknown-unknown".into());
        m.job.min_memory_mb = 10_000;
        let r = evaluate(&m).unwrap();
        let codes: Vec<_> = r.findings.iter().map(|f| f.code).collect();
        assert_eq!(r.status, Status::Hold);
        for code in [
            "LABEL_MISSING",
            "TOOL_MISSING",
            "RUST_TARGET_MISSING",
            "MEMORY_INSUFFICIENT",
        ] {
            assert!(codes.contains(&code), "{code}");
        }
    }
    #[test]
    fn invalid_schema_and_token_rejected() {
        let mut m = valid();
        m.schema = "other".into();
        assert!(evaluate(&m).is_err());
        m.schema = IN_SCHEMA.into();
        m.runner.labels.push("bad\ninput".into());
        assert!(evaluate(&m).is_err());
    }
    #[test]
    fn unknown_json_field_rejected() {
        let raw = r#"{"schema":"runner-preflight-input-v1","runner":{"os":"linux","arch":"x86_64","disk_free_mb":1,"memory_free_mb":1,"unknown":true},"job":{"os":"linux","arch":"x86_64","min_disk_mb":1,"min_memory_mb":1}}"#;
        assert!(serde_json::from_str::<Inventory>(raw).is_err());
    }
    #[test]
    fn serialization_contract() {
        let json = serde_json::to_value(evaluate(&valid()).unwrap()).unwrap();
        assert_eq!(json["schema"], OUT_SCHEMA);
        assert_eq!(json["status"], "READY");
    }
}
