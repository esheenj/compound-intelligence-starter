"""Post-publish, read-only HTTPS evidence for the Sigma Code integration offer.

No email is sent; no customer data, credentials or private tools accessed.
The page's deployed bytes MUST match the source reviewed by GitHub CI.
"""
from __future__ import annotations
import hashlib
import json
import socket
import sys
import time
import urllib.request
from pathlib import Path
from browser_check_issue_report import Driver, driver_executable

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.stage_showcase import INTEGRATION_OFFER_SOURCE,verify_integration_offer

URL="https://esheenj.github.io/compound-intelligence-starter/integration-reliability.html"

def verify(ok,name):
    if ok is not True:
        raise AssertionError(name)

def run():
    source=INTEGRATION_OFFER_SOURCE.read_bytes()
    source_check=verify_integration_offer(source)
    sha=source_check["htmlSha256"]
    for _ in range(32):
        req=urllib.request.Request(URL,headers={"User-Agent":"Esheen-Labs-ReadOnly-Release-Acceptance"})
        try:
            with urllib.request.urlopen(req,timeout=15) as response:
                verify(response.status==200,"INTEGRATION_OFFER_HTTPS_200")
                deployed=response.read(65536)
        except (TimeoutError,OSError):
            time.sleep(.4)
            continue
        if hashlib.sha256(deployed).hexdigest()==sha:
            break
        time.sleep(.7)
    else:
        raise AssertionError("INTEGRATION_OFFER_DEPLOYED_BYTES_NOT_MATCH_SOURCE")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1",0))
        port=sock.getsockname()[1]
    driver=Driver(driver_executable(),port)
    try:
        version=driver.start()
        driver.command("POST","url",{"url":URL})
        for _ in range(40):
            if driver.js("return !!document.querySelector('#tools article.tool') && document.querySelector('#pilot')!==null;") is True:
                break
            time.sleep(.2)
        else:
            raise AssertionError("INTEGRATION_OFFER_BROWSER_NOT_READY")
        result=driver.js("""
            return {
                href:location.href,origin:location.origin,
                title:document.title,
                h1:document.querySelectorAll('h1').length,
                main:document.querySelectorAll('main').length,
                steps:document.querySelectorAll('#tools article.tool').length,
                advanced:document.querySelectorAll('#engineering .technical a').length,
                mail:[...document.querySelectorAll('a[href^="mailto:"]')].map(x=>x.getAttribute('href')),
                exampleLinks:[...document.querySelectorAll('#tools article.tool .actions a:first-child')].map(x=>x.href),
                githubIssue:[...document.querySelectorAll('a')].some(x=>x.href.includes('issues/new?template=pilot.yml')),
                csp:document.querySelector('meta[http-equiv="Content-Security-Policy"]')?.content,
                scripts:document.querySelectorAll('script').length,
                forms:document.querySelectorAll('form').length,
                assets:performance.getEntriesByType('resource').filter(x=>x.name.startsWith('http')).length,
                caution:document.body.textContent.includes('An enquiry is not a booking')
            };
        """)
        verify(result["href"]==URL and result["origin"]=="https://esheenj.github.io",
               "INTEGRATION_OFFER_EXACT_HTTPS")
        verify(result["h1"]==1 and result["main"]==1 and result["steps"]==4 and result["advanced"]==2
               and result["scripts"]==0 and result["forms"]==0 and result["assets"]==0
               and result["githubIssue"] and result["caution"] and
               "connect-src 'none'" in result["csp"] and "script-src 'none'" in result["csp"],
               "INTEGRATION_OFFER_SAFE_CUSTOMER_DISCOVERY")
        verify(len(result["mail"])==1 and
               result["mail"][0].startswith("mailto:info@sigmacode.co.za?subject=Integration%20reliability"),
               "INTEGRATION_OFFER_ENQUIRY_DESTINATION")
        verify(len(result["exampleLinks"])==4 and
               all(x.startswith("https://esheenj.github.io/") for x in result["exampleLinks"]),
               "INTEGRATION_OFFER_FOUR_REAL_DEMOS")
        for width,height in ((320,720),(375,812),(1440,900)):
            driver.viewport(width,height)
            verify(driver.js("return document.documentElement.scrollWidth<=innerWidth+1;") is True,
                   "INTEGRATION_OFFER_NO_OVERFLOW_"+str(width))
        return {
            "schema":"esheen-integration-offer-live-acceptance-v1","state":"PASS",
            "sourceSha256":sha,"httpsUrl":URL,"liveBytesMatchReviewedSource":True,
            "linkedFreeTools":4,"developerLabs":2,"browser":"Google Chrome","browserVersion":version,
            "responsiveWidths":[320,375,1440],
            "leadDeliveryVerified":False,
            "paidPilotVerified":False,
            "scope":"Exact published source and link targets; email not sent, customer adoption not measured."
        }
    finally:
        driver.close()

if __name__=="__main__":
    try:print(json.dumps(run(),sort_keys=True))
    except (AssertionError,OSError,ValueError,TimeoutError,RuntimeError) as exc:
        print(json.dumps({"schema":"esheen-integration-offer-live-acceptance-v1",
                          "state":"FAIL","error":str(exc)[:170]},sort_keys=True))
        raise SystemExit(1)
