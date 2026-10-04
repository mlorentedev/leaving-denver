---
id: "lesson-a-redirect-that-rebuilds-the-url-drops-the-query"
type: lesson
scope: local
tags: [analytics, utm, redirects, testing, cloudflare]
created: "2026-10-03"
source: "FEAT-015 / issue #177"
---

# Lesson: A Redirect That Rebuilds the URL Drops the Query

## Context

Every link the seller tool builds is `/i/<id>/?utm_source=<channel>&utm_campaign=moving-sale`. The
share page it points at exists for link previews (ADR-004) and sends the buyer on with
`location.replace("../../#<id>")`. Cloudflare Web Analytics, which ADR-005 relied on for
attribution, does not log query strings at all.

## Problem

Two layers each assumed the other kept the source. The share page built a new URL from a constant
and never looked at `location.search`, so the catalog never saw `utm_source` on any seller-tool link;
only the flyer, which points at `/` directly, would have been attributed. Nothing failed: the page
loaded, the item opened, and a metric that reads "direct" for every channel looks like a quiet week.
ADR-005 only said to check whether the dashboard reports UTMs; nobody had.

## Solution

The share page forwards `location.search` ahead of the hash. The test that proves it follows the
real hop: the built site served over HTTP, a request for `/i/<id>/?utm_source=facebook`, and the
beacon request the stand-in endpoint receives, in both languages. An assertion on the template text
(`location.search` is in it) is kept as well, but it is the weaker one.

## Takeaway

Attribution is a property of the whole path from the link to the page that counts. Test it from the
link as posted, through every redirect, to the event that is recorded, and check the third-party tool's
documentation for what it discards before choosing it to carry the signal.
