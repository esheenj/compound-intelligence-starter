"""Actual headless Chrome acceptance for the offline Runner Preflight browser reference."""
from __future__ import annotations

import json
import socket
import sys
import tempfile
from pathlib import Path

from browser_check_issue_report import Driver, driver_executable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.stage_showcase import stage_catalog  # noqa: E402


def require(ok, name):
    if ok is not True:
        raise AssertionError(name)


def main():
    with tempfile.TemporaryDirectory(prefix="preflight-ui-browser-") as tmp:
        dest = Path(tmp) / "site"
        stage = stage_catalog(dest)
        require((dest / "runner-preflight.html").is_file(), "SAFE_STAGED_PAGE")
        require("runnerPreflightSha256" in stage, "SOURCE_DIGEST")
        with socket.socket() as bound:
            bound.bind(("127.0.0.1", 0))
            port = bound.getsockname()[1]
        browser = Driver(driver_executable(), port)
        try:
            version = browser.start()
            browser.command("POST", "url", {"url": (dest / "runner-preflight.html").resolve().as_uri()})
            initial = browser.js("""
              return {
                heading:document.querySelectorAll('h1').length,
                main:document.querySelectorAll('main').length,
                status:document.getElementById('status').textContent,
                report:JSON.parse(document.getElementById('response').textContent),
                scripts:document.querySelectorAll('script').length,
                csp:document.querySelector('meta[http-equiv="Content-Security-Policy"]')?.content,
                requests:performance.getEntriesByType('resource').length
              };
            """)
            require(initial["heading"] == 1 and initial["main"] == 1
                    and initial["status"] == "READY" and initial["report"]["status"] == "READY"
                    and initial["scripts"] == 1 and initial["requests"] == 0
                    and "connect-src 'none'" in initial["csp"], "INITIAL_OFFLINE_RENDER")
            outcomes = []
            for button, expected in (("warn", "WARN"), ("hold", "HOLD"), ("ready", "READY")):
                state = browser.js("""
                  document.getElementById(arguments[0]).click();
                  return {status:document.getElementById('status').textContent,
                    report:JSON.parse(document.getElementById('response').textContent),
                    count:document.getElementById('findings').children.length};
                """.replace("arguments[0]", json.dumps(button)))
                require(state["status"] == expected and state["report"]["status"] == expected
                        and state["count"] > 0, "BUTTON_" + button)
                outcomes.append(state["status"])
            bad = browser.js("""
              const input=document.getElementById('inventory');
              const parsed=JSON.parse(input.value);
              parsed.runner.unknown_field='must-be-rejected';
              input.value=JSON.stringify(parsed);
              document.getElementById('evaluate').click();
              return {status:document.getElementById('status').textContent,
                report:JSON.parse(document.getElementById('response').textContent)};
            """)
            require(bad["status"] == "INVALID" and bad["report"]["status"] == "INVALID",
                    "MALFORMED_FIELD_IS_REJECTED")
            sizes = (320, 375, 812, 1440)
            for width in sizes:
                browser.viewport(width, 800)
                layout = browser.js("""
                  return {width:document.documentElement.scrollWidth,
                          viewport:innerWidth,
                          inputLabel:!!document.querySelector('label[for="inventory"]'),
                          live:document.getElementById('status').getAttribute('aria-live')};
                """)
                require(layout["width"] <= layout["viewport"] and layout["inputLabel"]
                        and layout["live"] == "polite", "RESPONSIVE_" + str(width))
            print(json.dumps({
                "schema": "runner-preflight-browser-qa-v1",
                "status": "PASS", "browser": version,
                "scenarios": outcomes, "invalid_input": "REJECTED",
                "widths": sizes, "external_requests_observed": 0,
                "screen_reader_tested": False, "wcag_certified": False,
                "rust_wasm_executed": False,
            }, sort_keys=True))
        finally:
            browser.close()


if __name__ == "__main__":
    main()
