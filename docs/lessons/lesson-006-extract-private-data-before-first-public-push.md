---
id: "lesson-extract-private-data-before-first-public-push"
type: lesson
scope: local
tags: [security, git, secrets, sops, public-repo]
created: "2026-09-25"
source: "Publishing leaving-denver as a public GitHub repo"
---

# Lesson: Extract Private Data Before the First Push of a Public Repo

## Context (The Problem/Error)
> "The repo was about to go public with reserve floor prices (`firm_floor_price`) and the seller phone in plaintext in `data/inventory.yaml`, tests and docs."

The natural move — push, then open a PR that moves the secrets into sops — publishes them anyway. On a public GitHub repo every PR diff and every `refs/pull/*` ref is permanent: the red lines of the "remove the secret" PR are the secret, and a later force-push to `main` does not purge PR refs.

## The Finding (Root Cause/Solution)
Secret extraction and history rewrite must happen **locally, before the first push**, as a baseline commit reviewed by the human from the local diff (the PR review gate cannot exist yet without leaking).

For this repo:
1. Floors and phone moved to `data/private.sops.yaml` (sops + age, canonical dotfiles key); public build reads the phone from `SELLER_PHONE` (CI secret) or the sops file.
2. A fresh orphan commit replaced the three local commits (cheaper and safer than regex-scrubbing small integers with `git filter-repo`).
3. Photos moved to Git LFS and `dist/` stopped being tracked in the same rewrite.
4. The old history is kept only as the local ref `refs/backup/pre-public-main` — never push with `--all`/`--mirror`; drop it with `git update-ref -d refs/backup/pre-public-main` once the sale is over.

## Anti-Pattern (What NOT to do)
Pushing first and cleaning up with a PR, or relying on force-push to erase data from a public repo.

## Golden Rule (The Pattern)
> **Anything that must stay private is removed from every commit before the first public push; after that, assume the history is forever.**

## References
- `.sops.yaml`, `data/private.sops.yaml`, `src/leaving_denver/private_data.py`
- dotfiles `docs/runbooks/guide-secrets-governance.md` (age key recovery)
