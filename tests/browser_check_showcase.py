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
                   and page["extraTools"] == 12 and page["language"] == "en",
                   "SEMANTIC_PUBLIC_DIRECTORY")
            verify(len(page["extraLinks"]) == 12 and "mvp-wave.html" in page["extraLinks"]
                   and "agentops.html" in page["extraLinks"]
                   and "https://esheenj.github.io/mobile-first-flow-kit-oss/recovery.html" in page["extraLinks"]
                   and "https://esheenj.github.io/design-system-foundations-oss/audit.html" in page["extraLinks"]
                   and "https://esheenj.github.io/data-table-interactions-oss/experiment.html" in page["extraLinks"]
                   and "https://esheenj.github.io/form-experience-kit-oss/onboarding.html" in page["extraLinks"]
                   and "https://esheenj.github.io/flow-state-machine-oss/journey.html" in page["extraLinks"]
                   and "https://esheenj.github.io/data-table-interactions-oss/quality.html" in page["extraLinks"]
                   and "https://esheenj.github.io/form-experience-kit-oss/consent.html" in page["extraLinks"]
                   and "https://esheenj.github.io/mobile-first-flow-kit-oss/notifications.html" in page["extraLinks"]
                   and "https://esheenj.github.io/flow-state-machine-oss/blueprint.html" in page["extraLinks"]
                   and "https://esheenj.github.io/flow-state-machine-oss/approval.html" in page["extraLinks"],
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
            driver.command("POST", "url", {"url": (path / "agentops.html").resolve().as_uri()})
            agentops = driver.js("""
                document.getElementById('inspect').click();
                return {
                    status:document.getElementById('status').textContent,
                    units:document.getElementById('units').textContent,
                    duplicates:document.getElementById('duplicates').textContent,
                    incomplete:document.getElementById('incomplete').textContent,
                    runs:document.querySelectorAll('#runrows tr').length,
                    csp:document.querySelector('meta[http-equiv="Content-Security-Policy"]')?.content,
                    network:performance.getEntriesByType('resource').filter(x=>x.name.startsWith('http')).length
                };
            """)
            verify(agentops["status"].startswith("PASS:") and agentops["units"] == "7"
                   and agentops["duplicates"] == "1" and agentops["incomplete"] == "0"
                   and agentops["runs"] == 1 and agentops["network"] == 0
                   and "connect-src 'none'" in agentops["csp"], "AGENTOPS_VALID_OFFLINE")
            hold = driver.js("""
                document.getElementById('missing').click();
                return {status:document.getElementById('status').textContent,
                        incomplete:document.getElementById('incomplete').textContent,
                        state:document.querySelector('#runrows tr td:nth-child(3)')?.textContent};
            """)
            verify(hold["status"].startswith("HOLD:") and hold["incomplete"] == "1"
                   and hold["state"] == "INCOMPLETE", "AGENTOPS_MISSING_TERMINAL")
            conflict = driver.js("""
                document.getElementById('conflict').click();
                return {status:document.getElementById('status').textContent,
                        rows:document.querySelectorAll('#runrows tr').length,
                        units:document.getElementById('units').textContent};
            """)
            verify(conflict["status"].startswith("Rejected:") and conflict["rows"] == 0
                   and conflict["units"] == "—", "AGENTOPS_DUPLICATE_CONFLICT")
            for width, height in ((320, 720), (375, 812), (812, 375), (1440, 900)):
                driver.viewport(width, height)
                verify(driver.js("return document.documentElement.scrollWidth <= innerWidth;") is True,
                       "AGENTOPS_NO_OVERFLOW_" + str(width))
            driver.js("document.getElementById('reset').click(); return true;")
            verify(driver.js("return document.getElementById('status').textContent.startsWith('PASS:');") is True,
                   "AGENTOPS_RECOVERY_FROM_INVALID_INPUT")
            print(json.dumps({
                "schema":"oss-directory-browser-qa-v1","status":"PASS",
                "browser":version,"publicCards":7,"additionalToolsLinked":12,
                "responsiveWidths":[320,375,812,1440],
                "networkAssets":0,"interactiveToolsChecked":2,"screenReaderTested":False
            },sort_keys=True))
        finally:
            driver.close()


if __name__ == "__main__":
    run()
