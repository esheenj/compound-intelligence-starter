"""v0.7 read-only, self-contained HTML report from local evidence.

No server, external assets, JavaScript, model execution, or implicit file discovery.
Only explicitly supplied SQLite paths are inspected. All user-derived text is escaped.
"""
from __future__ import annotations

import argparse
import html
import json
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from .benchmark import metrics

ALLOWED_STATES = {"PENDING", "RUNNING", "DONE", "FAILED"}
ALLOWED_RESULTS = {"VERIFIED", "REJECTED", "NO_RESULT"}
MAX_ROWS = 1000


def _read(path: Path | None, query: str) -> list:
    if path is None:
        return []
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"evidence database not found: {path}")
    # Read-only connection; never create or migrate a database from the dashboard.
    uri = path.resolve().as_uri() + "?mode=ro"
    connection = sqlite3.connect(uri, uri=True, timeout=5)
    try:
        return connection.execute(query).fetchmany(MAX_ROWS + 1)
    finally:
        connection.close()


def snapshot(queue_db: Path | None = None, challenge_db: Path | None = None) -> dict:
    jobs_raw = _read(queue_db, "SELECT id,capability,state,attempts,result,error FROM jobs ORDER BY id")
    evidence_raw = _read(challenge_db, "SELECT record FROM challenge_records ORDER BY fingerprint")
    if len(jobs_raw) > MAX_ROWS or len(evidence_raw) > MAX_ROWS:
        raise ValueError("dashboard supports at most 1000 rows per input; narrow your source")
    jobs, outcomes = [], []
    for job_id, capability, state, attempts, result, error in jobs_raw:
        if state not in ALLOWED_STATES:
            raise ValueError("unexpected job state")
        jobs.append({"id": str(job_id), "capability": str(capability), "state": state,
                     "attempts": int(attempts), "error": str(error or "")})
        if result:
            data = json.loads(result)
            for item in data.get("results", []):
                # Bundled fixtures are not counted as real-model outcomes.
                if item.get("status") in ALLOWED_RESULTS:
                    outcomes.append({"model": str(item.get("model", "unknown")),
                                     "task": str(item.get("task", "unknown")),
                                     "status": item["status"],
                                     "mode": str(data.get("run_mode", "UNSPECIFIED")),
                                     "origin": "job:" + str(job_id)})
    for (raw,) in evidence_raw:
        record = json.loads(raw)
        summary = record.get("summary", {})
        if summary.get("status") in ALLOWED_RESULTS:
            outcomes.append({"model": str(summary.get("model", "unknown")),
                             "task": str(summary.get("task", "unknown")),
                             "status": summary["status"],
                             # Challenge records do not record provider origin.
                             "mode": "UNKNOWN_PROVIDER",
                             "origin": "challenge"})
    counts = Counter(job["state"] for job in jobs)
    by_model = defaultdict(list)
    for item in outcomes:
        by_model[(item["model"], item["mode"])].append(item)
    models = [
        {"model": model, "mode": mode, "stats": metrics(rows)}
        for (model, mode), rows in sorted(by_model.items())
    ]
    return {"jobs": jobs, "job_counts": {s: counts[s] for s in sorted(ALLOWED_STATES)},
            "outcomes": outcomes, "models": models,
            "source_count": int(queue_db is not None) + int(challenge_db is not None),
            "note": "Point-in-time view. Separate inputs may overlap; this is not a deduplicated global ledger."}


