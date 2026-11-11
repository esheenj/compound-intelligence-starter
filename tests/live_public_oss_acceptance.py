"""Read-only LIVE HTTPS Chrome acceptance for 21 existing public pages.

Unlike loopback source/staging checks, this opens deployed GitHub Pages.
Fixed allowlisted URLs; no secrets, auth, data uploads, CI mutations or
external browser packages. Failure is evidence, never silently skipped.
"""
from __future__ import annotations

import json
import socket
import time
from browser_check_issue_report import Driver, driver_executable

ENTRY_SITES = {
    "compound-intelligence-starter": "https://esheenj.github.io/compound-intelligence-starter/",
    "design-system-foundations-oss": "https://esheenj.github.io/design-system-foundations-oss/",
    "mobile-first-flow-kit-oss": "https://esheenj.github.io/mobile-first-flow-kit-oss/",
    "data-table-interactions-oss": "https://esheenj.github.io/data-table-interactions-oss/",
    "flow-state-machine-oss": "https://esheenj.github.io/flow-state-machine-oss/",
    "form-experience-kit-oss": "https://esheenj.github.io/form-experience-kit-oss/",
    "visual-regression-starter-oss": "https://esheenj.github.io/visual-regression-starter-oss/",
}
EARLY_URLS = {
    "wave": "https://esheenj.github.io/compound-intelligence-starter/mvp-wave.html",
    "recovery": "https://esheenj.github.io/mobile-first-flow-kit-oss/recovery.html",
    "audit": "https://esheenj.github.io/design-system-foundations-oss/audit.html",
    "experiment": "https://esheenj.github.io/data-table-interactions-oss/experiment.html",
}

URLS = {
    "onboarding": "https://esheenj.github.io/form-experience-kit-oss/onboarding.html",
    "journey": "https://esheenj.github.io/flow-state-machine-oss/journey.html",
    "quality": "https://esheenj.github.io/data-table-interactions-oss/quality.html",
    "consent": "https://esheenj.github.io/form-experience-kit-oss/consent.html",
    "notifications": "https://esheenj.github.io/mobile-first-flow-kit-oss/notifications.html",
    "blueprint": "https://esheenj.github.io/flow-state-machine-oss/blueprint.html",
    "agentops": "https://esheenj.github.io/compound-intelligence-starter/agentops.html",
    "agentproof": "https://esheenj.github.io/compound-intelligence-starter/agentproof.html",
    "agentcredits": "https://esheenj.github.io/compound-intelligence-starter/agentcredits.html",
    "approval": "https://esheenj.github.io/flow-state-machine-oss/approval.html",
}
READY = {
    "onboarding": "#status",
    "journey": "#status",
    "quality": "#status",
    "consent": "#analytics",
    "notifications": "#status",
    "blueprint": "#status",
    "agentops": "#inspect",
    "agentproof": "#check",
    "agentcredits": "#inspect",
    "approval": "#state",
}


def verify(value: bool, code: str) -> None:
    if value is not True:
        raise AssertionError(code)


def open_static(driver: Driver, label: str, url: str) -> None:
    """Verify an actual public HTTPS page and its semantic visible content."""
    driver.command("POST", "url", {"url": url})
    for _ in range(45):
        loaded = driver.js("""
            return document.readyState!=='loading' &&
              document.querySelector('h1')?.textContent.trim().length>0 &&
              document.querySelectorAll('main').length===1;
        """)
        if loaded is True:
            break
        time.sleep(0.2)
    else:
        raise AssertionError("LIVE_" + label.upper() + "_SITE_NOT_READY")
    origin = driver.js("return location.protocol==='https:' && location.host==='esheenj.github.io';")
    verify(origin is True, "LIVE_" + label.upper() + "_HTTPS_ORIGIN")


