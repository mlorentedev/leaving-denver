---
tags: [spec, proposal, privacy, secrets]
created: "2026-10-01"
---

# FEAT-009 PR 2: private data in `/seller/`, as ciphertext

> **Where this goes.** This is the PR 2 section of `specs/FEAT-009-one-seller-tool/proposal.md`.
> That proposal is on `feat/one-seller-tool-copy` (PR #142), not on `main`, so the section lives
> in its own file for now. Fold it into `proposal.md` once #142 merges.
>
> Decided in **ADR-007** (`docs/adr/adr-007-private-seller-data-travels-as-ciphertext.md`).
> This file sets acceptance criteria only; the decisions and their reasons are in the ADR.

## Why

The owner wants one seller tool, usable the same way anywhere, and PR 1 left its private half in
`poster_assistant.html`. ADR-007 allows that half into `/seller/` only as ciphertext, sealed on the
owner's machine under a passphrase only the owner knows.

## What

1. **Seal.** `make ci-secrets` decrypts sops in process and builds the allow-listed payload:
   `floors`, `targets`, `sales`, `tracking`, `notes`, `sealed_at`. It reads the passphrase from
   the TTY, seals with Node WebCrypto (PBKDF2-SHA256 at 1,000,000 iterations, then
   AES-256-GCM), checks the round trip and the size, and pipes the envelope to the
   `SELLER_SEALED` secret of both environments.
2. **Build.** The builder embeds `SELLER_SEALED`, when it is set, in `/seller/index.html` only,
   after validating the envelope. The deploy job requires the secret.
3. **Page.** The page unlocks with the passphrase in the browser and shows:
   - the three-week plan and the floors;
   - the negotiation notes;
   - the control-panel views (posts, sales, targets, price log);
   - "as of `<sealed_at>`".
4. **Remove** `poster_assistant.html`, its JavaScript PIN and the local-only workspace.
   `verify_security_guarantees` and the isolation tests change to match ADR-007's definition of
   private. `build/private/panel.html` follows the owner's decision (see open questions).
5. **Docs.**
   - `docs/runbooks/ops.md` gets the seal, rotation and decommission steps.
   - `docs/runbooks/seller-playbook.md` says that `make post`, `make sold` and `make reprice`
     reach the phone only after `make ci-secrets` and a deploy.
   - `docs/ARCHITECTURE.md` (the isolation paragraph and the threat model). It says floors are
     "never compiled into the public deployment", which stops being true for their ciphertext.
6. **CSP.** `/seller/*` gets its own Content-Security-Policy. `test_no_csp_stops_the_cloudflare_beacon`
   now checks every path except `/seller/*`.

## Where each criterion is proven

- **Every PR and every `test` job.** These have no secret, so they prove the fail-closed state
  (AC2).
- **Local runs.** Fixture-based criteria (AC1, AC3, AC4, AC5, AC7) seal
  `tests/fixtures/private.example.yaml` with a test passphrase. Its values are unusual on
  purpose, so a leak can be searched for. The tests run locally and in the `test` job.
- **The `deploy` job.** Its `make check` runs with the real `SELLER_SEALED`, so AC6 validates the
  real envelope there.
- **What no test proves.** CI never has plaintext, so no CI job proves "no plaintext of the real
  data". That holds by construction: no age key in CI (AC10).

## Acceptance criteria

- [ ] **AC1: no plaintext private value in any built file.**
  - The test plants sentinel values that cannot occur in public content. This is the approach
    of `test_template_sees_only_sanitized_data`. The small integers in
    `private.example.yaml` (13, 33, ...) also appear in dates, sizes and prices, so a search
    for them would fail on public content.
  - The sentinels go into every allow-listed key: a floor, a target, a sale, a price-log
    price, a posting date and a note. Then the data is sealed and built.
  - No file under `build/public/` holds any sentinel or the fixture phone's digits. The test
    decodes HTML entities and JSON escapes before searching.
  - Decrypting the envelope with the test passphrase gives exactly the keys `floors`,
    `targets`, `sales`, `tracking`, `notes` and `sealed_at`. There is no `seller`,
    `cloudflare_pages_token` or any other key.
- [ ] **AC2: the page fails closed without the secret.**
  - With `SELLER_SEALED` unset, the build succeeds.
  - `/seller/index.html` has no sealed block. Its private section says "No private data in this
    build", and the public half (PR 1, AC10) still works in the browser test.
  - With the variable set to a malformed envelope, the build fails. Each of these counts as
    malformed: bad JSON, `v` other than 1, `kdf` other than `PBKDF2-SHA256`, `iter` < 600000,
    salt not 16 bytes, IV not 12 bytes.
  - The `deploy` job fails before publishing when `SELLER_SEALED` is empty.
    `tests/test_cd_workflow.py` asserts the step exists.
- [ ] **AC3: a wrong passphrase reveals nothing.** This is a browser test on the fixture
  build.
  - A wrong passphrase shows exactly "That passphrase does not open the private data." The DOM
    then holds no AC1 sentinel and no private element.
  - The right passphrase shows the sentinel floor and "as of".
  - After "Lock", and after a `pagehide`, the DOM again holds no sentinel.
  - At no point does `localStorage`, `sessionStorage`, IndexedDB or `document.cookie` hold
    anything this page wrote.
- [ ] **AC4: the make target refuses a weak passphrase.** Each case below exits non-zero, and a
  fake `gh` on `PATH` records no `secret set` call:
  - fewer than 5 words;
  - a repeated word;
  - a word not in the vendored EFF large wordlist;
  - two entries that do not match;
  - no TTY.
  A passphrase given in argv or the environment is ignored, and the target still asks the TTY.
  A valid 5-word passphrase leads to exactly two `secret set SELLER_SEALED` calls, `--env
  production` and `--env preview`, each with the envelope on stdin and never in argv.
- [ ] **AC5: the payload is under the secret size limit.**
  - The target refuses an envelope over 40,000 bytes and sets nothing.
  - A synthetic worst case is sealed: 18 items, each with a floor, a target and a sale; 5
    channels with 6 dates each; 6 price-log entries; a 500-character note. Its envelope is
    under 40,000 bytes. ADR-007 estimates about 32 KB.
  - The test prints the measured size, not the envelope.
- [ ] **AC6: KDF parameters and per-seal randomness.**
  - The envelope has `iter` = 1000000, a 16-byte salt and a 12-byte IV.
  - Two seals of the same payload with the same passphrase differ in salt, IV and `ct`.
  - Changing `iter` or the salt in a valid envelope makes decryption fail, because the header
    is the additional data.
  - In the `deploy` job, the real envelope passes the builder's validation.
- [ ] **AC7: the browser opens what the target sealed.** A fixture envelope from the Node seal
  step is decrypted by the page in headless Chrome. This is the round trip between the seal and
  the page.
- [ ] **AC8: the envelope lives only in `/seller/index.html`.** No other file under
  `build/public/` holds its `ct` value or a sealed block.
- [ ] **AC9: `/seller/*` has a CSP with no third-party script and no network.**
  - The policy's `script-src` lists only `'self'`, with `connect-src 'none'` and
    `frame-ancestors 'none'`.
  - PR 2 chooses how the header is set: `_headers`, or `functions/_middleware.js`, which
    already handles that path. A unit test covers the mechanism it chooses.
  - What counts is the header on the *served* response. Nothing in the repo yet shows whether
    `_headers` rules apply to a response that passes through the middleware. So the owner
    checks it after an Access login with
    `curl -sI -H "cf-access-token: ..." .../seller/` or the browser's network tab, and records
    the result in `verification.md`.
  - The ADR-005 beacon test passes on every other path.
- [ ] **AC10: plaintext never leaves the machine.**
  - The seal writes no file. The Python side passes the payload and the passphrase to Node on
    stdin only.
  - The test checks this with a fake `gh` and a temporary working directory that stays empty.
  - `.github/workflows/*.yml` mentions neither `SOPS_AGE_KEY` nor `sops`.
- [ ] **AC11: unlocking on the phone is fast enough.** On the owner's phone, unlock (key
  derivation plus decryption) takes 3 s or less with 1,000,000 iterations. This is a manual check,
  and the owner records the time in `verification.md`. Over 3 s, lower `iter`, but never below
  600,000, and record the change in ADR-007.
