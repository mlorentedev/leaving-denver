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

`make install` does this. It finds the hooks directory with
`git rev-parse --path-format=absolute --git-common-dir`, plus `/hooks`. That path also
works from a linked worktree.

## Anti-Pattern (What NOT to do)
Running plain `git lfs install` (or `--force`) on a machine with a global `core.hooksPath`.

Finding the hooks directory with `git rev-parse --git-path hooks`. It follows
`core.hooksPath` too, so it returns the dispatcher. The first version of `make install`
used it and created `post-commit` and `post-merge` LFS hooks in `~/.dotfiles/git-hooks/`,
which made every repository on the machine run them. They were removed the same session
(2026-09-26).

## Golden Rule (The Pattern)
> **With a global hooks dispatcher, repo-specific hooks go in `.git/hooks`, never in the
> dispatcher. Make `make install` set them up so a fresh clone works (DX-001).**
