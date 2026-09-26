---
id: "lesson-git-lfs-install-under-global-hookspath"
type: lesson
scope: local
tags: [git, git-lfs, hooks, dotfiles]
created: "2026-09-25"
source: "Moving content/photos to Git LFS"
---

# Lesson: `git lfs install` Under a Global core.hooksPath Writes Into the Shared Dispatcher

## Context (The Problem/Error)
This machine sets `core.hooksPath` globally to the dotfiles hook dispatcher, which chains to each
repo's `.git/hooks/<type>`. `git lfs install` honours `core.hooksPath`, so it tries to write its
`pre-push`, `post-checkout`, `post-commit` and `post-merge` hooks into the shared dispatcher
directory. That would run LFS hooks in every repository on the machine, or fail because the hook
names already exist there.

## The Finding (Root Cause/Solution)
Install only the filters, then put the hooks where the dispatcher looks:

```bash
git lfs install --local --skip-repo   # filters in .git/config, no hooks
# then write .git/hooks/{pre-push,post-checkout,post-commit,post-merge}
# each as: command -v git-lfs >/dev/null && git lfs <hook> "$@"
```

## Anti-Pattern (What NOT to do)
Running plain `git lfs install` (or `--force`) on a machine with a global `core.hooksPath`.

## Golden Rule (The Pattern)
> **With a global hooks dispatcher, repo-specific hooks go in `.git/hooks`, never in the
> dispatcher. Make `make install` set them up so a fresh clone works (DX-001).**