def interact_early(driver: Driver, kind: str) -> None:
    """Small live actions on the four previously browser-smoked early add-ons."""
    if kind == "wave":
        verify(driver.js("""
            document.querySelector('#plan').click();
            const good=document.querySelectorAll('#results li').length===3;
            document.querySelector('#fixture').value='{"invalid":true}';
            document.querySelector('#plan').click();
            return good && document.querySelector('#status').textContent.startsWith('Rejected:')
                && document.querySelectorAll('#results li').length===0;
        """) is True, "LIVE_WAVE_PLANNER_AND_INVALID")
    elif kind == "recovery":
        verify(driver.js("""
            const $=id=>document.getElementById(id);
            if($('phase').textContent!=='Ready')return false;
            $('start').click();$('fail').click();
            if($('phase').textContent!=='Recovery needed')return false;
            for(let i=0;i<2;i++){$('retry').click();$('fail').click();}
            const exhausted=$('status').textContent.includes('budget reached')
                && $('retry').hidden;
            $('reset').click();
            return exhausted && $('phase').textContent==='Ready';
        """) is True, "LIVE_RECOVERY_BOUNDED_RETRIES")
    elif kind == "audit":
        verify(driver.js("""
            document.querySelector('#run-audit').click();
            const good=document.querySelector('#status').textContent.includes('3 illustrative findings')
                && document.querySelectorAll('#rows li').length===2;
            document.querySelector('#fixture').value='[{"bad":true}]';
            document.querySelector('#run-audit').click();
            return good && document.querySelector('#status').textContent.includes('Rejected:');
        """) is True, "LIVE_AUDIT_FINDINGS_AND_INVALID")
    elif kind == "experiment":
        verify(driver.js("""
            const $=id=>document.getElementById(id);
            const good=$('decision').textContent==='DESCRIPTIVE UPLIFT ONLY';
            const data=JSON.parse($('sheet').value);
            data.candidate.errors=17;
            $('sheet').value=JSON.stringify(data);$('evaluate').click();
            const held=$('decision').textContent==='HOLD ERROR GUARDRAIL';
            $('sheet').value='{"baseline":{}}';$('evaluate').click();
            return good&&held&&$('status').textContent.startsWith('Rejected:');
        """) is True, "LIVE_EXPERIMENT_HOLD_AND_INVALID")


def open_page(driver: Driver, kind: str) -> None:
    url = URLS[kind]
    driver.command("POST", "url", {"url": url})
    for _ in range(45):
        loaded = driver.js("""
            const target=document.querySelector(arguments[0]);
            return document.readyState!=='loading' && target!==null
                 && (target.tagName==='INPUT' || target.tagName==='BUTTON'
                     || target.textContent.trim().length>0);
        """, [READY[kind]])
        if loaded:
            break
        time.sleep(0.2)
    else:
        raise AssertionError("LIVE_" + kind.upper() + "_PAGE_NOT_READY")
    page = driver.js("""
        return {protocol:location.protocol,host:location.host,
          main:document.querySelectorAll('main').length,
          h1:document.querySelectorAll('h1').length,
          csp:document.querySelector('meta[http-equiv="Content-Security-Policy"]')?.content||'',
          external:performance.getEntriesByType('resource').filter(
            item=>!item.name.startsWith(location.origin+'/')).length};
    """)
    verify(page["protocol"] == "https:" and page["host"] == "esheenj.github.io",
           "LIVE_" + kind.upper() + "_ORIGIN")
    verify(page["main"] == 1 and page["h1"] == 1,
           "LIVE_" + kind.upper() + "_LANDMARKS")
    verify("connect-src 'none'" in page["csp"] and page["external"] == 0,
           "LIVE_" + kind.upper() + "_OFFLINE_ASSETS")