def _esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def render(data: dict) -> str:
    jobs = data["jobs"]
    results = data["outcomes"]
    models = data["models"]
    states = data["job_counts"]
    cards = [
        ("Jobs", len(jobs)), ("Completed", states["DONE"]),
        ("Needs attention", states["FAILED"]), ("Evaluations", len(results))
    ]
    card_html = "".join(
        '<section class="stat"><span>' + _esc(label) + '</span><strong>' +
        _esc(number) + '</strong></section>' for label, number in cards
    )
    def tablerows(rows, keys):
        return "".join("<tr>" + "".join("<td>" + _esc(row.get(key, "")) + "</td>" for key in keys)
                       + "</tr>" for row in rows)
    model_rows = []
    for item in models:
        stat = item["stats"]
        score = stat["verified_per_attempt"]
        model_rows.append({"model": item["model"], "mode": item["mode"],
                           "attempted": stat["attempted"],
                           "verified": stat["verified"], "rejected": stat["rejected"],
                           "no_result": stat["no_result"],
                           "score": "—" if score is None else f"{score * 100:.1f}%"})
    job_rows = tablerows(jobs, ("id", "capability", "state", "attempts", "error"))
    model_table = tablerows(model_rows,
                           ("model", "mode", "attempted", "verified", "rejected", "no_result", "score"))
    event_rows = tablerows(results, ("task", "model", "status", "mode", "origin"))
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src 'none'; script-src 'none'; connect-src 'none'; form-action 'none'">
<title>Compound Intelligence — Evidence Dashboard</title>
<style>
:root{color-scheme:dark;font:16px system-ui,sans-serif;background:#0c1423;color:#e9f1fb}
*{box-sizing:border-box}body{margin:0;padding:clamp(20px,5vw,64px);max-width:1350px;margin-inline:auto}
h1{font-size:clamp(27px,4vw,44px);margin:8px 0}h2{margin:36px 0 12px;font-size:21px}
p{line-height:1.5;color:#b9cadf}.eyebrow{font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:#88dfba}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:24px 0}
.stat{padding:22px;background:#16253a;border:1px solid #314762;border-radius:12px}
.stat span{display:block;color:#b9cadf;font-size:13px}.stat strong{display:block;margin-top:8px;font-size:32px}
.panel{background:#121f31;border:1px solid #314762;border-radius:12px;overflow-x:auto}
table{border-collapse:collapse;width:100%;min-width:620px}th,td{padding:13px 16px;text-align:left;border-bottom:1px solid #304258;font-size:13px}
th{color:#b2d5f6;background:#1b3047}tr:last-child td{border-bottom:0}
.note{margin-top:28px;border-left:3px solid #88dfba;padding:10px 16px;background:#16253a}
footer{font-size:12px;color:#a6bacd;margin-top:32px}
</style></head><body>
<div class="eyebrow">Esheen Labs / open-source reference</div>
<h1>Compound Intelligence</h1>
<p>What did we try, what worked, and what needs attention? This is a local, read-only evidence snapshot—not a live control panel.</p>
<div class="stats">""" + card_html + """</div>
<h2>Model and fixture comparisons</h2>
<div class="panel"><table><thead><tr><th>Model</th><th>Evidence origin</th><th>Attempts</th><th>Verified</th><th>Rejected</th><th>No result</th><th>Verified / attempt</th></tr></thead><tbody>""" + model_table + """</tbody></table></div>
<h2>Queued jobs</h2>
<div class="panel"><table><thead><tr><th>Job</th><th>Capability</th><th>Status</th><th>Attempts</th><th>Error</th></tr></thead><tbody>""" + job_rows + """</tbody></table></div>
<h2>Evaluation history</h2>
<div class="panel"><table><thead><tr><th>Task</th><th>Model</th><th>Outcome</th><th>Origin</th><th>Source</th></tr></thead><tbody>""" + event_rows + """</tbody></table></div>
<p class="note">""" + _esc(data["note"]) + """ Fixture results are simulated. Unlabeled challenge-provider records are UNKNOWN_PROVIDER, not evidence of real model inference. Static patch validation does not execute code. No evidence of continuous improvement is claimed.</p>
<footer>Generated """ + _esc(timestamp) + """ · Locally rendered, no network calls or scripts</footer>
</body></html>
"""


def build(queue_db: Path | None, challenge_db: Path | None, output: Path) -> dict:
    data = snapshot(queue_db, challenge_db)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render(data), encoding="utf-8")
    return {"output": str(output), "jobs": len(data["jobs"]),
            "evaluations": len(data["outcomes"]), "models": len(data["models"])}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue-db", type=Path, help="existing v0.6 queue.sqlite3")
    parser.add_argument("--challenge-db", type=Path, help="existing v0.4/0.5 challenges.sqlite3")
    parser.add_argument("--output", type=Path, default=Path("local-data/dashboard.html"))
    args = parser.parse_args()
    if not args.queue_db and not args.challenge_db:
        parser.error("provide --queue-db and/or --challenge-db; no automatic scanning")
    print(json.dumps(build(args.queue_db, args.challenge_db, args.output), indent=2))


if __name__ == "__main__":
    main()
