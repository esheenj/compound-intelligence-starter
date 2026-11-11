# Esheen Labs — tested payment options and activation guide

**Status as of 11 November 2026: No active payment destination.** The support route is generated entirely from a default-deny public config. The seven independent public repositories and 21 runnable add-ons (28 public tools) remain free. A support information page is not another MVP.

## Shortlist, South Africa

Provider fees below are published standard rates, NOT personalized quotes, and may change. Source links are original provider documentation.

| Channel | Published price | Practical use |
| --- | --- | --- |
| [GitHub Sponsors](https://docs.github.com/en/sponsors/receiving-sponsorships-through-github-sponsors/setting-up-github-sponsors-for-your-personal-account) | South Africa supported; 0% GitHub fee for personal sponsors; up to 6% for organizations | One-time and recurring support from open-source users after owner identity, tax and payout approval |
| [Yoco hosted Payment Page](https://support.yoco.help/en/articles/109565-setting-up-an-online-payment-page) | R0 monthly; [2.55–2.95% online](https://www.yoco.com/za/online-payment/) ex VAT | Pay-what-you-want or invoiced card donations and services |
| [Paystack Payment Pages](https://support.paystack.com/en/articles/2132546) | R0 monthly; [2.9% + R1 local cards or 2% supported EFT](https://paystack.com/za/pricing) ex VAT | One-off, variable contribution or subscription pages |
| [Payfast requests](https://payfast.io/features/payment-request/) | [3.2% + R2 cards, 2% Instant EFT minimum R2](https://payfast.io/fees/), ex VAT; no subscription on standard aggregation | SA payment choice, often request by email |
| [Ozow](https://ozow.com/pricing) | 1.5% or R1 minimum pay-by-bank; no monthly standard fee listed | Low-fee bank payments and compatible partner crypto checkout |
| [MoneyBadger](https://www.moneybadger.co.za/pricing) | No extra MoneyBadger processor charge above participating payment-provider fee | Bitcoin/crypto customers with merchant paid in rand |
| [BTCPay Server](https://btcpayserver.org/) | Free MIT code; hosting, storage, network and chain fees remain | Later non-custodial BTC invoices and automated on-chain settlement |
| Direct wallet transfer | No web processor fee; blockchain network fees, custody and exchange costs may apply | Low-complexity crypto support with manually verified public addresses |

First launch stack: GitHub Sponsors plus either Yoco or Paystack hosted payment page plus one or two owner-controlled wallet destinations. Maintain **R0 additional recurring infrastructure expenditure**. Do not run BTCPay alongside sensitive SIGMA/Oracle trading processes just to claim free hosting.

## Public GitHub payment infrastructure worth knowing

These are **real open-source repositories**, not Esheen Labs-installed processors or proof of merchant onboarding:

- [btcpayserver/btcpayserver](https://github.com/btcpayserver/btcpayserver): upstream non-custodial Bitcoin invoice server (MIT; full production deployment requires node/storage/security and maintenance).
- [btcpayserver/btcpayserver-docker](https://github.com/btcpayserver/btcpayserver-docker): official deployment scaffolding, not a zero-resource service.
- [lnbits/lnbits](https://github.com/lnbits/lnbits): Bitcoin Lightning wallet/account application; hosting and underlying funding custody still matter.
- [Payfast/payfast-php-sdk](https://github.com/Payfast/payfast-php-sdk): Payfast's public PHP integration library for future commercial backends; **do not run payment completion from a browser redirect alone**.
- [PaystackHQ/paystack-android](https://github.com/PaystackHQ/paystack-android) and [PaystackHQ/paystack-ios](https://github.com/PaystackHQ/paystack-ios): public client SDKs for mobile usage; for this static website the **provider-hosted Payment Page needs no SDK**.

No external gateway code is vendored into the Labs repo. Before adopting a gateway dependency: verify maintainer, releases, license, supported payment flow, failure/replay handling, and a working merchant payout account. A free license does not mean free settlement or secure production deployment.

## Existing implementation

- Public config: support/channels.json, schema esheen-labs.support.v1. All channels default to pending.
- Generator: scripts/render_support.py produces a no-JavaScript, no-network public support page only from strictly validated values.
- Strict active GitHub Sponsor URL: https://github.com/sponsors/esheenj. Enroll only when the profile really exists and is approved.
- Supported fiat links: exact provider HTTPS pages at pay.yoco.com/{page} or paystack.com/pay/{page}, rejecting fake hosts, password/userinfo, arbitrary query parameters and unknown redirects.
- Allowed crypto address/network *formats* are Bitcoin mainnet BTC, Ethereum mainnet ETH/USDC/USDT, Base mainnet ETH/USDC, Solana mainnet SOL and Tron mainnet USDT. Syntax checks do NOT establish ownership, token contract, network reachability or on-chain address validity.
- Active channels require an explicit owner-confirmed flag. The flag is a human review assertion, not cryptographic proof. Verify separately before approving the source diff.
- No direct wallet, checkout URL, QR, API key or seed phrase has been added. No dynamic wallet connections, no payment confirmation service, no automatic unlocking.
- Source, tests, Pages staging and browser checks separately validate that all pending channels show no links or wallet addresses.

## Activation: GitHub Sponsors

Visit the official GitHub setup linked above, enable 2FA, complete bank/tax onboarding and await an approved LIVE maintainer profile. Verify the public account really receives funds. Then update the Sponsors config to active with the canonical URL and an owner-verified flag. Only **after** actual enrollment, add GitHub FUNDING.yml to public repos with the verified recipient. Public repo source and README are not proof of recipient account activation.

## Activation: South African fiat

Create a permanent hosted payment page, not a one-off expiring invoice. Yoco supports custom payment pages; Paystack supports one-time variable-amount and recurring payment pages. Use the merchant's actual verified KYC legal recipient and settlement account.

Inspect the provider-generated live HTTPS URL, verify the payee and fees, and record an independently settled small test payment in the provider dashboard. Only then activate the matching pay-page URL in the reviewed public manifest. Do NOT post merchant API keys or webhook secrets. Customers enter card details only on the provider's hosted checkout, never on this static site.

Commercial SaaS product payments are different: production entitlement requires a separate authenticated server-side payment notification, signature checks, durable idempotency, reconciled settlement, refund handling and invoicing. Do NOT unlock a product based on a redirect URL, screenshot or user-supplied transaction hash.

## Activation: direct crypto

Use an owner-controlled, Labs-only receive wallet, isolated from SIGMA financial execution and operational keys. Pick an EXACT asset and network pair (not the ticker alone): e.g. BTC / bitcoin-mainnet, ETH / ethereum-mainnet or USDC / base-mainnet. Verify that the receiving wallet supports that chain and the token contract and whether the account requires a memo/tag. The current prototype does not support memo-required flows.

Verify the address directly in the recipient wallet, consider a low-value transfer, then paste **only the public receiving address** and matching asset and network into the config. Keep each address explicit. Verify the deployed public page characters against the receiving wallet before public announcement; clipboard hijacking and wrong networks can cause irreversible losses. Public blockchain addresses can be linked to the Labs brand and reveal payments. Do not put wallet seed phrases, keystores, passwords, private keys, exchange account credentials, trading endpoints or wallet API keys into code or ChatGPT.

A static wallet page does not prove a transaction occurred, identify a sender, grant access, or reconcile refunds. Log confirmed receipts, asset/network, date, transaction ID, amounts and ZAR valuation **privately**. Dynamic QR codes and more networks can be added only after safely testing the specific wallet URI and chain handling.

## Tax, licence and trust boundaries

[SARS crypto-assets guidance](https://www.sars.gov.za/individuals/crypto-assets-tax/) explains that crypto may generate revenue or capital tax consequences, and exchange for goods/services may be barter. Treat transactions as auditable and seek appropriate tax advice.

Do not issue a Section 18A charitable tax receipt; this requires real [SARS Section 18A approval](https://www.sars.gov.za/businesses-and-employers/tax-exempt-institutions/application-for-section-18a/), not evidenced for Esheen Labs. When using a crypto processor or rand settlement intermediary, check its actual [FSCA CASP licensing](https://www.fsca.co.za/New-Financial-Service-Provider/) and relevant compliance. This guide does not establish an exemption.

Open-source contributions remain voluntary and do not purchase code-review privileges, production keys, private content, execution authority or preferential security fixes.

## Exact state separation

- Source prepared: only after reviewed PR merges.
- Publisher success: only after actual GitHub Pages workflow passes on merged source.
- Live wallet/Sponsors/fiat recipient: **NOT VERIFIED OR ACTIVATED**.
- Money received: **NONE VERIFIED**.
- Product billing/entitlements: **NOT IMPLEMENTED**.

Owner inputs that unlock real support: actual approved Sponsors status, one verified Yoco/Paystack public payment-page URL, and up to two PUBLIC wallet receiving addresses with explicit asset and network. Never provide private payment secrets or card credentials.
