"""Read-only post-publish acceptance for the public Esheen Labs support page.

This checks the ACTUAL deployed HTTPS page against the GitHub-reviewed
payment destination manifest. No payment, signing, wallet connection, key,
real merchant interaction or transfer is ever initiated.
"""
from __future__ import annotations

import json
import socket
import sys
import time
from pathlib import Path

from browser_check_issue_report import Driver, driver_executable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.render_support import load_channels, NETWORK_LABEL

URL = "https://esheenj.github.io/compound-intelligence-starter/support.html"


def verify(ok: bool, code: str) -> None:
    if ok is not True:
        raise AssertionError(code)


def run() -> dict:
    approved = load_channels(ROOT / "support" / "channels.json")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    driver = Driver(driver_executable(), port)
    try:
        chrome = driver.start()
        driver.command("POST", "url", {"url": URL})
        for _ in range(48):
            ready = driver.js("""
                return document.readyState !== 'loading'
                  && document.querySelector('main h1')?.textContent.includes('Keep useful tools');
            """)
            if ready:
                break
            time.sleep(.25)
        else:
            raise AssertionError("SUPPORT_LIVE_PAGE_NOT_READY_OR_STALE")
        page = driver.js("""
            return {
                url:location.href,
                origin:location.origin,
                title:document.title,
                main:document.querySelectorAll('main').length,
                cards:document.querySelectorAll('section.panel').length,
                pending:document.querySelectorAll('.pending').length,
                scripts:document.querySelectorAll('script').length,
                forms:document.querySelectorAll('form').length,
                csp:document.querySelector('meta[http-equiv="Content-Security-Policy"]')?.content||'',
                links:[...document.querySelectorAll('a')].map(x=>x.href),
                addresses:[...document.querySelectorAll('.wallets code')].map(x=>x.textContent),
                titles:[...document.querySelectorAll('.wallets li strong')].map(x=>x.textContent),
                selectable:[...document.querySelectorAll('.wallets code')].every(x=>getComputedStyle(x).userSelect==='all' && x.tabIndex===0),
                cryptoFirst:document.querySelector('section.panel h2')?.textContent==='Direct crypto support',
                walletCount:document.querySelectorAll('.wallets li').length,
                remoteAssets:performance.getEntriesByType('resource').filter(
                    x=>!x.name.startsWith(location.origin+'/')).length
            };
        """)
        verify(page["url"] == URL and page["origin"] == "https://esheenj.github.io",
               "SUPPORT_HTTPS_EXACT_ORIGIN")
        verify(page["main"] == 1 and page["cards"] == 3 and page["scripts"] == 0
               and page["forms"] == 0 and page["remoteAssets"] == 0
               and "default-src 'none'" in page["csp"]
               and "connect-src 'none'" in page["csp"]
               and "script-src 'none'" in page["csp"], "SUPPORT_NO_DATA_OR_PAYMENT_SCRIPT")

        states = [approved["github_sponsors"]["state"], approved["fiat"]["state"],
                  approved["crypto"]["state"]]
        verify(page["pending"] == states.count("pending"), "SUPPORT_STATES_MATCH_REVIEWED_CONFIG")
        want_links = []
        if states[0] == "active":
            want_links.append(approved["github_sponsors"]["url"])
        if states[1] == "active":
            want_links.append(approved["fiat"]["url"])
        hosts = ("github.com/sponsors/", "pay.yoco.com/", "paystack.com/pay/")
        got_links = [x for x in page["links"] if any(host in x for host in hosts)]
        verify(sorted(got_links) == sorted(want_links), "SUPPORT_PAYMENT_URL_MISMATCH_OR_SUBSTITUTION")
        wallets = approved["crypto"]["wallets"] if states[2] == "active" else []
        verify(page["walletCount"] == len(wallets) and
               sorted(page["addresses"]) == sorted(x["address"] for x in wallets),
               "SUPPORT_WALLET_ADDRESS_MISMATCH_OR_SUBSTITUTION")
        verify(page["cryptoFirst"] and
               (not wallets or (page["selectable"] and
                page["titles"] == [x["asset"]+" · "+NETWORK_LABEL[x["network"]]
                                   for x in wallets])),
               "SUPPORT_DONATION_USABILITY_OR_CHAIN_LABEL_MISMATCH")
        for width, height in ((320, 720), (1440, 900)):
            driver.viewport(width, height)
            verify(driver.js("return document.documentElement.scrollWidth<=innerWidth;") is True,
                   "SUPPORT_LAYOUT_" + str(width))
        return {
            "schema": "esheen-support-live-acceptance.v1",
            "state": "PASS",
            "source_manifest_states": states,
            "https_page": URL,
            "payment_destinations_checked": len(want_links),
            "wallet_destinations_checked": len(wallets),
            "browser": "Google Chrome", "browser_version": chrome,
            "responsive_widths": [320, 1440],
            "scope": "Exact public HTML versus reviewed GitHub manifest; cannot prove provider payout, wallet ownership or financial settlement.",
        }
    finally:
        driver.close()


if __name__ == "__main__":
    try:
        print(json.dumps(run(), sort_keys=True))
    except (AssertionError, OSError, RuntimeError, TimeoutError, ValueError) as exc:
        print(json.dumps({
            "schema": "esheen-support-live-acceptance.v1",
            "state": "FAILED", "error": str(exc)[:140]
        }, sort_keys=True))
        raise SystemExit(1)