def interact(driver: Driver, kind: str) -> None:
    if kind == "onboarding":
        verify(driver.js("""
            return document.querySelector('#status').textContent.includes('4 heuristic flags')
                && document.querySelectorAll('#flags li').length===4;
        """) is True, "LIVE_ONBOARDING_BASELINE")
        verify(driver.js("""
            const el=document.querySelector('#input');el.value='[{"bad":true}]';
            document.querySelector('#review').click();
            return document.querySelector('#status').textContent.startsWith('Rejected:')
                && document.querySelector('#output').hidden;
        """) is True, "LIVE_ONBOARDING_INVALID")
    elif kind == "journey":
        verify(driver.js("""
            return document.querySelector('#status').textContent.includes('4 illustrative friction')
                && document.querySelectorAll('#steps li').length===3;
        """) is True, "LIVE_JOURNEY_BASELINE")
        verify(driver.js("""
            document.querySelector('#input').value='[{}]';
            document.querySelector('#map').click();
            return document.querySelector('#status').textContent.startsWith('Rejected:')
                && document.querySelector('#summary').hidden;
        """) is True, "LIVE_JOURNEY_INVALID")
    elif kind == "quality":
        verify(driver.js("""
            return document.querySelector('#status').textContent.includes('6 findings')
                && document.querySelectorAll('#rows li').length===3;
        """) is True, "LIVE_QUALITY_BASELINE")
        verify(driver.js("""
            document.querySelector('#input').value='[{"id":"x"}]';
            document.querySelector('#inspect').click();
            return document.querySelector('#status').textContent.startsWith('Rejected:')
                && document.querySelector('#output').hidden;
        """) is True, "LIVE_QUALITY_INVALID")
    elif kind == "consent":
        verify(driver.js("""
            return document.querySelector('#necessary').checked
              && document.querySelector('#necessary').disabled
              && !document.querySelector('#analytics').checked
              && !document.querySelector('#personalization').checked;
        """) is True, "LIVE_CONSENT_DEFAULTS")
        verify(driver.js("""
            document.querySelector('#accept').click();
            const accepted=document.querySelector('#analytics').checked
              && document.querySelector('#personalization').checked;
            document.querySelector('#withdraw').click();
            return accepted && !document.querySelector('#analytics').checked
              && !document.querySelector('#personalization').checked
              && document.querySelector('#necessary').checked;
        """) is True, "LIVE_CONSENT_WITHDRAWAL")
    elif kind == "notifications":
        verify(driver.js("""
            return document.querySelector('#status').textContent.includes('3 visible')
                && document.querySelectorAll('#notices li').length===3;
        """) is True, "LIVE_NOTIFICATIONS_DEFAULTS")
        verify(driver.js("""
            const buttons=[...document.querySelectorAll('button')];
            const snooze=buttons.find(b=>b.textContent.includes('Snooze visually'));
            if(!snooze)return false;
            snooze.click();
            const held=document.querySelector('#status').textContent.includes('1 snoozed');
            document.querySelector('#reset').click();
            return held && document.querySelector('#status').textContent.includes('3 visible');
        """) is True, "LIVE_NOTIFICATIONS_SNOOZE_RESET")
    elif kind == "blueprint":
        verify(driver.js("""
            return document.querySelector('#status').textContent.includes('3 illustrative flags')
              && document.querySelectorAll('#rows li').length===3
              && document.querySelector('#wait').textContent.includes('38 minutes');
        """) is True, "LIVE_BLUEPRINT_BASELINE")
        verify(driver.js("""
            document.querySelector('#input').value='[{}]';
            document.querySelector('#map').click();
            return document.querySelector('#status').textContent.startsWith('Rejected:')
                && document.querySelector('#output').hidden;
        """) is True, "LIVE_BLUEPRINT_INVALID")
    elif kind == "agentops":
        verify(driver.js("""
            document.querySelector('#inspect').click();
            return document.querySelector('#status').textContent.startsWith('PASS:')
              && document.querySelector('#units').textContent==='7'
              && document.querySelector('#duplicates').textContent==='1';
        """) is True, "LIVE_AGENTOPS_REPLAY")
        verify(driver.js("""
            document.querySelector('#missing').click();
            const held=document.querySelector('#status').textContent.startsWith('HOLD:');
            document.querySelector('#conflict').click();
            const rejected=document.querySelector('#status').textContent.startsWith('Rejected:');
            document.querySelector('#reset').click();
            return held && rejected && document.querySelector('#status').textContent.startsWith('PASS:');
        """) is True, "LIVE_AGENTOPS_HOLD_CONFLICT_RECOVERY")
    elif kind == "agentproof":
        driver.js("document.querySelector('#check').click();return true;")
        time.sleep(0.4)
        verify(driver.js("""
            return document.querySelector('#status').textContent.startsWith('PASS:')
                && document.querySelector('#count').textContent==='3'
                && document.querySelector('#digests').textContent==='3'
                && document.querySelector('#failures').textContent==='0';
        """) is True, "LIVE_AGENTPROOF_HASH_BASELINE")
        driver.js("document.querySelector('#tamper').click();return true;")
        time.sleep(0.25)
        verify(driver.js("""
            return document.querySelector('#status').textContent.startsWith('REJECTED:')
                && document.querySelector('#findings').textContent.includes('digest mismatch');
        """) is True, "LIVE_AGENTPROOF_TAMPER")
        driver.js("document.querySelector('#duplicate').click();return true;")
        time.sleep(0.25)
        verify(driver.js("""
            return document.querySelector('#status').textContent.startsWith('REJECTED:')
                && document.querySelector('#findings').textContent.includes('duplicate event ID');
        """) is True, "LIVE_AGENTPROOF_REPLAY_ID")
        driver.js("document.querySelector('#missing').click();return true;")
        time.sleep(0.25)
        verify(driver.js("""
            return document.querySelector('#status').textContent.startsWith('REJECTED:')
                && document.querySelector('#findings').textContent.includes('missing or unexpected fields');
        """) is True, "LIVE_AGENTPROOF_MISSING_ISSUER")
        driver.js("document.querySelector('#reset').click();return true;")
        time.sleep(0.25)
        verify(driver.js("""
            return document.querySelector('#status').textContent.startsWith('PASS:');
        """) is True, "LIVE_AGENTPROOF_RESET")
    elif kind == "agentcredits":
        result = driver.js("""
            document.getElementById('inspect').click();
            return {
                status:document.getElementById('status').textContent,
                available:document.getElementById('available').textContent,
                held:document.getElementById('held').textContent,
                spent:document.getElementById('spent').textContent,
                duplicates:document.getElementById('duplicates').textContent
            };
        """)
        verify(result["status"].startswith("PASS:") and result["available"] == "80"
               and result["held"] == "0" and result["spent"] == "20"
               and result["duplicates"] == "1", "LIVE_AGENTCREDITS_BALANCE")
        for button in ("overspend","conflict","refund"):
            failed = driver.js("""
                document.getElementById(arguments[0]).click();
                return {
                    status:document.getElementById('status').textContent,
                    balance:document.getElementById('available').textContent,
                    partial:document.querySelectorAll('#rows tr').length
                };
            """,[button])
            verify(failed["status"].startswith("REJECTED:")
                   and failed["balance"] == "—" and failed["partial"] == 0,
                   "LIVE_AGENTCREDITS_FAIL_CLOSED_"+button.upper())
        driver.js("document.getElementById('reset').click();return true;")
        verify(driver.js("""
            return document.getElementById('status').textContent.startsWith('PASS:')
                && document.getElementById('available').textContent==='80';
        """) is True, "LIVE_AGENTCREDITS_RESET")
    elif kind == "approval":
        verify(driver.js("""
            return document.querySelector('#state').textContent==='PENDING';
        """) is True, "LIVE_APPROVAL_PENDING")
        verify(driver.js("""
            document.querySelector('#simulate').click();
            const blocked=document.querySelector('#counts').textContent.includes('1 blocked attempts');
            document.querySelector('#approve').click();
            const approved=document.querySelector('#state').textContent==='APPROVED';
            document.querySelector('#simulate').click();
            const simulated=document.querySelector('#state').textContent==='SIMULATED';
            const policy=document.querySelector('#notice').textContent.includes('NEVER');
            return blocked && approved && simulated && policy;
        """) is True, "LIVE_APPROVAL_DENY_THEN_SIMULATE")


