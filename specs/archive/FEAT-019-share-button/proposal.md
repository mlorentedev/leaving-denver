---
id: "FEAT-019-share-button"
type: spec
status: archived # draft | implementing | verifying | archived
review: waived
review_waived_reason: "Owner waived the launcher review on 2026-10-08: the repo has no harness/reviewer-pool.json, so dotf spec review cannot run. The owner chose an independent reviewer subagent instead; its verdict is in verification.md (Independent review, 2026-10-08)."
created: "2026-10-06"
issue: "mlorentedev/leaving-denver#214"   # repo#NNN — GitHub issue / Project item that tracks this spec
tags: [spec, proposal]
template_version: "1.0"
---

# FEAT-019-share-button

## Why

Cloudflare Web Analytics, seven days to 2026-10-06: 117 of 121 visits are direct. The catalog removes the utm parameters from the address bar once it has counted a visit (ADR-011), and the item sheet's Share button (FEAT-002) shares a bare link, so a link a buyer forwards reads as direct. Word of mouth looks like the main channel so far, and nothing tells it apart.

## What

- Every link the catalog shares carries `?utm_source=share&utm_medium=referral&utm_campaign=moving-sale`: the item sheet's Share (the item's share page, `/i/<id>/`, which already forwards its query string to the catalog) and a new Share button under the hero.
- The hero button shares the page's own address (`og:url`: `/` or `/es/`), with the same behaviour as the item one: the Web Share sheet where the browser has one, else copy to the clipboard ("Link copied"), else the link shown and selected. A cancelled share sheet does nothing.
- `functions/api/hit.js` accepts `share` as a source, so these visits do not read as `other`.

No new event and no new data: the visit the shared link brings is the existing `visit` event with `source: share`. The utm parameters still leave the address bar after the visit is counted.

## Out of scope

- Counting share taps themselves (a new event, and a change to the n8n digest).
- A per-network share (WhatsApp or Facebook buttons): the phone's share sheet already lists them.

## Risks / open questions

- A shared link forwarded a second time still carries `utm_source=share` in the message, so a chain of forwards counts as `share`: that is word of mouth, which is what is being measured.
- Previews: crawlers fetch `/i/<id>/?utm_source=…`; Pages serves the same file, and `og:url` stays canonical.

## Acceptance criteria

1. The item sheet's Share shares or copies `<og:url>i/<id>/?utm_source=share&utm_medium=referral&utm_campaign=moving-sale`, on `/` and `/es/`.
2. The hero's Share shares or copies `<og:url>?utm_source=share&utm_medium=referral&utm_campaign=moving-sale`, with the same fallbacks (failed share copies, refused clipboard shows the link selected, cancel does nothing), in English and Spanish.
3. `hit.js` counts a visit with `source: share` as `share`; the drift test reads the catalog's shared source too.
4. No new event type; the full suite is green.

<!-- archived 2026-10-07 — PR: https://github.com/mlorentedev/leaving-denver/pull/239 -->
