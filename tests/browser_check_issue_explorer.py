"""Actual headless Chrome verification for the offline hypothesis selector.

The existing stdlib ChromeDriver helper is reused: no browser test package
download, network API, employer data, or additional infrastructure.
"""
from __future__ import annotations

import json
import socket
import subprocess
import sys
import tempfile
from pathlib import Path

from browser_check_issue_report import Driver, driver_executable

ROOT = Path(__file__).resolve().parents[1]


def check(value, name):
    if value is not True:
        raise AssertionError(name)


def main():
    with tempfile.TemporaryDirectory(prefix="compound-explorer-browser-") as temp:
        output = Path(temp) / "explorer.html"
        cmd = subprocess.run([
            sys.executable, "-m", "src.compound_intelligence.issue_explorer",
            "--input", str(ROOT / "examples" / "engineering_issues.json"),
            "--output", str(output),
        ], cwd=ROOT, capture_output=True, text=True, timeout=20)
        check(cmd.returncode == 0 and output.is_file(), "EXPLORER_CLI")
        receipt = json.loads(cmd.stdout)
        check(receipt.get("state") == "CREATED" and receipt.get("issues") == 2,
              "EXPLORER_RECEIPT")
        with socket.socket() as socket_:
            socket_.bind(("127.0.0.1", 0))
            port = socket_.getsockname()[1]
        browser = Driver(driver_executable(), port)
        try:
            version = browser.start()
            browser.command("POST", "url", {"url": output.resolve().as_uri()})
            initial = browser.js("""
                return {
                    heading: document.querySelectorAll('h1').length,
                    main: document.querySelectorAll('main').length,
                    cards: document.querySelectorAll('article[data-issue]').length,
                    visible: [...document.querySelectorAll('article[data-issue]')].filter(x=>!x.hidden).length,
                    options: document.querySelectorAll('#issue-filter option').length,
                    status: document.getElementById('filter-status').textContent,
                    csp: document.querySelector('meta[http-equiv="Content-Security-Policy"]')?.content,
                    resourceCount: performance.getEntriesByType('resource').length
                };
            """)
            check(initial["heading"] == 1 and initial["main"] == 1
                  and initial["cards"] == 2 and initial["visible"] == 2
                  and initial["options"] == 3, "SEMANTIC_COMPLETE_RENDER")
            check(initial["status"].startswith("2 fictional issues shown."),
                  "SCRIPT_ALLOWED_AND_STARTED")
            check("connect-src 'none'" in initial["csp"]
                  and "script-src 'sha256-" in initial["csp"]
                  and initial["resourceCount"] == 0, "NETWORK_LOCKED")
            selected = browser.js("""
                const filter=document.querySelector('#issue-filter');
                filter.value='empty-state';
                filter.dispatchEvent(new Event('change', {bubbles:true}));
                return {
                    visible:[...document.querySelectorAll('article[data-issue]')]
                      .filter(x=>!x.hidden).map(x=>x.dataset.issue),
                    status:document.querySelector('#filter-status').textContent,
                    first:document.querySelector('article[data-issue="empty-state"] details')
                      ?.hasAttribute('open')
                };
            """)
            check(selected["visible"] == ["empty-state"] and
                  selected["status"].startswith("1 fictional issue shown.") and
                  selected["first"] is True, "FILTER_INTERACTION")
            reset = browser.js("""
                const filter=document.querySelector('#issue-filter');
                filter.value='all';
                filter.dispatchEvent(new Event('change'));
                return [...document.querySelectorAll('article[data-issue]')]
                  .filter(x=>!x.hidden).length;
            """)
            check(reset == 2, "ALL_FILTER_RECOVERY")
            for width, height in ((320, 700), (375, 812), (1440, 900)):
                browser.viewport(width, height)
                layout = browser.js("""
                    return {
                        width:document.documentElement.scrollWidth,
                        viewport:innerWidth,
                        label:!!document.querySelector('label[for="issue-filter"]'),
                        skip:document.querySelector('a.skip')?.getAttribute('href')
                    };
                """)
                check(layout["width"] <= layout["viewport"] and
                      layout["label"] is True and layout["skip"] == "#main",
                      "RESPONSIVE_"+str(width))
            print(json.dumps({
                "schema": "compound-explorer-browser-qa-v1",
                "state": "PASS", "browser": version, "sample_issues": 2,
                "filter": "PASS", "responsive_widths": [320, 375, 1440],
                "external_requests_observed": 0,
                "screen_reader_tested": False, "wcag_certified": False,
            }, sort_keys=True))
        finally:
            browser.close()


if __name__ == "__main__":
    main()
