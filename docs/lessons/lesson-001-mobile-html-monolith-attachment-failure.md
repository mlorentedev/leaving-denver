---
id: "lesson-mobile-html-monolith-attachment-failure"
type: lesson
scope: local
tags: [movingsale, mobile, ux, web, lesson]
created: "2026-09-25"
source: "Denver moving sale platform development"
---

# Lesson: Mobile HTML Monolith Attachment Failure in Second-Hand Sales

## Context (The Problem/Error)
> "Attempted to package all inventory cards and photos as Base64 strings into a single 3.6 MB `index.html` file to be sent directly as a WhatsApp or SMS attachment to prospective buyers."

Non-technical mobile buyers on iOS could not preview the `.html` file inside messaging apps. Tapping the attachment displayed raw source code or prompted saving into the iOS Files app, immediately raising malware and phishing suspicions.

## The Finding (Root Cause/Solution)
The root cause was treating mobile messaging apps as universal document viewers for rich interactive HTML bundles. Mobile OS sandboxes restrict execution of local HTML files received via chat attachments.
The correct solution is deploying a lightweight (<50 KB) static HTML catalog with progressive, lazy-loaded JPEGs hosted on Cloudflare Pages (`leaving-denver.pages.dev`). Sending a clean short URL delivers sub-50ms render times and instant 1-tap SMS contact buttons without device friction.

## Anti-Pattern (What NOT to do)
Do not send offline HTML monoliths or Base64-encoded web bundles as file attachments to marketplace leads.

## Golden Rule (The Pattern)
> **Whenever distributing second-hand catalogs to mobile marketplace leads, deploy a lightweight CDN-hosted web page with progressive image loading rather than sending local document attachments.**

## References
- `research/competitive_agent_audit.md` (Forensic comparison with DeepSeek monolith)
- `src/leaving_denver/site_builder.py` (Lightweight static compilation pipeline)
