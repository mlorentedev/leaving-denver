---
id: "lesson-pages-answers-a-missing-file-with-the-home-page"
type: lesson
scope: local
tags: [cloudflare, ci, smoke, testing]
created: "2026-10-01"
source: "CI run 36847628465: production deploy of 13db4cf"
---

# Lesson: Pages Answers a Missing File With the Home Page

## Context

Cloudflare Pages has no `404.html` to serve for this site. In that case it serves the top
`index.html`, with a 200, for any path it has no file for:
`/definitely-not-here.txt` comes back as `200 text/html`. `scripts/smoke.sh` runs seconds after
a deploy, against a deployment that may not have published every file yet.

## Finding

The deploy of 13db4cf failed its smoke with "robots.txt is permissive", and the same deployment
passed minutes later. The fetch did not fail: `curl --retry` only retries errors, and a 200 is
not one. During that window the "robots.txt" it read was the catalog page, which has no
`User-agent: *` group, so the content check blamed the file. Retries on HTTP status cannot cover
a fallback that answers 200.

## Guard

`smoke.sh` fetches robots.txt through `robots_txt()`, which retries until the body reads as
robots rules and otherwise fails with "served as a page", not "permissive". The stub in
`tests/test_smoke_script.py` serves index.html for a path a set number of times, and two tests
pin both outcomes; both fail against the old script.

## Rule

Against a static host with a catch-all fallback, a 200 does not prove the file is there. A
smoke that reads content has to recognise the fallback and retry it as it would a 404.
