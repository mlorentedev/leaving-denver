---
id: "FEAT-010-building-flyer"
type: spec
status: verifying # draft | implementing | verifying | archived
created: "2026-10-01"
issue: "mlorentedev/leaving-denver#30"   # repo#NNN — GitHub issue / Project item that tracks this spec
tags: [spec, proposal]
template_version: "1.0"
---

# FEAT-010-building-flyer

## Why

Issue #30 (OPS-005) asks for a printed flyer with a QR code for the building board and local groups. The seller already depends on one: the playbook's first week says to put a QR flyer on the building board, and ADR-008 and the decommission runbook name the flyer's QR code as one of the links that must keep working after the sale. Today there is nothing to print. A flyer made by hand in a word processor would carry prices that repricing makes wrong, a phone number that ADR-002 keeps out of static markup, and a QR code with no attribution, so the dashboard could not tell paper visits from any other. The page is built from the same data as the catalog, so the departure date and the categories can never drift from the site.

## What

The build emits one more public page, `/flyer/index.html`, made to be printed from a browser:

- One US Letter portrait page. `@page { size: letter; margin: 0.5in }` and a print stylesheet put it on exactly one sheet, and it reads fine on a screen too.
- A QR code, as inline SVG made at build time, for `https://leaving-denver.pages.dev/?utm_source=flyer&utm_medium=print&utm_campaign=moving-sale`, so visits from paper show up as their own channel (ADR-005). The address is printed under the QR as text, without the tracking parameters, so someone without a phone can type it.
- Plain first-person copy from the locale files, English with one short Spanish line: "I'm moving abroad", the real departure date from `seller.departure_date`, the categories from the inventory, the car by its short title, "Pickup in DTC", "Scan to see photos and prices".
- No phone, email, price, unit number or address beyond what the public site shows; no script and no request to another host.
- `noindex` in the page; `robots.txt` already disallows it and the catalog does not link to it. The seller opens `/flyer/` in a browser and prints it; the playbook says so.
- With `seller.sale_over: true` the flyer is not built, a flyer left by an earlier build is swept, and `/flyer` and `/flyer/*` redirect to `/` like the share pages (ADR-008: the paper outlives the sale, and its QR then opens the end page).

New dependency: `segno` (pure Python, no native code, no runtime dependencies), added to `pyproject.toml` and `uv.lock`. It runs at build time only; nothing of it is deployed. A dependency is a contract change, so it is recorded here.

## Out of scope

- The owner's posting steps in #30: group posts, putting the paper up, checking each group's rules.
- A flyer in Spanish, and tear-off tabs. One page, English, with one Spanish line.
- Prices on paper. They change with repricing (the drop schedule is private, lesson-008) and paper cannot follow.
- A link to the flyer from the catalog or the seller tool.
- A QR decoder in the test suite: no pure-Python one is light enough to add (see Risks).

## Risks / open questions

- **No decoder.** AC2 is checked without scanning: the SVG is parsed back into its module matrix and compared with the matrix `segno` makes for the literal expected URL, and the printed address is checked against the origin. A change to the URL, the origin or the encoder settings fails it. A real scan of the printed page is an owner step in the PR.
- **Wording.** "Everything must go" is a phrase lesson-008 lists among the tropes that backfire on peer-to-peer markets. Here it carries the real departure date, which a buyer can check, and nothing else (no "act now", no count of interested people). The test fails on invented urgency words.
- **Body padding.** `public.css` pads `<body>` for the sticky bar with an unlayered rule (lesson-020). On paper that would push the page onto a second sheet, so the flyer resets it, and a headless-Chrome test counts the pages of the real print output.
- **Categories and the car follow the data.** A category whose items are all sold is not listed, and a sold car is not mentioned, so the paper never advertises what is gone. Prices changing never touches the flyer.
- **Conflict surface.** PR #146 edits `build_public_site`; this change adds one call there and puts everything else in new functions and files.

## Acceptance criteria

- [x] **AC1: the page.** A catalog build writes `flyer/index.html` with a print stylesheet whose `@page` is `size: letter` with a 0.5in margin, an inline `<svg>` QR code, no `<script>`, no `<img>` and no reference to any host but the site's own.
- [x] **AC2: the QR.** The SVG's module matrix equals the one `segno` makes for exactly `https://leaving-denver.pages.dev/?utm_source=flyer&utm_medium=print&utm_campaign=moving-sale` (error level M, 4-module quiet zone), and the page prints the host under it.
- [x] **AC3: no contact, no price.** With `SELLER_PHONE` set to a sentinel, the flyer holds the phone in no form, no `sms:` or `tel:`, no email address and no `$`.
- [x] **AC4: copy from the data.** The categories listed are those of the published, unsold items (labels from `locales/en.yaml`), the car appears by its `short_title` and only while it is not sold, and the date is `seller.departure_date` formatted, whatever it is. The copy has no em dash and none of the invented-urgency phrases.
- [x] **AC5: hidden, not linked.** The page carries `noindex`, and neither the catalog nor the share pages link to `/flyer/`.
- [x] **AC6: one Letter page.** Headless Chrome prints `/flyer/` to PDF on exactly one US Letter sheet, and a screenshot at 816x1056 CSS px shows no vertical scroll.
- [x] **AC7: end of sale.** With `seller.sale_over: true` no `flyer/` is built, a flyer left in the output by an earlier build is removed, `_redirects` sends `/flyer` and `/flyer/*` to `/` with a 302, and the end-mode smoke test still passes.
- [x] **AC8: the playbook and the stylesheet.** `docs/runbooks/seller-playbook.md` tells the seller to print `https://leaving-denver.pages.dev/flyer/` from a browser, and every class the flyer template uses is in the compiled stylesheet.

## References

- Issue #30 (OPS-005)
- ADR-002 (phone obfuscation), ADR-004 (crawlers), ADR-005 (UTM attribution), ADR-008 (end of sale, the flyer's QR outlives the sale)
- Lessons 008 (honest urgency), 020 (unlayered CSS outranks utilities)
- `docs/runbooks/seller-playbook.md`, `docs/runbooks/decommission.md`
