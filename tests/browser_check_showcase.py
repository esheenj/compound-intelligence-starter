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
                    extraTools:document.querySelectorAll("#additional-tools li").length,
                    projectLinks:[...document.querySelectorAll('article.card .links')]
                      .every(x=>x.querySelectorAll('a').length===3),
                    githubPagesLinks:[...document.querySelectorAll('article.card a')]
                      .filter(x=>x.textContent==='Deployed demo').length,
                    extraLinks:[...document.querySelectorAll("#additional-tools a")].map(x=>x.getAttribute("href")),
                    script:document.querySelectorAll('script').length,
                    externalAssets:performance.getEntriesByType('resource')
                      .filter(x=>!x.name.startsWith(location.origin)).length,
                    csp:document.querySelector('meta[http-equiv="Content-Security-Policy"]')?.content
                };
            """)
            verify(page["h1"] == 1 and page["main"] == 1 and page["cards"] == 7
                   and page["projectLinks"] is True and page["githubPagesLinks"] == 7
                   and page["extraTools"] == 7 and page["language"] == "en",
                   "SEMANTIC_PUBLIC_DIRECTORY")
            verify(len(page["extraLinks"]) == 4 and "mvp-wave.html" in page["extraLinks"]
                   and "https://esheenj.github.io/mobile-first-flow-kit-oss/recovery.html" in page["extraLinks"]
                   and "https://esheenj.github.io/design-system-foundations-oss/audit.html" in page["extraLinks"]
                   and "https://esheenj.github.io/data-table-interactions-oss/experiment.html" in page["extraLinks"],
                   "EXACT_PUBLIC_TOOL_DISCOVERY")
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
            driver.command("POST", "url", {"url": (path / "mvp-wave.html").resolve().as_uri()})
            wave = driver.js("""
                document.getElementById("plan").click();
                return {
                    title:document.title,
                    status:document.getElementById("status").textContent,
                    count:document.querySelectorAll("#results li").length,
                    first:document.querySelector("#results li strong")?.textContent,
                    csp:document.querySelector('meta[http-equiv="Content-Security-Policy"]')?.content,
                    remoteResources:performance.getEntriesByType("resource")
                        .filter(x=>x.name.startsWith("http")).length
                };
            """)
            verify(wave["count"] == 3 and wave["first"].startswith("fictional-form")
                   and "No execution authorized" in wave["status"]
                   and "connect-src 'none'" in wave["csp"]
                   and wave["remoteResources"] == 0,
                   "OFFLINE_MVP_WAVE_FUNCTION")
            rejection = driver.js("""
                document.getElementById("fixture").value =
                    '{"malformed":"<img src=x onerror=alert(1)>"}';
                document.getElementById("plan").click();
                return {
                    status:document.getElementById("status").textContent,
                    count:document.querySelectorAll("#results li").length
                };
            """)
            verify(rejection["count"] == 0 and rejection["status"].startswith("Rejected:"),
                   "MVP_WAVE_INVALID_INPUT")
            driver.viewport(320, 720)
            verify(driver.js("return document.documentElement.scrollWidth <= innerWidth;") is True,
                   "MVP_WAVE_MOBILE_NO_OVERFLOW")
            print(json.dumps({
                "schema":"oss-directory-browser-qa-v1","status":"PASS",
                "browser":version,"publicCards":7,"additionalToolsLinked":7,
                "responsiveWidths":[320,375,812,1440],
                "networkAssets":0,"interactiveToolsChecked":1,"screenReaderTested":False
            },sort_keys=True))
        finally:
            driver.close()


if __name__ == "__main__":
    run()
