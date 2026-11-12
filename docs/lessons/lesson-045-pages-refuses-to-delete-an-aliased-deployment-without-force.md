# Lesson 045 — Pages Refuses to Delete an Aliased Deployment Without `?force=true`

**Date:** 2026-11-11
**Tags:** [cloudflare, pages, api, deploy, close-out, script]

## What happened

The close-out's step 4 deletes every Pages deployment except the one serving production, and the
first version of `scripts/prune-deployments.sh` sent a plain `DELETE .../deployments/<id>`. It
listed 242 deployments correctly, marked the right one `keep`, and then stopped on the first
delete with an HTTP 400 that said nothing useful on the terminal:

```
$ make prune-deployments-apply
curl: (22) The requested URL returned error: 400
prune-deployments: deleting 6e2aca84-… failed after 0 deleted: the rest were left alone
```

The body carries the reason, and `--fail-with-body` prints it only if the caller keeps it:

```
{"errors":[{"code":8000035,"message":"You cannot delete an aliased deployment without a
\`?force=true\` parameter in the API request URL."}]}
```

Cloudflare will not delete a deployment that holds a branch alias — and every preview alias the
close-out exists to close (`candidate.leaving-denver.pages.dev` and the per-branch previews) is
exactly one of those. So the "safe" API call could not delete anything at all.

Two smaller findings came out of the same run:

- A **production** deployment answers with `aliases: null`. The alias that identifies it is not in
  the object; it is the project's `canonical_deployment.id`. Matching `<project>.pages.dev` against
  `aliases` — the obvious first implementation — finds zero keepers and refuses every run.
- The project held **242** deployments, not the ~25 that the GitHub deployments list suggests, and
  they span 81 API pages at `per_page=3` (10 at 25). A pruning step that reads one page deletes a
  tenth of the mess and reports success.

## Why it matters

A destructive script whose first real run fails is the good outcome: it stopped with 0 deleted
because the loop exits on the first failed call. The loaded failure is the other one — reading a
one-page answer as the whole list, or taking "the newest" for "the one serving production", and
then reporting a clean run over a set that was never complete. The keeper rule here is
Cloudflare's own answer (`canonical_deployment`), not an inference from dates or aliases, and the
dry run prints the keeper's id before anything is deleted.

## What to do next time

- When a delete answers 400 with no body in the log, re-run the call with `-w '%{http_code}'` and
  read the body; Cloudflare's `errors[].code` names the missing parameter.
- `?force=true` is correct here because the keeper is unreachable from the delete loop. If the
  keeper were chosen by alias, force would be a way to delete production.
- Assert the keeper's identity in the dry run's output and in the script's fail-closed path
  (`tests/test_prune_deployments.py`), not just in the delete path: the first two bugs above were
  both in *identifying* what to keep.
