"""Render no-script Esheen Labs support page from reviewed, default-deny destinations.

No payment is processed here. Payment links require manual recipient
verification in a reviewed public PR; typed flags cannot prove ownership.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

SCHEMA = "esheen-labs.support.v1"
IDENT = re.compile(r"[A-Za-z0-9_-]{3,64}\Z")
EVM = re.compile(r"0x[0-9a-fA-F]{40}\Z")
BASE58 = re.compile(r"[1-9A-HJ-NP-Za-km-z]+\Z")
BTC = re.compile(r"(?:bc1[ac-hj-np-z02-9]{11,71}|[13][1-9A-HJ-NP-Za-km-z]{25,34})\Z")
PAIRS = {
    ("BTC", "bitcoin-mainnet"),
    ("ETH", "ethereum-mainnet"),
    ("USDC", "ethereum-mainnet"),
    ("USDT", "ethereum-mainnet"),
    ("USDC", "base-mainnet"),
    ("ETH", "base-mainnet"),
    ("SOL", "solana-mainnet"),
    ("USDT", "solana-mainnet"),
    ("USDT", "tron-mainnet"),
}


PIONEX_MINIMUM_SNAPSHOT = {
    ("BTC", "bitcoin-mainnet"): "0.00001 BTC",
    ("USDT", "solana-mainnet"): "0.1 USDT",
    ("USDT", "ethereum-mainnet"): "1 USDT",
    ("USDT", "tron-mainnet"): "1 USDT",
}


def fail(label: str):
    raise ValueError("SUPPORT_" + label)


def fields(value: object, keys: set[str], label: str):
    if type(value) is not dict or set(value) != keys:
        fail("FIELDS_" + label)


def _url_allowed(raw: object, provider: str) -> bool:
    if type(raw) is not str or len(raw) > 190 or any(ord(c) < 33 or ord(c) > 126 for c in raw):
        return False
    try:
        u = urlsplit(raw)
        if u.scheme != "https" or u.username or u.password or u.port or u.query or u.fragment:
            return False
        if provider == "github":
            return u.netloc == "github.com" and u.path == "/sponsors/esheenj"
        if provider == "paystack":
            return u.netloc == "paystack.com" and re.fullmatch(r"/pay/[A-Za-z0-9_-]{3,70}", u.path) is not None
        if provider == "yoco":
            return u.netloc == "pay.yoco.com" and re.fullmatch(r"/[A-Za-z0-9_-]{3,70}", u.path) is not None
    except ValueError:
        return False
    return False


def _wallet_format(asset: object, network: object, address: object) -> bool:
    if type(asset) is not str or type(network) is not str or type(address) is not str:
        return False
    if (asset, network) not in PAIRS or len(address) > 100:
        return False
    if network == "bitcoin-mainnet":
        return BTC.fullmatch(address) is not None
    if network in ("ethereum-mainnet", "base-mainnet"):
        return EVM.fullmatch(address) is not None and address[2:] != "0" * 40
    if network == "solana-mainnet":
        return 32 <= len(address) <= 44 and BASE58.fullmatch(address) is not None
    if network == "tron-mainnet":
        return len(address) == 34 and address.startswith("T") and BASE58.fullmatch(address) is not None
    return False


def validate_channels(value: object) -> dict:
    fields(value, {"schema", "github_sponsors", "fiat", "crypto"}, "ROOT")
    if value["schema"] != SCHEMA:
        fail("SCHEMA")
    sponsor = value["github_sponsors"]
    fiat = value["fiat"]
    crypto = value["crypto"]

    if type(sponsor) is not dict or sponsor.get("state") not in ("pending", "active"):
        fail("SPONSOR_STATE")
    if sponsor["state"] == "pending":
        fields(sponsor, {"state", "url"}, "SPONSOR_PENDING")
        if sponsor["url"] != "":
            fail("SPONSOR_PENDING_URL")
    else:
        fields(sponsor, {"state", "url", "verified_by_owner"}, "SPONSOR_ACTIVE")
        if sponsor["verified_by_owner"] is not True or not _url_allowed(sponsor["url"], "github"):
            fail("SPONSOR_UNVERIFIED")
    if type(fiat) is not dict or fiat.get("state") not in ("pending", "active"):
        fail("FIAT_STATE")
    if fiat["state"] == "pending":
        fields(fiat, {"state", "provider", "url"}, "FIAT_PENDING")
        if fiat["url"] != "" or fiat["provider"] != "none":
            fail("FIAT_PENDING_URL")
    else:
        fields(fiat, {"state", "provider", "url", "verified_by_owner"}, "FIAT_ACTIVE")
        if fiat["verified_by_owner"] is not True or fiat["provider"] not in ("yoco", "paystack"):
            fail("FIAT_UNVERIFIED")
        if not _url_allowed(fiat["url"], fiat["provider"]):
            fail("FIAT_URL")
    if type(crypto) is not dict or crypto.get("state") not in ("pending", "active"):
        fail("CRYPTO_STATE")
    if crypto["state"] == "pending":
        fields(crypto, {"state", "wallets"}, "CRYPTO_PENDING")
        if crypto["wallets"] != []:
            fail("CRYPTO_PENDING_WALLETS")
    else:
        fields(crypto, {"state", "wallets"}, "CRYPTO_ACTIVE")
        wallets = crypto["wallets"]
        if type(wallets) is not list or not (1 <= len(wallets) <= 4):
            fail("CRYPTO_COUNT")
        seen = set()
        for row in wallets:
            base_fields = {"asset", "network", "address", "verified_by_owner"}
            exchange_fields = base_fields | {"destination_type", "minimum_snapshot"}
            if type(row) is not dict or set(row) not in (base_fields, exchange_fields):
                fail("FIELDS_CRYPTO_WALLET")
            if set(row) == exchange_fields:
                if (row["destination_type"] != "pionex-exchange-deposit" or
                        row["minimum_snapshot"] != PIONEX_MINIMUM_SNAPSHOT.get(
                            (row["asset"], row["network"]))):
                    fail("CRYPTO_EXCHANGE_METADATA")
            if row["verified_by_owner"] is not True or not _wallet_format(
                    row["asset"], row["network"], row["address"]):
                fail("CRYPTO_UNVERIFIED_OR_FORMAT")
            key = (row["asset"], row["network"])
            if key in seen:
                fail("CRYPTO_DUPLICATE_NETWORK")
            seen.add(key)
    return value


def load_channels(path: Path) -> dict:
    if path.is_symlink() or path.parent.is_symlink() or not path.is_file() or path.stat().st_size > 16384:
        fail("CONFIG_SOURCE")
    raw = path.read_bytes()
    if len(raw) > 16384:
        fail("CONFIG_OVERSIZE")

    def unique(pairs):
        result = {}
        for key, val in pairs:
            if key in result:
                fail("DUPLICATE_JSON_KEY")
            result[key] = val
        return result

    def invalid_number(_):
        fail("NONFINITE_JSON_NUMBER")

    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique, parse_constant=invalid_number)
    except (ValueError, UnicodeError) as exc:
        fail("INVALID_JSON")
    return validate_channels(value)


def _safe(value: object) -> str:
    return html.escape(str(value), quote=True)


def render_support(value: object) -> bytes:
    value = validate_channels(value)
    sponsor, fiat, crypto = value["github_sponsors"], value["fiat"], value["crypto"]

    def make_card(title: str, body: str, action: str) -> str:
        return f'<section class="panel"><h2>{_safe(title)}</h2><p>{body}</p>{action}</section>'

    if sponsor["state"] == "active":
        s = '<a href="' + _safe(sponsor["url"]) + '" rel="noopener noreferrer">Sponsor through GitHub</a>'
        s_info = "One-time or recurring support through the published maintainer profile."
    else:
        s = '<p class="pending">Not connected yet — no payment is accepted here.</p>'
        s_info = "A maintainer sponsorship profile must first be approved and verified."

    if fiat["state"] == "active":
        f = '<a href="' + _safe(fiat["url"]) + '" rel="noopener noreferrer">Open secure ' + _safe(fiat["provider"].title()) + ' checkout</a>'
        f_info = "Checkout and settlement are performed by the payment provider, not by this site."
    else:
        f = '<p class="pending">Not connected yet — no checkout link is published.</p>'
        f_info = "A South African payment provider must be onboarded and its recipient account verified."

    if crypto["state"] == "active":
        wallets = []
        for row in crypto["wallets"]:
            note = ""
            if row.get("destination_type") == "pionex-exchange-deposit":
                note = ('<small>Pionex custodial exchange deposit · minimum shown in owner screenshot '
                        'on 12 November 2026: ' + _safe(row["minimum_snapshot"]) +
                        '. Minimums and deposit addresses can change. Reconfirm the live Pionex '
                        'deposit screen and same asset/network before sending.</small>')
            wallets.append('<li><strong>' + _safe(row["asset"]) + ' · ' + _safe(row["network"]) +
                           '</strong><code>' + _safe(row["address"]) + '</code>' + note + '</li>')
        c = '<ul class="wallets">' + "".join(wallets) + '</ul>'
        c_info = ("These receiving addresses were supplied by the maintainer. Pionex destinations "
                  "are custodial exchange deposits, not independent self-custody or GitHub Sponsors. "
                  "Before each transfer, verify the current Pionex deposit address, coin, network "
                  "and live minimum: addresses may be replaced and mismatched networks can lose funds. "
                  "Avoid tiny donations below deposit minimums. This static site cannot verify payment "
                  "or grant product access. No automatic product access is granted.")
    else:
        c = '<p class="pending">No public wallet address has been enrolled or published.</p>'
        c_info = "Wallet-network pairing and ownership checks are required before any crypto address appears."

    page = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'none'; connect-src 'none'; img-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'">
<meta name="description" content="Support Esheen Labs open-source AI and UX development through reviewed channels only.">
<title>Support Esheen Labs · Open source</title>
<style>
:root{font:16px/1.5 system-ui,sans-serif;color-scheme:light dark}
*{box-sizing:border-box}body{background:Canvas;color:CanvasText;margin:0}
main{max-width:65rem;margin:auto;padding:clamp(1rem,4vw,3.5rem)}
h1{font-size:clamp(2rem,5vw,3.4rem);line-height:1.1}
a{color:LinkText;overflow-wrap:anywhere}
a:focus-visible{outline:3px solid Highlight;outline-offset:3px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,18rem),1fr));gap:1rem}
.panel{border:1px solid GrayText;border-radius:1rem;padding:1.2rem;min-width:0}
.pending{font-weight:700}code{display:block;overflow-wrap:anywhere;margin:.45rem 0;padding:.5rem;border:1px solid GrayText;border-radius:.4rem}
.wallets{padding-left:1.1rem}.wallets li{margin:1rem 0}.wallets small{display:block;margin-top:.4rem;line-height:1.5}
.note{border-left:4px solid currentColor;padding:.8rem 1rem;margin:1.2rem 0}
</style></head><body><main>
<p><a href="./">Back to Esheen Labs tools</a></p><p>Esheen Labs · public open-source support</p>
<h1>Keep useful tools open and improving.</h1>
<p>All basic public experiments remain free. Financial support is voluntary, never required to try tools, and does not purchase access to private research, verified identity or execution authority.</p>
<div class="grid">""" + make_card("GitHub Sponsors", s_info, s) + make_card("Card and rand payments", f_info, f) + make_card("Direct crypto support", c_info, c) + """</div>
<section class="note"><h2>Before sending funds</h2><p>Use only destinations shown on this public page after the maintainer activates them. Independently confirm the receiver and selected network. Cryptocurrency transfers can be irreversible. No keys or wallet connections are requested. Avoid posting private payment proofs or personal data in public issues.</p>
<p>These deposits may be controlled by Pionex, may be replaced, and may require current exchange-specific minimums. An address shown here does not guarantee successful crediting. Never reuse an address after an exchange replacement notice.</p><p>Support is not an order or a tax-deductible charitable donation. No Section 18A certificate is issued. For commercial work, separately agree scope, pricing, invoicing, delivery and a verified payment channel. Screenshots and transaction IDs are not proof of settled payment.</p></section>
<p><a href="https://github.com/esheenj/compound-intelligence-starter/blob/main/CONTRIBUTING.md" rel="noopener noreferrer">You can also contribute without money</a>.</p>
<p><a href="https://github.com/esheenj/compound-intelligence-starter/blob/main/docs/SUPPORT_AND_SUSTAINABILITY.md" rel="noopener noreferrer">Read the support policy and limitations</a>.</p>
</main></body></html>"""
    if len(page.encode("utf-8")) > 65536 or "<script" in page.lower() or "<form" in page.lower():
        fail("RENDER_SECURITY")
    return page.encode("utf-8")
