"""Real headless Chrome checks of the exact offline OSS contributor directory."""
from __future__ import annotations
import json
import socket
import time
import sys
import tempfile
from pathlib import Path
from browser_check_issue_report import Driver, driver_executable

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.stage_showcase import stage_catalog, SUPPORT_CONFIG_SOURCE
from scripts.render_support import load_channels


def verify(ok, name):
    if ok is not True:
        raise AssertionError(name)


def run():
    with tempfile.TemporaryDirectory(prefix="oss-public-directory-") as folder:
        path = Path(folder) / "stage"
        receipt = stage_catalog(path)
        verify(receipt["repoCount"] == 11, "SOURCE_ALLOWLIST")
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
                      .filter(x=>x.textContent==='Try demo').length,
                    extraLinks:[...document.querySelectorAll("#additional-tools a")].map(x=>x.getAttribute("href")),
                    script:document.querySelectorAll('script').length,
                    externalAssets:performance.getEntriesByType('resource')
                      .filter(x=>!x.name.startsWith(location.origin)).length,
                    csp:document.querySelector('meta[http-equiv="Content-Security-Policy"]')?.content
                };
            """)
            verify(page["h1"] == 1 and page["main"] == 1 and page["cards"] == 11
                   and page["projectLinks"] is True and page["githubPagesLinks"] == 11
                   and page["extraTools"] == 21 and page["language"] == "en",
                   "SEMANTIC_PUBLIC_DIRECTORY")
            verify(len(page["extraLinks"]) == 21 and "mvp-wave.html" in page["extraLinks"]
                   and "agentops.html" in page["extraLinks"]
                   and "agentproof.html" in page["extraLinks"]
                   and "agentcredits.html" in page["extraLinks"]
                   and "model-cost.html" in page["extraLinks"]
                   and "model-fit.html" in page["extraLinks"]
                   and "context-preservation.html" in page["extraLinks"]
                   and "model-disagreement.html" in page["extraLinks"]
                   and "decision-review.html" in page["extraLinks"]
                   and "agent-trust.html" in page["extraLinks"]
                   and "signed-agent.html" in page["extraLinks"]
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
            filters = driver.js("""
                const total = document.querySelectorAll("#additional-tools li").length;
                document.getElementById("filter-ai").click();
                const ai = [...document.querySelectorAll("#additional-tools li")]
                    .filter(x => getComputedStyle(x).display !== "none");
                document.getElementById("filter-ux").click();
                const ux = [...document.querySelectorAll("#additional-tools li")]
                    .filter(x => getComputedStyle(x).display !== "none");
                document.getElementById("filter-all").click();
                const restored = [...document.querySelectorAll("#additional-tools li")]
                    .filter(x => getComputedStyle(x).display !== "none").length;
                return {total, ai:ai.length, ux:ux.length,
                        aiCorrect:ai.every(x=>x.classList.contains("ai")),
                        uxCorrect:ux.every(x=>x.classList.contains("ux")), restored};
            """)
            verify(filters["total"] == 21 and filters["ai"] == 10 and filters["ux"] == 6
                   and filters["aiCorrect"] and filters["uxCorrect"]
                   and filters["restored"] == 21, "CATEGORY_FILTERS_RESTORE_ALL")
            for width, height in ((320, 720), (375, 812), (812, 375), (1440, 900)):
                driver.viewport(width, height)
                layout = driver.js("""
                    return {
                      page:document.documentElement.scrollWidth,
                      viewport:innerWidth,
                      cards:document.querySelectorAll('article.card').length
                    };
                """)
                verify(layout["page"] <= layout["viewport"] and layout["cards"] == 11,
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
            driver.command("POST", "url", {"url": (path / "agentproof.html").resolve().as_uri()})
            driver.js("document.getElementById('check').click(); return true;")
            time.sleep(0.35)
            proof = driver.js("""
                return {status:document.getElementById('status').textContent,
                        count:document.getElementById('count').textContent,
                        digests:document.getElementById('digests').textContent,
                        failures:document.getElementById('failures').textContent,
                        csp:document.querySelector('meta[http-equiv="Content-Security-Policy"]')?.content,
                        remote:performance.getEntriesByType('resource')
                            .filter(x=>x.name.startsWith('http')).length};
            """)
            verify(proof["status"].startswith("PASS:") and proof["count"] == "3"
                   and proof["digests"] == "3" and proof["failures"] == "0"
                   and proof["remote"] == 0 and "connect-src 'none'" in proof["csp"],
                   "AGENTPROOF_GOOD_SAMPLE")
            driver.js("document.getElementById('tamper').click(); return true;")
            time.sleep(0.25)
            verify(driver.js("""
                return document.getElementById('status').textContent.startsWith('REJECTED:')
                  && document.getElementById('findings').textContent.includes('digest mismatch');
            """) is True, "AGENTPROOF_TAMPER_DETECTED")
            driver.js("document.getElementById('duplicate').click(); return true;")
            time.sleep(0.25)
            verify(driver.js("""
                return document.getElementById('status').textContent.startsWith('REJECTED:')
                  && document.getElementById('findings').textContent.includes('duplicate event ID');
            """) is True, "AGENTPROOF_DUPLICATE_DETECTED")
            driver.js("document.getElementById('missing').click(); return true;")
            time.sleep(0.25)
            verify(driver.js("""
                return document.getElementById('status').textContent.startsWith('REJECTED:')
                  && document.getElementById('findings').textContent.includes('missing or unexpected fields');
            """) is True, "AGENTPROOF_MISSING_PRODUCER")
            driver.js("""
                document.getElementById('fixture').value =
                  '{"schema":"agentproof.receipts.v1","schema":"agentproof.receipts.v1","events":[]}';
                document.getElementById('check').click();return true;
            """)
            time.sleep(0.2)
            verify(driver.js("""
                return document.getElementById('status').textContent.startsWith('REJECTED:')
                    && document.getElementById('count').textContent==='—';
            """) is True, "AGENTPROOF_DUPLICATE_JSON_KEY_FAIL_CLOSED")
            driver.js("document.getElementById('reset').click();return true;")
            time.sleep(0.25)
            verify(driver.js("""
                return document.getElementById('status').textContent.startsWith('PASS:');
            """) is True, "AGENTPROOF_RESET_RECOVERS")
            for width,height in ((320,720),(375,812),(812,375),(1440,900)):
                driver.viewport(width,height)
                verify(driver.js("return document.documentElement.scrollWidth <= innerWidth;") is True,
                       "AGENTPROOF_NO_OVERFLOW_" + str(width))
            driver.command("POST","url",{"url":(path / "agentcredits.html").resolve().as_uri()})
            credits = driver.js("""
                document.getElementById('inspect').click();
                return {
                    status:document.getElementById('status').textContent,
                    available:document.getElementById('available').textContent,
                    held:document.getElementById('held').textContent,
                    spent:document.getElementById('spent').textContent,
                    duplicates:document.getElementById('duplicates').textContent,
                    rows:document.querySelectorAll('#rows tr').length,
                    csp:document.querySelector('meta[http-equiv="Content-Security-Policy"]')?.content,
                    remote:performance.getEntriesByType('resource').filter(x=>x.name.startsWith('http')).length
                };
            """)
            verify(credits["status"].startswith("PASS:") and credits["available"]=="80"
                   and credits["held"]=="0" and credits["spent"]=="20"
                   and credits["duplicates"]=="1" and credits["rows"]==1
                   and credits["remote"]==0 and "connect-src 'none'" in credits["csp"],
                   "AGENTCREDITS_POSITIVE_BALANCES")
            for button in ("overspend","conflict","refund"):
                result = driver.js("""
                    document.getElementById(arguments[0]).click();
                    return {
                        status:document.getElementById('status').textContent,
                        available:document.getElementById('available').textContent,
                        count:document.querySelectorAll('#rows tr').length
                    };
                """,[button])
                verify(result["status"].startswith("REJECTED:")
                       and result["available"]=="—" and result["count"]==0,
                       "AGENTCREDITS_FAIL_CLOSED_"+button.upper())
            duplicate_json = driver.js("""
                document.getElementById('journal').value=
                    '{"schema":"agentcredits.journal.v1","schema":"agentcredits.journal.v1","events":[]}';
                document.getElementById('inspect').click();
                return document.getElementById('status').textContent.startsWith('REJECTED:')
                    && document.querySelectorAll('#rows tr').length===0;
            """)
            verify(duplicate_json is True, "AGENTCREDITS_DUPLICATE_JSON_KEY")
            driver.js("document.getElementById('reset').click();return true;")
            verify(driver.js("""
                return document.getElementById('status').textContent.startsWith('PASS:')
                    && document.getElementById('available').textContent==='80';
            """) is True, "AGENTCREDITS_RESET_RECOVERY")
            for width,height in ((320,720),(375,812),(812,375),(1440,900)):
                driver.viewport(width,height)
                verify(driver.js("return document.documentElement.scrollWidth <= innerWidth;") is True,
                       "AGENTCREDITS_NO_OVERFLOW_"+str(width))
            driver.command("POST","url",{"url":(path/"model-cost.html").resolve().as_uri()})
            costs=driver.js("""
                document.getElementById('compare').click();
                return{
                    status:document.getElementById('status').textContent,
                    budget:document.getElementById('budget-display').textContent,
                    applied:document.getElementById('applied').textContent,
                    duplicates:document.getElementById('duplicates').textContent,
                    values:[...document.querySelectorAll('#rows tr')].map(row=>
                        [...row.querySelectorAll('td')].map(cell=>cell.textContent)),
                    remote:performance.getEntriesByType('resource').filter(e=>e.name.startsWith('http')).length
                };
            """)
            verify(costs["status"].startswith("HOLD:") and costs["budget"]=="0.000400000000"
                   and costs["applied"]=="2" and costs["duplicates"]=="1"
                   and len(costs["values"])==2 and costs["values"][0][3]=="0.000380000000"
                   and costs["values"][1][3]=="0.000460000000" and costs["remote"]==0,
                   "MODEL_COST_EXACT_DECIMAL_HOLD")
            verify(driver.js("""
                document.getElementById('budget').click();
                return document.getElementById('status').textContent.startsWith('PASS:')
                  && document.getElementById('budget-display').textContent==='0.001000000000';
            """) is True,"MODEL_COST_BUDGET_PROMOTION")
            for button in ("conflict","missing"):
                r=driver.js("""
                    document.getElementById(arguments[0]).click();
                    return{
                        status:document.getElementById('status').textContent,
                        count:document.querySelectorAll('#rows tr').length,
                        budget:document.getElementById('budget-display').textContent
                    };
                """,[button])
                verify(r["status"].startswith("REJECTED:") and r["count"]==0
                       and r["budget"]=="—","MODEL_COST_FAIL_CLOSED_"+button.upper())
            driver.js("document.getElementById('reset').click();return true;")
            verify(driver.js("""
                return document.getElementById('status').textContent.startsWith('HOLD:')
                  && document.querySelectorAll('#rows tr').length===2;
            """) is True,"MODEL_COST_RESET")
            for width,height in ((320,720),(375,812),(812,375),(1440,900)):
                driver.viewport(width,height)
                verify(driver.js("return document.documentElement.scrollWidth<=innerWidth;") is True,
                       "MODEL_COST_NO_OVERFLOW_"+str(width))
            driver.command("POST","url",{"url":(path/"model-fit.html").resolve().as_uri()})
            fit=driver.js("""
                document.getElementById('evaluate').click();
                return{
                    status:document.getElementById('status').textContent,
                    available:document.getElementById('available').textContent,
                    fits:document.getElementById('fits').textContent,
                    misses:document.getElementById('misses').textContent,
                    rows:[...document.querySelectorAll('#rows tr')].map(row=>
                        [...row.querySelectorAll('td')].map(cell=>cell.textContent)),
                    remote:performance.getEntriesByType('resource').filter(e=>e.name.startsWith('http')).length
                };
            """)
            verify(fit["status"].startswith("PASS:") and fit["available"]=="2560"
                   and fit["fits"]=="1" and fit["misses"]=="1" and len(fit["rows"])==2
                   and fit["rows"][0][0]=="fictional-small-q4" and fit["rows"][0][2]=="810"
                   and "RAM below estimate" in fit["rows"][1][5]
                   and fit["remote"]==0,"MODEL_FIT_EXPLICIT_RESOURCE_HEADROOM")
            verify(driver.js("""
                document.getElementById('constrained').click();
                return document.getElementById('status').textContent.startsWith('HOLD:')
                  && document.getElementById('fits').textContent==='0';
            """) is True,"MODEL_FIT_CONSTRAINED_HOLD")
            verify(driver.js("""
                document.getElementById('duplicate').click();
                return document.getElementById('status').textContent.startsWith('REJECTED:')
                  && document.querySelectorAll('#rows tr').length===0
                  && document.getElementById('fits').textContent==='—';
            """) is True,"MODEL_FIT_DUPLICATE_FAIL_CLOSED")
            verify(driver.js("""
                document.getElementById('reset').click();
                return document.getElementById('status').textContent.startsWith('PASS:')
                  && document.getElementById('fits').textContent==='1';
            """) is True,"MODEL_FIT_RESET")
            for width,height in ((320,720),(375,812),(812,375),(1440,900)):
                driver.viewport(width,height)
                verify(driver.js("return document.documentElement.scrollWidth<=innerWidth;") is True,
                       "MODEL_FIT_NO_OVERFLOW_"+str(width))
            driver.command("POST", "url", {"url":(path/"context-preservation.html").resolve().as_uri()})
            retention = driver.js("""
                document.getElementById('evaluate').click();
                return {
                    status:document.getElementById('status').textContent,
                    candidates:document.getElementById('candidates').textContent,
                    lossless:document.getElementById('lossless').textContent,
                    held:document.getElementById('held').textContent,
                    rows:[...document.querySelectorAll('#rows tr')].map(row=>
                      [...row.querySelectorAll('td')].map(x=>x.textContent)),
                    remote:performance.getEntriesByType('resource').filter(x=>x.name.startsWith('http')).length,
                    csp:document.querySelector('meta[http-equiv="Content-Security-Policy"]')?.content
                };
            """)
            by_name={x[0]:x for x in retention["rows"]}
            verify(retention["status"].startswith("RECORDED:")
                   and retention["candidates"]=="3" and retention["lossless"]=="1"
                   and retention["held"]=="2"
                   and by_name["brief-chat"][1]=="HOLD" and by_name["brief-chat"][2]=="1/4"
                   and by_name["evidence-checkpoint"][1]=="PASS_LOSSLESS"
                   and by_name["evidence-checkpoint"][2]=="4/4"
                   and by_name["unsafe-drift"][1]=="HOLD"
                   and retention["remote"]==0
                   and "connect-src 'none'" in retention["csp"],
                   "CONTEXT_PRESERVATION_THREE_REFERENCE_CASES")
            for button in ("drop","stale","promote"):
                r=driver.js("""
                    document.getElementById(arguments[0]).click();
                    const rows=[...document.querySelectorAll('#rows tr')];
                    const exact=rows.find(r=>r.querySelector('td')?.textContent==='evidence-checkpoint');
                    return {lossless:document.getElementById('lossless').textContent,
                            held:document.getElementById('held').textContent,
                            gate:exact?.querySelectorAll('td')[1].textContent,
                            findings:document.getElementById('findings').textContent};
                """,[button])
                verify(r["lossless"]=="0" and r["held"]=="3" and r["gate"]=="HOLD",
                       "CONTEXT_PRESERVATION_FAIL_CLOSED_"+button.upper())
            driver.js("""
                document.getElementById('fixture').value=
                  '{"schema":"context-preservation.v1","schema":"bad","source":{},"candidates":[]}';
                document.getElementById('evaluate').click();return true;
            """)
            verify(driver.js("""
                return document.getElementById('status').textContent.startsWith('REJECTED:')
                  && document.querySelectorAll('#rows tr').length===0
                  && document.getElementById('lossless').textContent==='—';
            """) is True,"CONTEXT_PRESERVATION_DUPLICATE_JSON_KEY_REJECTED")
            driver.js("document.getElementById('reset').click();return true;")
            verify(driver.js("""
                return document.getElementById('status').textContent.startsWith('RECORDED:')
                   && document.getElementById('lossless').textContent==='1';
            """) is True,"CONTEXT_PRESERVATION_RESET")
            for width,height in ((320,720),(375,812),(812,375),(1440,900)):
                driver.viewport(width,height)
                verify(driver.js("return document.documentElement.scrollWidth<=innerWidth;") is True,
                       "CONTEXT_PRESERVATION_NO_OVERFLOW_"+str(width))
            driver.command("POST","url",{"url":(path/"model-disagreement.html").resolve().as_uri()})
            disagreement=driver.js("""
                document.getElementById('inspect').click();
                return {
                    status:document.getElementById('status').textContent,
                    cases:document.getElementById('cases').textContent,
                    review:document.getElementById('review').textContent,
                    critical:document.getElementById('critical').textContent,
                    rows:[...document.querySelectorAll('#rows tr')].map(row=>
                        [...row.querySelectorAll('td')].map(cell=>cell.textContent)),
                    csp:document.querySelector('meta[http-equiv="Content-Security-Policy"]')?.content,
                    remote:performance.getEntriesByType('resource').filter(x=>x.name.startsWith('http')).length
                };
            """)
            cases={x[0]:x for x in disagreement["rows"]}
            verify(disagreement["status"].startswith("REVIEW:") and
                   disagreement["cases"]=="5" and disagreement["review"]=="4"
                   and disagreement["critical"]=="2" and len(cases)==5
                   and cases["unverified-consensus"][1]=="UNVERIFIED_CONSENSUS"
                   and cases["split-critical-decision"][1]=="DISAGREEMENT"
                   and cases["unanimous-wrong"][1]=="CONTRADICTS_SUPPLIED_REFERENCE"
                   and cases["missing-and-abstained"][1]=="INCOMPLETE"
                   and cases["matches-supplied"][1]=="MATCHES_SUPPLIED_REFERENCE"
                   and disagreement["remote"]==0
                   and "connect-src 'none'" in disagreement["csp"],
                   "MODEL_DISAGREEMENT_BASELINE_AND_FALSE_CONSENSUS")
            corrected=driver.js("""
                document.getElementById('reference').click();
                return {review:document.getElementById('review').textContent,
                        critical:document.getElementById('critical').textContent,
                        state:[...document.querySelectorAll('#rows tr')].find(r=>
                           r.querySelector('td')?.textContent==='unanimous-wrong')
                           ?.querySelectorAll('td')[1].textContent};
            """)
            verify(corrected["review"]=="3" and corrected["critical"]=="1" and
                   corrected["state"]=="MATCHES_SUPPLIED_REFERENCE",
                   "MODEL_DISAGREEMENT_CORRECTED_FICTIONAL_CONSENSUS")
            for button,state in (("split","DISAGREEMENT"),("missing","INCOMPLETE"),("abstain","INCOMPLETE")):
                outcome=driver.js("""
                    document.getElementById(arguments[0]).click();
                    const name=arguments[1];
                    return [...document.querySelectorAll('#rows tr')].find(r=>
                        r.querySelector('td')?.textContent===name)
                        ?.querySelectorAll('td')[1].textContent;
                """,[button,"unverified-consensus" if button=="split" else "matches-supplied"])
                verify(outcome==state,"MODEL_DISAGREEMENT_NEGATIVE_"+button.upper())
            duplicate=driver.js("""
                document.getElementById('fixture').value=
                  '{"schema":"model-disagreement.fixtures.v1","schema":"bad","models":[],"cases":[]}';
                document.getElementById('inspect').click();
                return document.getElementById('status').textContent.startsWith('REJECTED:')
                    && document.querySelectorAll('#rows tr').length===0
                    && document.getElementById('cases').textContent==='—';
            """)
            verify(duplicate is True,"MODEL_DISAGREEMENT_DUPLICATE_JSON_FAIL_CLOSED")
            driver.js("document.getElementById('reset').click();return true;")
            verify(driver.js("""
                return document.getElementById('status').textContent.startsWith('REVIEW:')
                    && document.getElementById('review').textContent==='4';
            """) is True,"MODEL_DISAGREEMENT_RESET")
            for width,height in ((320,720),(375,812),(812,375),(1440,900)):
                driver.viewport(width,height)
                verify(driver.js("return document.documentElement.scrollWidth<=innerWidth;") is True,
                       "MODEL_DISAGREEMENT_NO_OVERFLOW_"+str(width))
            driver.command("POST","url",{"url":(path/"decision-review.html").resolve().as_uri()})
            explain=driver.js("""
                document.getElementById('inspect').click();
                return {
                    status:document.getElementById('status').textContent,
                    total:document.getElementById('total').textContent,
                    holds:document.getElementById('holds').textContent,
                    needs:document.getElementById('needs').textContent,
                    recorded:document.getElementById('recorded').textContent,
                    rows:[...document.querySelectorAll('#rows tr')].map(r=>
                        [...r.querySelectorAll('td')].map(x=>x.textContent)),
                    evidence:document.getElementById('evidence').textContent,
                    csp:document.querySelector('meta[http-equiv="Content-Security-Policy"]')?.content,
                    remote:performance.getEntriesByType('resource').filter(x=>x.name.startsWith('http')).length
                };
            """)
            cases={r[0]:r for r in explain["rows"]}
            verify(explain["status"].startswith("RECORDED:") and
                   explain["total"]=="6" and explain["holds"]=="3"
                   and explain["needs"]=="2" and explain["recorded"]=="1"
                   and cases["routine"][1]=="REVIEW_RECORDED_NOT_AUTHORIZED"
                   and cases["high-impact"][1]=="HUMAN_REVIEW_REQUIRED"
                   and cases["contradicted"][1]=="HOLD"
                   and cases["stale"][1]=="HOLD"
                   and cases["unverified"][1]=="HOLD"
                   and cases["unscored"][1]=="HUMAN_REVIEW_REQUIRED"
                   and "source" not in cases["routine"][1].lower()
                   and "DECLARED_VERIFIED_MATCH" in explain["evidence"]
                   and "Execution authority: NONE" in explain["evidence"]
                   and explain["remote"]==0 and "connect-src 'none'" in explain["csp"],
                   "EXPLAINABLE_REVIEW_BOUNDARIES_AND_EVIDENCE")
            for button in ("stale","opposing","hypothesis","reject"):
                result=driver.js("""
                    document.getElementById(arguments[0]).click();
                    const item=[...document.querySelectorAll('#rows tr')].find(r=>
                        r.querySelector('td')?.textContent==='routine');
                    return {holds:document.getElementById('holds').textContent,
                            recorded:document.getElementById('recorded').textContent,
                            gate:item?.querySelectorAll('td')[1].textContent};
                """,[button])
                verify(result["holds"]=="4" and result["recorded"]=="0"
                       and result["gate"]=="HOLD",
                       "EXPLAINABLE_REVIEW_HOLD_"+button.upper())
            review=driver.js("""
                document.getElementById('no-confidence').click();
                return {holds:document.getElementById('holds').textContent,
                        needs:document.getElementById('needs').textContent,
                        recorded:document.getElementById('recorded').textContent};
            """)
            verify(review["holds"]=="3" and review["needs"]=="3"
                   and review["recorded"]=="0","EXPLAINABLE_NO_CONFIDENCE_METHOD_REVIEW")
            invalid=driver.js("""
                document.getElementById('fixture').value=
                  '{"schema":"explainable-review.fixtures.v1","schema":"wrong","sources":[],"decisions":[]}';
                document.getElementById('inspect').click();
                return document.getElementById('status').textContent.startsWith('REJECTED:')
                    && document.querySelectorAll('#rows tr').length===0
                    && document.getElementById('total').textContent==='—';
            """)
            verify(invalid is True,"EXPLAINABLE_DUPLICATE_JSON_FAIL_CLOSED")
            driver.js("document.getElementById('reset').click();return true;")
            verify(driver.js("""
                return document.getElementById('status').textContent.startsWith('RECORDED:')
                    && document.getElementById('recorded').textContent==='1';
            """) is True,"EXPLAINABLE_RESET")
            for width,height in ((320,720),(375,812),(812,375),(1440,900)):
                driver.viewport(width,height)
                verify(driver.js("return document.documentElement.scrollWidth<=innerWidth;") is True,
                       "EXPLAINABLE_NO_OVERFLOW_"+str(width))
            driver.command("POST","url",{"url":(path/"agent-trust.html").resolve().as_uri()})
            claim_info=None
            for _ in range(30):
                claim_info=driver.js("""
                    const s=document.getElementById('status').textContent;
                    return {ready:s.startsWith('RECORDED:'),
                            error:s.startsWith('REJECTED:'),
                            status:s};
                """)
                if claim_info["ready"] or claim_info["error"]:
                    break
                time.sleep(.12)
            verify(claim_info["ready"],"TRUST_BROWSER_INITIALIZE_"+claim_info["status"][:65])
            results=driver.js("""
                return {total:document.getElementById('total').textContent,
                        held:document.getElementById('held').textContent,
                        matching:document.getElementById('matching').textContent,
                        authenticated:document.getElementById('authenticated').textContent,
                        rows:[...document.querySelectorAll('#rows tr')].map(r=>
                           [...r.querySelectorAll('td')].map(x=>x.textContent)),
                        csp:document.querySelector('meta[http-equiv="Content-Security-Policy"]')?.content,
                        remote:performance.getEntriesByType('resource').filter(x=>x.name.startsWith('http')).length};
            """)
            by_id={r[0]:r for r in results["rows"]}
            verify(results["total"]=="11" and results["held"]=="10"
                   and results["matching"]=="1" and results["authenticated"]=="0"
                   and by_id["matching-claim"][2]=="CLAIM_MATCH_ONLY"
                   and by_id["revoked-agent"][2]=="HOLD"
                   and by_id["unknown-agent"][2]=="HOLD"
                   and by_id["wrong-origin"][2]=="HOLD"
                   and by_id["wrong-key"][2]=="HOLD"
                   and by_id["capability-escalation"][2]=="HOLD"
                   and by_id["stale-registry"][2]=="HOLD"
                   and by_id["nonce-replay-first"][2]=="HOLD"
                   and by_id["nonce-replay-second"][2]=="HOLD"
                   and by_id["expired"][2]=="HOLD"
                   and by_id["checksum-tamper"][2]=="HOLD"
                   and by_id["checksum-tamper"][4]=="MISMATCH"
                   and all(r[5]=="NOT VERIFIED" for r in results["rows"])
                   and results["remote"]==0
                   and "connect-src 'none'" in results["csp"],
                   "TRUST_BASELINE_FICTIONAL_HOLD_AND_NOT_AUTHENTICATED")
            for btn,reason in (("revoke","REVOKED_REGISTRATION"),
                               ("scope","CAPABILITY_NOT_DECLARED"),
                               ("replay","REPLAYED_NONCE"),
                               ("tamper","CHECKSUM_MISMATCH")):
                driver.js("document.getElementById(arguments[0]).click();return true;",[btn])
                info={}
                for _ in range(30):
                    info=driver.js("""
                        const s=document.getElementById('status').textContent;
                        const row=[...document.querySelectorAll('#rows tr')].find(x=>
                            x.querySelector('td')?.textContent==='matching-claim');
                        return {ready:s.startsWith('RECORDED:'),error:s.startsWith('REJECTED:'),
                                held:document.getElementById('held').textContent,
                                gate:row?.querySelectorAll('td')[2].textContent,
                                reasons:row?.querySelectorAll('td')[3].textContent};
                    """)
                    if info["ready"] or info["error"]:
                        break
                    time.sleep(.12)
                verify(info["ready"] and info["gate"]=="HOLD"
                       and reason in info["reasons"] and info["held"]=="11",
                       "TRUST_FICTIONAL_NEGATIVE_"+btn.upper())
            duplicate=driver.js("""
                document.getElementById('fixture').value=
                  '{"schema":"agent-trust-claims.v1","schema":"wrong","registry":[],"claims":[],"evaluation_tick":1}';
                document.getElementById('check').click();return true;
            """)
            bad={}
            for _ in range(30):
                bad=driver.js("""
                    const s=document.getElementById('status').textContent;
                    return {reject:s.startsWith('REJECTED:'),
                            rows:document.querySelectorAll('#rows tr').length,
                            metric:document.getElementById('total').textContent};
                """)
                if bad["reject"]:break
                time.sleep(.12)
            verify(bad["reject"] and bad["rows"]==0 and bad["metric"]=="—",
                   "TRUST_DUPLICATE_JSON_FAIL_CLOSED")
            driver.js("document.getElementById('reset').click();return true;")
            recovered={}
            for _ in range(30):
                recovered=driver.js("""
                    return {status:document.getElementById('status').textContent,
                            held:document.getElementById('held').textContent,
                            match:document.getElementById('matching').textContent};
                """)
                if recovered["status"].startswith("RECORDED:") or recovered["status"].startswith("REJECTED:"):
                    break
                time.sleep(.12)
            verify(recovered["status"].startswith("RECORDED:") and
                   recovered["held"]=="10" and recovered["match"]=="1",
                   "TRUST_RESET")
            for width,height in ((320,720),(375,812),(812,375),(1440,900)):
                driver.viewport(width,height)
                verify(driver.js("return document.documentElement.scrollWidth<=innerWidth;") is True,
                       "TRUST_NO_OVERFLOW_"+str(width))
            driver.command("POST","url",{"url":(path/"signed-agent.html").resolve().as_uri()})
            initial=None
            for _ in range(60):
                initial=driver.js("""
                    return {ready:document.getElementById('status').textContent.startsWith('READY:'),
                            fail:document.getElementById('status').textContent.startsWith('REJECTED:'),
                            status:document.getElementById('status').textContent};
                """)
                if initial["ready"] or initial["fail"]:break
                time.sleep(.1)
            verify(initial["ready"],"SIGNED_CHALLENGE_WEB_CRYPTO_AVAILABLE_"+initial["status"][:65])
            def action(btn, expected_gate, sig_state):
                driver.js("document.getElementById(arguments[0]).click();return true;",[btn])
                report={}
                for _ in range(60):
                    report=driver.js("""
                        return {done:document.getElementById('status').textContent.startsWith('RESULT:'),
                                fail:document.getElementById('status').textContent.startsWith('REJECTED:'),
                                gate:document.getElementById('gate').textContent,
                                sig:document.getElementById('signature').textContent,
                                nonce:document.getElementById('nonce-state').textContent,
                                auth:document.getElementById('authorization').textContent,
                                challenge:document.getElementById('challenge').textContent};
                    """)
                    if report["done"] or report["fail"]:break
                    time.sleep(.1)
                verify(report["done"] and report["gate"]==expected_gate
                       and report["sig"]==sig_state and report["auth"]=="NONE"
                       and '"nonce"' in report["challenge"],
                       "SIGNED_CHALLENGE_"+btn.upper()+"_"+report.get("gate","missing"))
                return report
            good=action("valid","VERIFIED_NOT_AUTHORIZED","VALID")
            verify(good["nonce"]=="YES","SIGNED_CHALLENGE_NONCE_CONSUMED")
            action("wrong-key","INVALID_SIGNATURE","INVALID")
            action("scope","UNAUTHORIZED_SCOPE","NOT CHECKED")
            replay=action("replay","REPLAYED_CHALLENGE","VALID")
            verify(replay["nonce"]=="ALREADY CONSUMED","SIGNED_CHALLENGE_REPLAY")
            action("expired","EXPIRED_CHALLENGE","NOT CHECKED")
            action("revoked","REVOKED_KEY","NOT CHECKED")
            driver.js("document.getElementById('reset').click();return true;")
            reset={}
            for _ in range(60):
                reset=driver.js("""
                    return {status:document.getElementById('status').textContent,
                            gate:document.getElementById('gate').textContent};
                """)
                if reset["status"].startswith("READY:") or reset["status"].startswith("REJECTED:"):break
                time.sleep(.1)
            verify(reset["status"].startswith("READY:") and reset["gate"]=="READY",
                   "SIGNED_CHALLENGE_FRESH_EPHEMERAL_KEY_RESET")
            details=driver.js("""
                return {remote:performance.getEntriesByType('resource').filter(x=>
                          x.name.startsWith('http')).length,
                        csp:document.querySelector('meta[http-equiv="Content-Security-Policy"]')?.content,
                        script:document.querySelectorAll('script').length};
            """)
            verify(details["remote"]==0 and details["script"]==1
                   and "connect-src 'none'" in details["csp"],
                   "SIGNED_CHALLENGE_NO_REMOTE_ASSETS")
            for width,height in ((320,720),(375,812),(812,375),(1440,900)):
                driver.viewport(width,height)
                verify(driver.js("return document.documentElement.scrollWidth<=innerWidth;") is True,
                       "SIGNED_CHALLENGE_NO_OVERFLOW_"+str(width))
            # No browser-controlled payment activation: compare the exact destinations
            # rendered from the owner-reviewed manifest, whether pending or active.
            approved_support=load_channels(SUPPORT_CONFIG_SOURCE)
            driver.command("POST", "url", {"url": (path / "support.html").resolve().as_uri()})
            support_page=driver.js("""
                return {
                    main:document.querySelectorAll('main').length,
                    headings:document.querySelectorAll('.panel h2').length,
                    pending:document.querySelectorAll('.pending').length,
                    scripts:document.querySelectorAll('script').length,
                    addresses:[...document.querySelectorAll('.wallets code')].map(x=>x.textContent),
                    chainTitles:[...document.querySelectorAll('.wallets li strong')].map(x=>x.textContent),
                    selectable:[...document.querySelectorAll('.wallets code')].every(x=>getComputedStyle(x).userSelect==='all' && x.tabIndex===0),
                    cryptoFirst:document.querySelector('section.panel h2')?.textContent==='Direct crypto support',
                    links:[...document.querySelectorAll('a')].map(x=>x.href),
                    csp:document.querySelector('meta[http-equiv="Content-Security-Policy"]')?.content,
                    remote:performance.getEntriesByType('resource').filter(x=>x.name.startsWith('http')).length
                };
            """)
            states=[approved_support["github_sponsors"]["state"],
                    approved_support["fiat"]["state"],approved_support["crypto"]["state"]]
            expected_pay_urls=[]
            if states[0]=="active":expected_pay_urls.append(approved_support["github_sponsors"]["url"])
            if states[1]=="active":expected_pay_urls.append(approved_support["fiat"]["url"])
            actual_pay_urls=[url for url in support_page["links"] if
                any(host in url for host in ("github.com/sponsors/","pay.yoco.com/","paystack.com/pay/"))]
            expected_wallets=[x["address"] for x in approved_support["crypto"]["wallets"]]
            verify(support_page["main"]==1 and support_page["headings"]==3
                   and support_page["pending"]==states.count("pending")
                   and support_page["scripts"]==0 and support_page["remote"]==0
                   and "connect-src 'none'" in support_page["csp"]
                   and sorted(actual_pay_urls)==sorted(expected_pay_urls)
                   and sorted(support_page["addresses"])==sorted(expected_wallets)
                   and support_page["cryptoFirst"]
                   and (not expected_wallets or (
                       support_page["selectable"] and
                       support_page["chainTitles"]==
                           ["BTC · Bitcoin", "USDT · Solana",
                            "USDT · Ethereum (ERC-20)", "USDT · Tron (TRC-20)"])),
                   "SUPPORT_CONFIG_MATCHES_RENDERED_DESTINATIONS")
            for width,height in ((320,720),(1440,900)):
                driver.viewport(width,height)
                verify(driver.js("return document.documentElement.scrollWidth<=innerWidth;") is True,
                       "SUPPORT_NO_OVERFLOW_"+str(width))
            print(json.dumps({
                "schema":"oss-directory-browser-qa-v1","status":"PASS",
                "browser":version,"publicCards":11,"additionalToolsLinked":21,
                "responsiveWidths":[320,375,812,1440],
                "networkAssets":0,"interactiveToolsChecked":11,"supportPageDestinationsChecked":True,"screenReaderTested":False
            },sort_keys=True))
        finally:
            driver.close()


if __name__ == "__main__":
    run()
