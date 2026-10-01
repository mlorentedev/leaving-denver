---
id: "lesson-defer-shell-token-substitution-in-make"
type: lesson
scope: local
tags: [make, cloudflare, secrets, deploy]
created: "2026-09-30"
source: "FEAT-005 (#17): Pages preview deploy from Windows"
---

# Lesson: Keep Shell Token Substitution Out of Immediate Make Expansion

## Context

`make check` passed, but `make deploy BRANCH=seller-access-smoke` passed an empty
`CLOUDFLARE_API_TOKEN` to Wrangler. Decrypting the token directly with `sops`
worked in both PowerShell and the shell used by `make`. Wrangler failed before
uploading anything; the problem was not the Cloudflare token or permissions.

## Finding

The shared `CF_ENV := ... "$$(sops ...)"` assignment used immediate expansion.
With the Windows BusyBox `make`, its later use in a recipe lost the deferred
shell substitution: `make -n cf-project` displayed
`CLOUDFLARE_API_TOKEN=""`. The shell never received a `$(sops ...)` command
to execute. Changing the assignment to recursive `CF_ENV = ... "$$(sops ...)"`
preserved that substitution until the recipe reached the shell.

## Guard

`test_local_pages_commands_preserve_sops_shell_substitution` inspects the
expanded dry-run command without decrypting or printing the token. A real
`make deploy BRANCH=seller-access-smoke` then uploaded the sanitized public
site and Functions to a Pages preview. When debugging deploy authentication,
inspect command expansion without logging token values, verify decryption
separately, and never assume a successful build implies a token was passed.
