---
id: "TEST-002-computed-contrast"
type: spec
status: implementing # draft | implementing | verifying | archived
created: "2026-09-30"
issue: "mlorentedev/leaving-denver#106"   # repo#NNN — GitHub issue / Project item that tracks this spec
tags: [spec, proposal]
template_version: "1.0"
---

# TEST-002-computed-contrast

## Why

<!-- from issue #106, raised by the second independent FEAT-003 review -->

FEAT-003's contrast guard is a denylist of colour classes per ground (light, grey, dark). It passes anything the list does not name:
- alpha modifiers (`text-neutral-500/60`);
- arbitrary colours (`text-[#999]`, and the body's own `text-[#1c1c1c]` is never checked);
- `opacity-*` on text;
- `emerald-700` on a grey ground (4.35:1).

The 12 px rule is a denylist of three arbitrary sizes, so `text-[9.5px]` and `text-[0.6rem]` pass.

## What

- **Compute the contrast.** Every run of visible text in the rendered EN and ES pages is measured against the ground it sits on, and must reach 4.5:1:
  - Colours come from the compiled stylesheet. Tailwind v4's oklch palette is converted to sRGB, and `[#hex]` is read directly.
  - Alpha modifiers and `opacity-*` blend the text into its ground. A translucent ground blends into the one behind it.
  - `sr-only` and `aria-hidden` text is exempt, as in WCAG 1.4.3.
  - Hover, focus and selection states are not the resting colour, so they are not measured.
- **Calibrate the arithmetic** against Tailwind v4's published hex values and WCAG's #767676 reference pair.
- **Script-built class strings** (status pills, spec bullets) are measured on their own ground, or on the white sheet they are rendered into.
- **Sizes:** any arbitrary `text-[Npx|Nrem]` in the template or the rendered pages must be at least 12 px.

## Out of scope

- **`poster_assistant.html`**: owner-only, never published, and it keeps its dense 10–11 px layout. A published page would need this guard; this one is a local tool.
- **The large-text 3:1 allowance:** every text run is held to 4.5:1, which is stricter.

## Acceptance criteria

- AC1: the rendered pages pass a computed 4.5:1 check for every visible text run.
- AC2: the checker fails on a set colour, an inherited colour, grey grounds (`neutral-500`, `emerald-700`), an alpha modifier, an arbitrary hex, `opacity-*` and a tinted ground.
- AC3: the checker passes readable text, `sr-only` and `aria-hidden` text, hover-only colours, and faded images.
- AC4: the colour conversion matches Tailwind v4's hex values within 1.5/255, and the ratio matches WCAG's reference.
- AC5: no arbitrary font size under 12 px in the template or the rendered pages.
