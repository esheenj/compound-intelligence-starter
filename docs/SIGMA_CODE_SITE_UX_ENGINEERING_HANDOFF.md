# Sigma Code corporate website — UX Engineering feature handoff

**Status:** SOURCE-ONLY HANDOFF — **NOT** published on `sigmacode.co.za`  
**Prepared:** 15 November 2026 (SAST)  
**Source repository:** `esheenj/compound-intelligence-starter`  
**Destination:** the independently managed Sigma Code corporate website at `https://sigmacode.co.za/`

This is a publishing brief, not a request to create a replacement website. The corporate site has been managed separately from GitHub Pages; **its editable source, authorized editor session and deployment workflow are not verified here**. This repository cannot deploy to that domain. Preserve the live Sigma Code logo, main navigation, existing SEO verification, analytics/privacy settings and all unrelated sections. Do not publish or add scripts solely because this file exists.

## Customer-facing feature: copy

**Section eyebrow:** UX ENGINEERING / SIGMA CODE  
**Heading:** Better journeys. More dependable interfaces.  
**Intro:** Complex forms, confusing dashboards and fragile workflows create friction for customers and staff. Explore how Sigma Code approaches clear interactions, recoverable journeys and maintainable product interfaces through original, freely available engineering examples.

**Featured evidence:** A fictional repair-service request, SERVICE-104, demonstrates four design decisions: guided intake, guarded workflow transitions, staff triage and consistent interfaces. It is a transparent walkthrough of engineering *patterns*, **not a completed customer implementation, integrated CRM or measured conversion result**.

**Primary action:** Explore the UX case study  
**Primary URL:** https://esheenj.github.io/compound-intelligence-starter/#ux-case-study

**Secondary action:** Browse UX engineering tools  
**Secondary URL:** https://esheenj.github.io/compound-intelligence-starter/#ux-engineering

**Commercial action:** Discuss a UX engineering review  
**Commercial route:** `mailto:info@sigmacode.co.za?subject=UX%20Engineering%20Enquiry`  
**Commercial reassurance:** Potential work includes an experience review, bounded prototype, or implementation handoff. Scope and pricing are determined after a conversation; public examples are free and independently hosted.

**Optional caption:** Demonstrations use fictional data. Individual projects are independent; they do not currently share a live backend. No completed client outcomes or certified accessibility results are implied.

## Five supporting public examples

| Demonstration | What visitors can actually inspect | Source-backed destination |
| --- | --- | --- |
| Form Experience Patterns | A fictional multi-step form with errors, draft export and recovery | https://esheenj.github.io/form-experience-kit-oss/ |
| UI Workflow State Machine | Deterministic guarded transitions and a synthetic event history | https://esheenj.github.io/flow-state-machine-oss/ |
| Data Table Interaction Toolkit | Sample-row filtering, stable sorting, pagination and CSV export | https://esheenj.github.io/data-table-interactions-oss/ |
| Design System Foundations | Offline design-token resolution and numeric contrast demonstration | https://esheenj.github.io/design-system-foundations-oss/ |
| Mobile Journey Patterns | Responsive guided interaction, input feedback and focus recovery | https://esheenj.github.io/mobile-first-flow-kit-oss/ |

## Placement and visual direction

- Position this feature **after core services and before lower-priority portfolio cards** so customers understand the value before opening code examples.
- Reuse the corporate site's actual maintained Sigma Code logo and design tokens. Do not redraw the master emblem. Follow the existing dark matte green/near-black background, restrained bright-green highlights, fine strokes and editorial hierarchy.
- Use **one hero statement, one case-study preview, two evidence links, and one clear enquiry action**. Avoid double selling statements, repeating the same tagline in header/footer or making three equally prominent CTAs.
- Use an actual anchor element for the case-study destination and a user-initiated `mailto:` for enquiry. No invented contact form, server API, chat bot, account registration, tracking pixel, GTM modification, ad-consent component or third-party embed.
- Keep the design responsive, keyboard accessible and respectful of reduced-motion preferences. Ensure that links remain visibly distinguishable without colour alone.
- The direct case-study link is an existing public GitHub Pages destination; it must not be rewritten to a nonexistent `/products/chimovra` route. Chimovra remains a **provisional name under clearance review** and does not belong in live corporate navigation yet.

