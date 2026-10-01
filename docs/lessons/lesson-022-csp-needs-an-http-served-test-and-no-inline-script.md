---
id: "lesson-csp-needs-an-http-served-test-and-no-inline-script"
type: lesson
scope: local
tags: [csp, testing, browser, cloudflare]
created: "2026-10-01"
source: "FEAT-009 PR 2, the CSP for /seller/*"
---

# Lesson: A CSP Test Needs an HTTP Response, and the Page Needs No Inline Script

## Context

`/seller/*` gets `script-src 'self'; connect-src 'none'` (ADR-007), set by the Pages middleware.
The page had inline scripts for its data and its code, and the browser tests load it from
`file://`.

## Problem

`script-src 'self'` blocks every inline script, so the page had to move its code into
`seller.mjs` and its data into `<script type="application/json">` blocks, which a CSP does not
execute. And a `file://` page carries no response header, so the existing browser tests could not
tell a page that would be blocked from one that would run. A first assertion on the policy text
passed whether or not the page obeyed it.

## Solution

`tests/test_seller_csp.py` serves the built page over HTTP with the exact policy the middleware
sets, and checks in headless Chrome that the page unlocks with no `securitypolicyviolation`
event. A page that kept an inline script or style stays dead there. Static guards fail on
inline code, handlers and any network, storage or dynamic-code call in `seller.mjs`. The owner
still checks the header on the served response after an Access login, because nothing in the
repository shows what Cloudflare adds or strips.

## Takeaway

A policy is only tested by a browser that enforces it, serving the policy the code really sets.
Asserting the string of the header shows the configuration, not the effect.
