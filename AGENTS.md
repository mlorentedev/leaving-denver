# AGENTS.md

> Instructions for AI coding agents (Claude, Copilot, Cursor, Codex) operating in this repo.

## Spec-Driven Development

This repo follows the **Spec-Driven Development per feature** pattern: non-trivial changes are specified before they are implemented.

When the user asks to **create, fill, or archive a spec**, follow this workflow. The `dotf` CLI (installed via dotfiles, on PATH) is the canonical, self-contained interface — run `dotf spec --help` for the full surface.

| Trigger phrase | Action |
|---|---|
| "create a spec for X", "scaffold spec X", "start working on X" | `dotf spec init <feature-id> --issue <N>` |
| "fill in the proposal for X", "help me write the proposal" | edit `specs/<feature-id>/proposal.md` — the Why + acceptance criteria — before writing implementation code |
| "archive spec X", "close spec X" | `dotf spec archive <feature-id> --pr <url>` |

Per-feature specs live at `specs/<feature-id>/` in this repo; archived at `specs/archive/<feature-id>/` (never deleted — audit trail).

**Skip SDD for**: typo fixes, comment-only edits, mechanical refactors, bug fixes <20 lines with obvious cause, doc-only changes.

`<feature-id>` format: `^([A-Z]+[0-9]*-[0-9]+[a-z]?(-[a-z0-9-]+)?|[0-9]{4}-[0-9]{2}-[0-9]{2}-[a-z0-9-]+)$` (e.g., `AI-001-ollama-public`, `ADR028-004`, `SDD-012b-guard`, `2026-05-13-cleanup`). This string is `idPattern` in dotfiles `cli/internal/spec/spec.go` verbatim; a drift test asserts every copy matches, so do not reword it.
