---
tags: [spec, tasks, templates]
created: "2026-11-09"
id: "OPS-018-close-out"
type: spec-tasks
status: active
owner: manu
---

# Tasks - OPS-018-close-out

> TDD order. One task = one focused commit. Tick as you go. Reorder freely while spec is in `draft` state; freeze once you start `implementing`.
>
> **Inline markers**: `[P]` — no dependency on another unchecked task. `[AC<n>]` — helps satisfy acceptance criterion `<n>` of `proposal.md`.

## Setup

- [x] Branch created from main: `feat/close-out` (worktree `worktrees/leaving-denver/feat-close-out`)
- [x] `proposal.md` is complete and acceptance criteria are testable
- [x] No open questions left in `proposal.md` "Risks / open questions"

## Implementation

- [ ] [P] [AC1] Failing test: `disposition` is one of `sale`/`giveaway`, absent means `sale`, an unknown value raises; the inventory holds 12 sales, 4 giveaways and no `Available`.
- [ ] [AC1] `DISPOSITIONS` in `config.py` and the check in the item path (`site_builder`), so an unknown value fails the build.
- [ ] [AC1] `data/inventory.yaml`: the car and the queen bed `Sold` at their real prices; the four giveaways `Sold` + `disposition: giveaway`.
- [ ] [P] [AC2] Failing test: `retro_summary(items, targets, floors, sales)` — the arithmetic (target present or absent, a giveaway at `0`, an unplaced item, an empty group), pure, no sops.
- [ ] [AC2] `src/leaving_denver/retro.py` with `retro_summary` and the report text.
- [ ] [AC2] Failing test: `leaving-denver retro` prints the summary, `--json` prints JSON, exits 1 with a clear message when the private file cannot be read, and its output holds no phone, no token and no secret (sentinels).
- [ ] [AC2] `cmd_retro` in `cli.py` + `retro` in `Makefile`.
- [ ] [P] [AC3] Failing test: the end build's `/index.html` and `/es/index.html` carry the counts (derived from the inventory), the published days and percentage, and the contact line; still no phone, no `sms:`/`tel:`, no item id.
- [ ] [AC3] `sale_over.html`: the result block and the contact line; locale strings in `en.yaml` and `es.yaml`, typed once with the provenance comment.
- [ ] [AC3] `build_end_site()` passes the derived counts to the template.
- [ ] [P] [AC4] Failing test: `docs/case-study.md` exists, cites `make retro`, states the split and the percentages; the README links it; ADR-013 exists and ADR-008 points at it.
- [ ] [AC4] Write `docs/case-study.md`, the README "Results" section, `adr-013-the-end-page-states-the-result.md`, and ADR-008's pointer.
- [ ] [AC5] `features.json` filled in, one feature per acceptance criterion.
- [ ] [AC5] `make check` green in the catalog mode; `dotf spec review`/the end-of-sale CI job green with the switch on.
- [ ] [AC5] Candidate deployment + `scripts/smoke.sh` against it (the ADR-008 rehearsal), then the switch on `main`.

## Closing

- [ ] Every acceptance criterion from `proposal.md` is covered by at least one test
- [ ] Every acceptance criterion has a matching entry in `features.json` with a non-vacuous verification command
- [ ] Type checks pass (`mypy`), lint passes (`ruff`), `make check` green
- [ ] No unrelated changes in the diff (no scope creep)
- [ ] `verification.md` filled in with the evidence, including the `make retro` run the published numbers came from
- [ ] PR opened referencing this spec folder, with a `## Knowledge` section
- [ ] After the merge: the decommission steps (credentials, deployments, monitor, digest), then the archive

## Machine-readable features

See `features.json` beside this file ([[pattern-feature-list-as-primitive]]). Only the harness sets
`"state": "passing"`, after running `verification` and capturing exit 0.
