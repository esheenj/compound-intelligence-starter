"""Real headless Chrome checks of the exact offline OSS contributor directory."""
from __future__ import annotations
import json
import socket
import sys
import tempfile
from pathlib import Path
from browser_check_issue_report import Driver, driver_executable

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.stage_showcase import stage_catalog


def verify(ok, name):
    if ok is not True:
        raise AssertionError(name)


def run():
    with tempfile.TemporaryDirectory(prefix="oss-public-directory-") as folder:
        path = Path(folder) / "stage"
        receipt = stage_catalog(path)
        verify(receipt["repoCount"] == 7, "SOURCE_ALLOWLIST")
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        driver = Driver(driver_executable(), port)
        try:
            version = driver.start()
            driver.command("POST", "url", {"url": (path / "index.html").resolve().as_uri()})
            page = driver.js("""
                return {
                    title:document.title,
                    language:document.documentElement.lang,
                    h1:document.querySelectorAll('h1').length,
                    main:document.querySelectorAll('main').length,
                    cards:document.querySelectorAll('article.card').length,
                    projectLinks:[...document.querySelectorAll('article.card .links')]
                      .every(x=>x.querySelectorAll('a').length===2),
                    script:document.querySelectorAll('script').length,
                    externalAssets:performance.getEntriesByType('resource')
                      .filter(x=>!x.name.startsWith(location.origin)).length,
                    csp:document.querySelector('meta[http-equiv="Content-Security-Policy"]')?.content
                };
            """)
            verify(page["h1"] == 1 and page["main"] == 1 and page["cards"] == 7
                   and page["projectLinks"] is True and page["language"] == "en",
                   "SEMANTIC_PUBLIC_DIRECTORY")
            verify(page["script"] == 0 and page["externalAssets"] == 0
                   and "connect-src 'none'" in page["csp"]
                   and "script-src 'none'" in page["csp"],
                   "NO_RUNTIME_OR_NETWORK_ASSETS")
            driver.key("\ue004")  # Tab to skip link.
            skip = driver.js("""
                return {className:document.activeElement.className,
                  label:document.activeElement.textContent,
                  top:document.activeElement.getBoundingClientRect().top};
            """)
            verify("skip" in skip["className"] and skip["label"] == "Skip to public projects"
                   and 0 <= skip["top"] <= 50, "SKIP_LINK_FOCUS")
            driver.key("\ue007")  # Enter to main.
            verify(driver.js("return location.hash;") == "#main", "KEYBOARD_SKIP_TARGET")
            for width, height in ((320, 720), (375, 812), (812, 375), (1440, 900)):
                driver.viewport(width, height)
                layout = driver.js("""
                    return {
                      page:document.documentElement.scrollWidth,
                      viewport:innerWidth,
                      cards:document.querySelectorAll('article.card').length
                    };
                """)
                verify(layout["page"] <= layout["viewport"] and layout["cards"] == 7,
                       "NO_PAGE_OVERFLOW_" + str(width))
            print(json.dumps({
                "schema":"oss-directory-browser-qa-v1","status":"PASS",
                "browser":version,"publicCards":7,
                "responsiveWidths":[320,375,812,1440],
                "networkAssets":0,"screenReaderTested":False
            },sort_keys=True))
        finally:
            driver.close()


if __name__ == "__main__":
    run()