def run() -> dict:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    driver = Driver(driver_executable(), port)
    checked = []
    try:
        version = driver.start()
        for repo, url in ENTRY_SITES.items():
            open_static(driver, repo, url)
            checked.append({"kind": "repository-home", "repo": repo, "url": url,
                            "result": "PASS", "interaction_scope": "HTTPS load and semantic landmarks"})
        for kind, url in EARLY_URLS.items():
            open_static(driver, kind, url)
            interact_early(driver, kind)
            for width, height in ((320, 720), (1440, 900)):
                driver.viewport(width, height)
                verify(driver.js("return document.documentElement.scrollWidth<=innerWidth+1;") is True,
                       "LIVE_" + kind.upper() + "_RESPONSIVE_" + str(width))
            checked.append({"kind": "early-addon", "tool": kind, "url": url,
                            "result": "PASS", "interaction_scope": "HTTPS interaction",
                            "responsive_widths": [320, 1440]})
        for kind in URLS:
            open_page(driver, kind)
            interact(driver, kind)
            for width, height in ((320, 720), (1440, 900)):
                driver.viewport(width, height)
                verify(driver.js("return document.documentElement.scrollWidth<=innerWidth+1;") is True,
                       "LIVE_" + kind.upper() + "_RESPONSIVE_" + str(width))
            checked.append({"tool": kind, "url": URLS[kind], "result": "PASS",
                            "responsive_widths": [320, 1440],
                            "independent_https_interaction": True})
        return {
            "schema": "esheen-public-live-oss-acceptance-v1",
            "state": "PASS", "tested_at": "workflow-runtime",
            "browser": "Google Chrome", "browser_version": version,
            "pages_tested": len(checked), "checks": checked,
            "wcag_certified": False, "screen_reader_tested": False,
            "proof_type": "remote HTTPS: 7 public landing pages loaded and 14 add-ons exercised in Chrome; not user-device acceptance",
        }
    finally:
        driver.close()


if __name__ == "__main__":
    try:
        print(json.dumps(run(), sort_keys=True, indent=2))
    except (AssertionError, OSError, RuntimeError, TimeoutError) as exc:
        print(json.dumps({"schema": "esheen-public-live-oss-acceptance-v1",
                          "state": "FAILED", "error": str(exc)[:130]}, sort_keys=True))
        raise SystemExit(1)
