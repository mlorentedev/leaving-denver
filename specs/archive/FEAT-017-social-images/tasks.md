---
tags: [spec, tasks]
created: "2026-10-06"
---

# Tasks - FEAT-017-social-images

## Setup

- [x] Branch `feat/social-images` from `main`
- [x] `proposal.md` complete; owner decisions recorded (collage in the post, QR and message in the story)

## Implementation

- [x] [AC1-AC5][AC7] `tests/test_social.py` written first
- [x] [AC2][AC3] `src/leaving_denver/social.py`: selection rule, layout, QR geometry, rendering in the site's font
- [x] [AC1][AC4][AC5] `write_social` in `site_builder.py`, `templates/social.html`, `assets/social.css`, `locales/social.yaml`, `/social` in `END_REDIRECTS`
- [x] [AC6] `instagram` and `whatsapp` in `functions/api/hit.js`; the drift test reads `social.SOURCES`
- [x] [AC7] `@source` for the template in `public.css`; the class coverage test includes it
- [x] The seller playbook says where to get the images

## Verification

- [x] Full suite green; images rendered with the real photos and looked at