## Content handoff (platform neutral)

The website editor can add this as an ordinary **feature section** without changing the rest of the homepage:

> **UX ENGINEERING**  
> **Better journeys. More dependable interfaces.**  
> From guided forms to recoverable workflows, we help teams make complex digital experiences easier to use and maintain. Explore our public engineering examples through a fictional service-request case study, then talk to Sigma Code about your own product.  
>
> [Explore the UX case study](https://esheenj.github.io/compound-intelligence-starter/#ux-case-study) · [Browse the tools](https://esheenj.github.io/compound-intelligence-starter/#ux-engineering)  
> **Discuss a UX engineering review:** info@sigmacode.co.za  
> *Examples are independent and fictional. Scope and pricing are agreed separately.*

If the native website editor supports components, prefer its **existing card, button and typography components**, not unreviewed imported HTML/CSS.

## Conversion and privacy measurement

**Immediate R0 option:** Track enquiries manually in the existing private commercial pipeline: source **"Sigma Code UX Engineering"**, enquiry received date, requested outcome, qualified/unqualified, quoted/declined and closed status. Do not log private customer data in public repositories.

**Optional after existing analytics access is verified:** observe aggregate feature visits or outbound CTA engagement using **only consented/currently authorized first-party analytics**. The existing marketing/analytics configurations are not verified from this repository; do not silently add new scripts, third-party pixels, new cookies, advertising-preference UI, or claims of tracking implementation. Outbound clicks or page views alone are **not** paid conversions.

**First actual business metric:** qualified enquiries attributable to this feature divided by the relevant site visitors, *only once both counts can be legitimately measured*. Report unknown when the denominator is absent. Do not invent conversion rates or ROI.

## Acceptance checklist for the website editor

1. Confirm **authoritative current site source** (ChatGPT Sites editor or owned deployment repository), authorized publishing identity and target domain. Verify latest deployed state; do not overwrite a newer site revision.
2. Use the existing logo, typography, palette and navigation rather than replacing site-wide branding.
3. Check the exact two public URLs above load and show the referenced sections; avoid linking to a non-existent corporate /UX route.
4. At 320, 360, 768 and 1440 px, inspect clipping, button hierarchy and readable copy. At keyboard-only, verify focus order, link labels and external navigation.
5. Confirm SEO: no duplicate H1, page title/canonical preserved, descriptive anchor text and reasonable page loading behaviour. If an actual dedicated page is created, use a site-owned canonical and new page-level metadata.
6. Confirm privacy: no new trackers, forms, personal data submission or cookie preference changes without a separate approved process.
7. Preview the exact change, inspect the diff, publish once through the site's actual deployment workflow, and independently verify the live `sigmacode.co.za` page.
8. Record separately **source ID / tests / publication ID / live check / enquiry measurement**. If direct site authority is still unavailable, status remains **READY_FOR_SITE_EDITOR_NOT_DEPLOYED**.

## Evidence and boundaries

- Original UX worked example: https://github.com/esheenj/compound-intelligence-starter/blob/main/docs/UX_ENGINEERING_WORKED_CASE_STUDY.md
- Live case study: https://esheenj.github.io/compound-intelligence-starter/#ux-case-study
- Published UX collection: https://esheenj.github.io/compound-intelligence-starter/#ux-engineering
- Commercial brand: Sigma Code, not Sigma Quant Finance.
- No private client work, private trading source, confidential governance instructions, production credentials, or payment flows are used by this feature.
- **Additional recurring infrastructure spend:** R0.
