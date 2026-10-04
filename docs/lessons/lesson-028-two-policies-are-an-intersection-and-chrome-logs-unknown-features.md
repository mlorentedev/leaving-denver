---
id: "lesson-two-policies-are-an-intersection-and-chrome-logs-unknown-features"
type: lesson
scope: local
tags: [csp, cloudflare, headers, lighthouse, testing]
created: "2026-10-03"
source: "ADR-010, the public pages' security headers"
---

# Lesson: Two Policies Are an Intersection, and Chrome Logs Unknown Permissions-Policy Features

## Context

Adding a Content-Security-Policy to a Pages site whose catalog has inline scripts and a 404 page
that Pages serves at any URL.

## Finding

- Pages joins a header written in two `_headers` rules with a comma, and a browser enforces each
  `Content-Security-Policy` value on its own. A base policy on `/*` plus a "more permissive" one
  with hashes on `/` leaves the page the *intersection*, which blocks the inline script. A policy
  cannot be layered; it is one line, once.
- A path rule such as `/` or `/es/` never reaches the 404 page, which is served at the missing URL,
  nor `/index.html` or `/?utm_source=...`. Only `/*` does, so the hashes of every inline script go
  into that one policy.
- Chrome logs an *error* for a `Permissions-Policy` feature it does not know on its platform:
  `web-share` and `bluetooth` are unknown on desktop Linux, the platform Lighthouse runs on, and a
  console error costs the Best Practices score. A feature whose default is already `self` need not
  be named at all.

## Guard

`tests/test_public_csp.py` serves the build over HTTP with the headers its `_headers` file
implies and fails on any `securitypolicyviolation`, any console error (the harness now enables
`Log` and keeps every entry) and any Permissions-Policy complaint. It asserts exactly one policy
line and the same value at `/`, `/es/`, `/index.html`, a query string and a path that does not
exist; and that the hashes it lists are exactly those of the scripts the build emitted.

## Rule

Write a policy once, on `/*`. Test it in a browser that enforces it, and read the console as well
as the violation events: some mistakes in a header are logged, not reported.
