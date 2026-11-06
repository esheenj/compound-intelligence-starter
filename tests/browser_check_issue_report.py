"""Real Chromium smoke for the generated static issue report (CI-only).

Uses ChromeDriver's W3C WebDriver protocol over 127.0.0.1 with stdlib HTTP.
No Selenium/Playwright package or external network service is required.
This checks observable browser behavior, not WCAG or screen-reader compliance.
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "examples" / "engineering_issues.json"


def driver_executable() -> str:
    candidates = [
        shutil.which("chromedriver"),
        str(Path(os.environ.get("CHROMEWEBDRIVER", "")) / "chromedriver")
        if os.environ.get("CHROMEWEBDRIVER") else None,
        os.environ.get("CHROMEDRIVER_PATH"),
    ]
    for value in candidates:
        if value and Path(value).is_file() and os.access(value, os.X_OK):
            return value
    raise RuntimeError("CHROMEDRIVER_NOT_AVAILABLE")


class Driver:
    def __init__(self, path: str, port: int):
        self.url = f"http://127.0.0.1:{port}"
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        self.proc = subprocess.Popen(
            [path, f"--port={port}", "--allowed-ips=127.0.0.1"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.session = None

    def request(self, method: str, path: str, body: dict | None = None):
        payload = json.dumps(body).encode("utf-8") if body is not None else None
        request = urllib.request.Request(
            self.url + path, data=payload, method=method,
            headers={"Content-Type": "application/json"},
        )
        try:
            with self.opener.open(request, timeout=8) as response:
                result = json.load(response)
        except urllib.error.HTTPError as exc:
            # Avoid echoing potentially untrusted HTML/paths from driver errors.
            raise RuntimeError(f"WEBDRIVER_HTTP_{exc.code}") from exc
        if not isinstance(result, dict) or "value" not in result:
            raise RuntimeError("INVALID_WEBDRIVER_REPLY")
        value = result["value"]
        if isinstance(value, dict) and value.get("error"):
            raise RuntimeError("WEBDRIVER_" + str(value["error"]).upper().replace(" ", "_"))
        return value

    def start(self):
        for _ in range(60):
            if self.proc.poll() is not None:
                raise RuntimeError("CHROMEDRIVER_EXITED")
            try:
                status = self.request("GET", "/status")
                if status.get("ready"):
                    break
            except (urllib.error.URLError, OSError, TimeoutError):
                pass
            time.sleep(0.2)
        else:
            raise RuntimeError("CHROMEDRIVER_START_TIMEOUT")
        session = self.request("POST", "/session", {
            "capabilities": {"alwaysMatch": {
                "browserName": "chrome",
                "goog:chromeOptions": {"args": [
                    "--headless=new", "--no-sandbox", "--disable-dev-shm-usage",
                    "--disable-background-networking", "--no-first-run",
                ]},
            }}
        })
        self.session = session["sessionId"]
        return session["capabilities"].get("browserVersion", "UNKNOWN")

    def command(self, method: str, tail: str, body: dict | None = None):
        if not self.session:
            raise RuntimeError("NO_SESSION")
        return self.request(method, f"/session/{self.session}/{tail}", body)

    def js(self, code: str, args: list | None = None):
        return self.command("POST", "execute/sync", {"script": code, "args": args or []})

    def key(self, symbol: str):
        self.command("POST", "actions", {"actions": [{
            "type": "key", "id": "keyboard",
            "actions": [{"type": "keyDown", "value": symbol},
                        {"type": "keyUp", "value": symbol}],
        }]})

    def viewport(self, width: int, height: int):
        return self.command("POST", "window/rect", {"width": width, "height": height})

    def scheme(self, choice: str):
        return self.command("POST", "goog/cdp/execute", {
            "cmd": "Emulation.setEmulatedMedia",
            "params": {"features": [{"name": "prefers-color-scheme", "value": choice}]},
        })

    def close(self):
        if self.session:
            try:
                self.command("DELETE", "", None)
            except (OSError, RuntimeError):
                pass
        self.proc.terminate()
        try:
            self.proc.wait(timeout=4)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait(timeout=4)


def assert_true(condition: bool, name: str):
    if condition is not True:
        raise AssertionError(name)


def run() -> dict:
    with tempfile.TemporaryDirectory(prefix="cist-browser-") as work:
        output = Path(work) / "report.html"
        created = subprocess.run([
            sys.executable, "-m", "src.compound_intelligence.issue_report",
            "--input", str(INPUT), "--output", str(output),
        ], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            timeout=20, check=False)
        assert_true(created.returncode == 0 and output.is_file(), "HTML_REPORT_CLI")
        receipt = json.loads(created.stdout)
        assert_true(receipt.get("state") == "CREATED" and receipt.get("issues") == 2,
                    "HTML_REPORT_RECEIPT")
        markup = output.read_text(encoding="utf-8")
        for unsafe in ("<script", "<iframe", "<img", "http://", "https://"):
            assert_true(unsafe not in markup.lower(), "REMOTE_OR_ACTIVE_HTML")

        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        driver = Driver(driver_executable(), port)
        findings = {}
        try:
            version = driver.start()
            driver.command("POST", "url", {"url": output.resolve().as_uri()})
            semantic = driver.js("""
                const cards=[...document.querySelectorAll('article.card')];
                return {
                    language: document.documentElement.lang,
                    title: document.title,
                    main: document.querySelectorAll('main').length,
                    h1: document.querySelectorAll('h1').length,
                    cards: cards.length,
                    ordered: cards.every(c => {
                        const key=c.getAttribute('aria-labelledby');
                        return key && c.querySelector('h2#' + CSS.escape(key));
                    }),
                    hypotheses: [...document.querySelectorAll('article.card ol')].every(
                        ol => ol.querySelectorAll('li').length >= 2),
                    warning: !!document.querySelector('#warning') &&
                        document.body.innerText.includes('nothing has been executed'),
                    csp: document.querySelector('meta[http-equiv="Content-Security-Policy"]')
                        ?.content.includes("default-src 'none'"),
                    scripts: document.querySelectorAll('script,iframe,img,form').length,
                    skip: document.querySelector('a.skip')?.getAttribute('href')
                };
            """)
            assert_true(semantic["language"] == "en" and semantic["main"] == 1
                        and semantic["h1"] == 1 and semantic["cards"] == 2
                        and semantic["ordered"] is True
                        and semantic["hypotheses"] is True
                        and semantic["warning"] is True and semantic["csp"] is True
                        and semantic["scripts"] == 0 and semantic["skip"] == "#main",
                        "BROWSER_SEMANTICS_AND_WARNING")
            findings["semantics_and_warning"] = "PASS"

            # Real keyboard event and observed CSS position, not source-only assertions.
            driver.key("\ue004")  # W3C Tab key
            focused = driver.js("""
                const el=document.activeElement;
                const box=el.getBoundingClientRect();
                return {tag:el.tagName, cls:el.className, top:box.top,
                        visible:getComputedStyle(el).visibility,
                        display:getComputedStyle(el).display};
            """)
            assert_true(focused["tag"] == "A" and focused["cls"] == "skip"
                        and 0 <= focused["top"] <= 32
                        and focused["visible"] == "visible"
                        and focused["display"] != "none", "KEYBOARD_SKIP_LINK_FOCUS")
            driver.key("\ue007")  # W3C Enter key
            assert_true(driver.js("return location.hash") == "#main",
                        "KEYBOARD_SKIP_LINK_TARGET")
            findings["keyboard_skip_link"] = "PASS"

            for width, height in ((375, 812), (1440, 900)):
                driver.viewport(width, height)
                shape = driver.js("""
                    return {inner:innerWidth, scroll:document.documentElement.scrollWidth,
                            main:!!document.querySelector('main'),
                            visible:document.querySelector('#warning')
                                .getBoundingClientRect().width > 0};
                """)
                assert_true(shape["inner"] >= width - 20
                            and shape["scroll"] <= shape["inner"] + 1
                            and shape["main"] is True and shape["visible"] is True,
                            f"VIEWPORT_{width}")
                findings[f"viewport_{width}"] = "PASS"

            # Chrome's DevTools emulation verifies actual CSS color-scheme response.
            themes = {}
            for scheme in ("light", "dark"):
                driver.scheme(scheme)
                themes[scheme] = driver.js("""
                    return {media:matchMedia('(prefers-color-scheme: '+arguments[0]+')').matches,
                            background:getComputedStyle(document.body).backgroundColor,
                            color:getComputedStyle(document.body).color};
                """, [scheme])
                assert_true(themes[scheme]["media"] is True
                            and bool(themes[scheme]["background"])
                            and bool(themes[scheme]["color"]),
                            "THEME_" + scheme + "_" + json.dumps(themes[scheme], sort_keys=True))
            assert_true(themes["dark"]["background"] != themes["light"]["background"],
                        "THEME_BACKGROUND_RESPONSIVE")
            findings["light_dark_theme"] = "PASS"
            return {
                "schema": "compound-browser-qa-v1",
                "runner_browser": "Google Chrome",
                "browser_version": version,
                "report_source": "synthetic-existing-cli",
                "findings": findings,
                "screen_reader_tested": False,
                "wcag_certified": False,
                "external_network_required": False,
            }
        finally:
            driver.close()


if __name__ == "__main__":
    try:
        report = run()
    except (RuntimeError, ValueError, AssertionError, OSError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"schema": "compound-browser-qa-v1", "state": "FAILED",
                          "reason": str(exc)[:160]}, sort_keys=True))
        raise SystemExit(1)
    print(json.dumps(report, indent=2, sort_keys=True))
