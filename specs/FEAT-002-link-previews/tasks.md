---
tags: [spec, tasks, templates]
created: "2026-09-30"
---

# Tasks - FEAT-002-link-previews

## Setup

- [x] Branch `feat/share-links` from main 6ac3293; #14 In Progress
- [x] `proposal.md` complete; the design choices are defaults the owner can overrule in review

## PR 1: previews and links

- [x] [AC1] [AC2] [AC3] [AC4] [AC5] [AC6] [AC7] `tests/test_link_previews.py` written first (RED: 15 failed)
- [x] [AC4] `image_processor.write_share_image`: letterboxed 1200x630, written only when the bytes change, older previews pruned
- [x] [AC1] [AC2] [AC3] [AC5] [AC7] `site_builder`: `ROBOTS_TXT`, `site_url()`, share pages rebuilt whole, catalog tags; `_og.html` and `share.html` templates
- [x] [AC6] `/#<id>` opens the item after load
- [x] `test_template_sees_only_sanitized_data` records the context per template; share pages get `locale`, `t`, `og` and `target` only
- [x] `scripts/smoke.sh`: robots names `facebookexternalhit`, the catalog `og:image` answers as a JPEG, the first item's share page exists
- [x] ADR-004, ADR-001 note, runbook "Link previews"
- [x] `make check` green
- [x] Independent review (reviewer subagent, 9a0405f) dispositioned in `verification.md`

## PR 2: share button

- [x] [AC8] Tests first (RED: 7 failed): button in the item sheet, shared URL equals the share page's own `og:url`, share/copy/select fallbacks, locale strings
- [x] [AC8] Share button in the item sheet: `navigator.share`, clipboard fallback, select fallback; `share` / `link_copied` strings; classes compile (class coverage green)
- [x] PR 2 reviews dispositioned in `verification.md`; headless Chrome behaviour tests added

## Closing

- [ ] After deploy: Facebook Sharing Debugger shows the item card for one share page
- [ ] Independent adversarial review before archive
