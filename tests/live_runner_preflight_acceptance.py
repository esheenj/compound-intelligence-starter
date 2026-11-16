"""Post-Pages read-only HTTPS and real-Chrome acceptance for Runner Preflight.

Verifies actual published HTML byte-for-byte against the review-qualified
source. This is not a CI runner inventory check, penetration test, remote
execution, token exchange or claim of Rust/WASM in the browser.
"""
from __future__ import annotations

import hashlib
import json
import socket
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

from browser_check_issue_report import Driver, driver_executable

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "site" / "runner-preflight.html"
URL = "https://esheenj.github.io/compound-intelligence-starter/runner-preflight.html"
EXPECTED_RELEASE = "runner-preflight/releases/tag/v0.3.0"
MAX_HTML_BYTES = 100_000


def require(condition: bool, name: str) -> None:
    if condition is not True:
        raise AssertionError(name)


def verify_deployed_bytes(source: bytes, actual: bytes) -> str:
    """Pure, exact source/deployment parity check. SHA-256 is the receipt."""
    require(len(source) <= MAX_HTML_BYTES, "PREFLIGHT_SOURCE_EXCEEDS_BOUND")
    require(len(actual) <= MAX_HTML_BYTES, "PREFLIGHT_LIVE_HTML_EXCEEDS_BOUND")
    require(hashlib.sha256(actual).digest() == hashlib.sha256(source).digest(),
            "PREFLIGHT_DEPLOYED_BYTES_NOT_MATCH_SOURCE")
    require(actual == source, "PREFLIGHT_DEPLOYED_BYTES_NOT_EXACT")
    require(EXPECTED_RELEASE.encode("ascii") in actual, "PREFLIGHT_RELEASE_LINK_MISSING")
    return hashlib.sha256(actual).hexdigest()


def read_live_bytes(source: bytes) -> str:
    """Only a fixed allowlisted public HTTPS URL; never follow to another origin."""
    want = urlsplit(URL)
    for _ in range(12):
        request = urllib.request.Request(
            URL,
            headers={"User-Agent": "Runner-Preflight-Public-Pages-ReadOnly-Acceptance",
                     "Cache-Control": "no-cache"},
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                destination = urlsplit(response.geturl())
                require(
                    response.status == 200
                    and destination.scheme == want.scheme
                    and destination.netloc == want.netloc
                    and destination.path == want.path,
                    "PREFLIGHT_UNEXPECTED_HTTPS_DESTINATION",
                )
                html = response.read(MAX_HTML_BYTES + 1)
        except (OSError, TimeoutError, urllib.error.URLError):
            time.sleep(0.5)
            continue
        try:
            return verify_deployed_bytes(source, html)
        except AssertionError:
            time.sleep(0.5)  # Pages CDN can briefly serve the previous revision.
    raise AssertionError("PREFLIGHT_LIVE_BYTES_MISSING_OR_STALE")


def run() -> dict:
    source = SOURCE.read_bytes()
    digest = read_live_bytes(source)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    driver = Driver(driver_executable(), port)
    try:
        chrome = driver.start()
        driver.command("POST", "url", {"url": URL})
        for _ in range(40):
            loaded = driver.js("""
              return document.readyState!=='loading' &&
                document.querySelector('h1')?.textContent.length>10 &&
                document.querySelector('#status')?.textContent==='READY';
            """)
            if loaded is True:
                break
            time.sleep(0.25)
        else:
            raise AssertionError("PREFLIGHT_LIVE_CHROME_NOT_READY")
        page = driver.js("""
          return {
            href: location.href, origin: location.origin,
            title: document.title,
            main: document.querySelectorAll('main').length,
            heading: document.querySelectorAll('h1').length,
            scripts: document.querySelectorAll('script').length,
            forms: document.querySelectorAll('form').length,
            csp: document.querySelector('meta[http-equiv="Content-Security-Policy"]')?.content||'',
            resourceRequests: performance.getEntriesByType('resource')
              .filter(x=>x.name.startsWith('http')).length,
            releaseLinks: [...document.querySelectorAll('a[href]')]
              .map(a=>a.href)
              .filter(h=>h.includes('runner-preflight/releases/tag/v0.3.0')),
            status: document.querySelector('#status').textContent
          };
        """)
        require(page["href"] == URL and page["origin"] == "https://esheenj.github.io"
                and page["main"] == 1 and page["heading"] == 1
                and page["scripts"] == 1 and page["forms"] == 0
                and page["resourceRequests"] == 0
                and page["status"] == "READY"
                and len(page["releaseLinks"]) >= 2
                and "default-src 'none'" in page["csp"]
                and "connect-src 'none'" in page["csp"],
                "PREFLIGHT_LIVE_SECURITY_AND_VERSION")
        outcomes = []
        for button, expected in (("warn", "WARN"), ("hold", "HOLD"), ("ready", "READY")):
            state = driver.js("""
              document.getElementById('BUTTON').click();
              return {
                status: document.querySelector('#status').textContent,
                report: JSON.parse(document.querySelector('#response').textContent)
              };
            """.replace("BUTTON", button))
            require(state["status"] == expected and state["report"]["status"] == expected,
                    "PREFLIGHT_LIVE_SCENARIO_" + button.upper())
            outcomes.append(state["status"])
        rejected = driver.js("""
          const box = document.querySelector('#inventory');
          const data = JSON.parse(box.value);
          data.runner.unexpected = 'must-reject';
          box.value = JSON.stringify(data);
          document.querySelector('#evaluate').click();
          return document.querySelector('#status').textContent;
        """)
        require(rejected == "INVALID", "PREFLIGHT_LIVE_INVALID_NOT_REJECTED")
        for width in (320, 375, 812, 1440):
            driver.viewport(width, 800)
            require(driver.js("return document.documentElement.scrollWidth<=innerWidth+1;") is True,
                    "PREFLIGHT_LIVE_OVERFLOW_" + str(width))
        return {
            "schema": "runner-preflight-live-pages-acceptance-v1",
            "state": "PASS",
            "httpsUrl": URL,
            "sourceSha256": digest,
            "actualLiveBytesMatchReviewedSource": True,
            "browser": "Google Chrome",
            "browserVersion": chrome,
            "scenarios": outcomes,
            "invalid": "REJECTED",
            "responsiveWidths": [320, 375, 812, 1440],
            "thirdPartyResources": 0,
            "limitations": "No runner administration, real trading, Rust/WASM browser execution, independent security certification or customer usage measurement.",
        }
    finally:
        driver.close()


if __name__ == "__main__":
    try:
        print(json.dumps(run(), sort_keys=True))
    except (AssertionError, OSError, ValueError, TimeoutError, RuntimeError) as exc:
        print(json.dumps({
            "schema": "runner-preflight-live-pages-acceptance-v1",
            "state": "FAIL", "reason": str(exc)[:140],
        }, sort_keys=True))
        raise SystemExit(1)