- [ ] **AC12: the old workspace is gone.**
  - `poster_assistant.html`, the PIN `8011` and any reference to them are absent from `src/`
    and the build.
  - `make panel`, `src/leaving_denver/panel.py`, `templates/panel.html` and `build/private/`
    are gone (owner, 2026-10-01). The panel's row logic moves to the `/seller/` views.
  - `verify_security_guarantees` accepts the sealed block in `/seller/` and still fails a build
    whose `build/public/` contains a plaintext fixture value.
- [ ] **AC13: the runbook covers the operation.** `docs/runbooks/ops.md` names:
  - `SELLER_SEALED`;
  - staleness ("as of the last `make ci-secrets` and deploy");
  - rotation, including deleting earlier Pages deployments;
  - the decommission after 2026-11-09.
  `tests/test_ops_runbook.py` asserts each of them.

## Out of scope

- Writing from the phone (ADR-007, rejected: KV backend).
- Compression and envelope `v: 2`, until the envelope passes 32 KB.
- An attempt counter or lockout in the browser. It is meaningless against an offline attacker.

## Owner answers (2026-10-01)

- **The panel is retired.** `make panel` and `build/private/panel.html` go, with the rest of
  `build/private/`. AC12 covers it.
- **Notes** are `notes.<item-id>`, free text of 500 characters or fewer.
- **The passphrase** is 5 words from the EFF list, as ADR-007 decision 4 says. There is no
  estimator.
- **`make post|sold|reprice` offer to re-seal.** After the write succeeds, they ask whether to
  update `/seller/` now. On yes: passphrase prompt, seal, `gh secret set` for both
  environments, and a deploy dispatch. On no, nothing else happens. AC14 covers it.
- **Deploy requires `SELLER_SEALED`,** as it requires `SELLER_PHONE`, so `make ci-secrets` runs
  before PR 2 merges.

- [ ] **AC14: recording offers to update `/seller/`.** After a successful `make post`, `make sold`
  or `make reprice`, the command asks once whether to update `/seller/`. "No" (the default, and
  any non-TTY run) changes nothing more. "Yes" runs the seal and the dispatch, and the command's
  exit status reflects them. Tests stub the prompt, the seal and `gh`.
