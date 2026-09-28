---
id: "lesson-template-contexts-are-public-data-contracts"
type: lesson
scope: local
tags: [security, templates, privacy, testing]
created: "2026-09-28"
source: "BUG-001 PR 4: seller metadata added to the public catalog context"
---

# Lesson: Template Contexts Are Public Data Contracts

## Context

The catalog needed public seller metadata for the departure countdown, pickup location and
payment terms. Passing the complete `seller` mapping to Jinja worked, but also meant that a
future phone number or private field added to the YAML would silently reach the public template.

## Finding

Sanitizing item JSON is insufficient when a template receives additional top-level mappings.
Every template argument is part of the publication boundary and needs its own explicit allowlist.

## Guard

`sanitize_public_seller` copies only location, departure date and payment methods. The isolation
test injects a phone into the source seller mapping, spies on the Jinja context and fails if that
phone or any private item field reaches the renderer.
