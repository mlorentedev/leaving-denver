---
id: "ADR-006-seller-tracking-stays-private"
type: adr
status: accepted
owner: manu
date: "2026-09-30"
issue: "mlorentedev/leaving-denver#16"
tags: [architecture, decision, privacy, secrets]
created: "2026-09-30"
---

# ADR-006: Seller Tracking Stays in the Encrypted File

## Status

Accepted. It extends ADR-002 (output isolation) from floors to everything the owner records
while selling.

Amended by ADR-007: private means the plaintext never leaves the owner's machine. The sealed
ciphertext may be served inside `/seller/`, behind Access, so decision 3 no longer confines the
panel's data to a local file. Decisions 1, 2 and 4 are unchanged.

## Date

2026-09-30

## Context

The control panel (FEAT-004) needs per-item facts the public inventory does not hold: targets,
what was posted where and when, price changes, and the realized price and date. The repository
is public and a push to `main` deploys. `data/private.sops.yaml` already holds the floors and
(BUG-008) the realized prices.

## Decision

1. All of it lives in `data/private.sops.yaml`: `targets`, `sales.<id>.{price,at}`,
   `tracking.<id>.channels.<channel>` (posting dates) and `tracking.<id>.price_log`.
   Listing dates and channels would be harmless alone, but "listed for five weeks, unsold" is
   leverage for a buyer, the same reason drop timing stays private, and a public file would
   cost a commit, a review and a deploy for every post.
2. Writes go through `sops set` with the value on stdin (`private_data.set_private`); the
   owner never decrypts the file to edit it. A list grows by setting its next index, because
   `sops set` rejects a bare JSON list as a value.
3. The panel is a local HTML file at `build/private/panel.html`, written 0600, refused under
   `build/public/`, marked with `data-private-panel` so `verify_security_guarantees` fails the
   build if a public page ever carries it. It has no script and loads nothing.
4. `listed_at` and the renewal date are derived from the posting dates, never stored.

## Consequences

- The public inventory is unchanged; `public_item` stays an allow-list.
- The panel exists only on a machine with the age key. In CI there is no private data and no
  panel, which is the intended state.
- Tracking history is as durable as the encrypted file: it is in git, encrypted.
