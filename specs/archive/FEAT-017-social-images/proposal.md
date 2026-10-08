---
id: "FEAT-017-social-images"
type: spec
status: archived # draft | implementing | verifying | archived
review: waived
review_waived_reason: "Owner waived the launcher review on 2026-10-08: the repo has no harness/reviewer-pool.json, so dotf spec review cannot run. The owner chose an independent reviewer subagent instead; its verdict is in verification.md (Independent review, 2026-10-08)."
created: "2026-10-06"
issue: "mlorentedev/leaving-denver#209"   # repo#NNN — GitHub issue / Project item that tracks this spec
tags: [spec, proposal]
template_version: "1.0"
---

# FEAT-017-social-images


## Why

<!-- from issue #209: FEAT-017: Social images: a collage post and a QR story at /social/ -->

The owner wants to post the sale on Instagram and other social networks from the phone. A feed post on Instagram carries no clickable link, so the image itself has to print the address, and a story needs a QR code plus the link sticker. An image made by hand would show sold items within days and would carry no attribution, so the dashboard could not tell social visits from direct ones (ADR-005).

## What

The build emits one more hidden directory, `/social/`, from the sanitized data only, like the flyer (FEAT-010):

- **`/social/post.jpg`, 1080×1350 (4:5 feed).** A collage of what is still for sale, with the copy and the address printed below it. Selection rule: the car's cover first while it is unsold, then the cover of the highest-priced item of each household category, then the next highest-priced items, up to 5 photos. Each cell crops its photo to fill. No QR code: nobody scans their own screen.
- **`/social/story.png`, 1080×1920 (9:16 story).** "I'm moving abroad.", a QR code for `https://leaving-denver.pages.dev/?utm_source=instagram&utm_medium=social&utm_campaign=moving-sale`, the address as text under it and one Spanish line. The top 250 px and bottom 340 px are left empty for Instagram's header and reply bar, and room is left for the link sticker.
- **`/social/index.html`.** Both images as `<img>` (long-press, Save image, on a phone), the caption in English with one Spanish line, ready to copy, and one link per network: Instagram, Facebook and WhatsApp (`utm_source=<network>&utm_medium=social&utm_campaign=moving-sale`). No script.
- The copy comes from `locales/social.yaml` and the data: the categories of unsold items and the car while unsold, as on the flyer. No price, phone, email, date or invented urgency.
- `noindex`; not linked from the catalog. With `seller.sale_over: true` it is not built, the existing sweep removes a stale copy, and `/social` and `/social/*` redirect to `/` like the flyer.
- `functions/api/hit.js` accepts `instagram` and `whatsapp` as sources, so these visits do not read as `other`.

The text is set in the site's own font (Plus Jakarta Sans, the woff2 already in `node_modules` and on the page); Pillow, already a dependency, draws the images. No new dependency.

## Out of scope

- Posting to any network, and a per-item image. IG posts are not per-item listings, so `make post` and the seller tool are untouched.
- A Spanish image. One English image with one Spanish line, like the flyer.
- Prices on the images: repricing would make them wrong.

## Risks / open questions

- **A PNG cannot be grepped.** The copy is a pure function tested like the flyer's (no `$`, phone, date or urgency words); the images are tested on shape: exact sizes, the story's safe bands left empty, and the QR checked by sampling module centres against `segno`'s matrix (FEAT-010's approach, no decoder).
- **Font.** The build already requires `npm ci` (the stylesheet fails without it). Loading the font fails loudly; there is no fallback to Pillow's default bitmap font.
- **Leak scan.** `tests/test_private_isolation.py` only reads text suffixes, so two binary files cannot trip it (#195).
- **Crops.** The catalog shows whole photos; a collage cell crops. A small price for a full grid, and the full photos are one tap away.

## Acceptance criteria

- [x] AC1: a build writes `social/post.jpg` (1080×1350), `social/story.png` (1080×1920) and `social/index.html`; the page holds both `<img>`, the caption and the three UTM links, `noindex`, no `<script>`, and no host but the site's own.
- [x] AC2: the story's QR modules equal `segno`'s matrix for exactly the Instagram URL, and the story's top 250 px and bottom 340 px are one flat colour.
- [x] AC3: the collage follows the selection rule on a synthetic inventory (car first while unsold, then one per category by price, then by price; a sold item never appears), and draws as many cells as it has photos, from one to five.
- [x] AC4: with `SELLER_PHONE` set to a sentinel, neither the page nor the copy holds the phone, `sms:`, `tel:`, an email address or a `$`; the copy names the categories and the car from the data and carries no date and no urgency words.
- [x] AC5: with `seller.sale_over: true`, no `social/` is built, a stale one is swept, and `_redirects` sends `/social` and `/social/*` to `/` with a 302.
- [x] AC6: `hit.js` reads `instagram` and `whatsapp` as themselves, and the drift test covers every source the social page links with.
- [x] AC7: the catalog does not link to `/social/`, and every class the page uses is in the compiled stylesheet.

<!-- archived 2026-10-07 — PR: https://github.com/mlorentedev/leaving-denver/pull/239 -->
