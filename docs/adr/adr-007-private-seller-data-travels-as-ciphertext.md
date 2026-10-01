---
id: "ADR-007-private-seller-data-travels-as-ciphertext"
type: adr
status: accepted
owner: manu
date: "2026-10-01"
issue: "mlorentedev/leaving-denver#140"
tags: [architecture, decision, privacy, secrets, security]
created: "2026-10-01"
---

# ADR-007: Private Seller Data Travels as Ciphertext

## Status

Accepted (owner decisions of 2026-09-30, open questions answered 2026-10-01). It amends:

- **ADR-006**, decision 3 and the meaning of "private";
- **ADR-002**, decision 2 ("`build/public/` holds public artifacts only");
- **ADR-005**, negative consequence 1 (a CSP must allow the beacon everywhere);
- the rule in `docs/runbooks/ops.md`, "Never put floors ... under `build/public/`, even behind Access".

## Date

2026-10-01

## Context

FEAT-009 (#140) makes `/seller/` the one seller tool, on a phone and on a computer. PR 1 moved
the copy that needs no private data. PR 2 needs the rest: floors, negotiation notes, and the
tracking ADR-006 added for the control panel (FEAT-004): `targets`, `sales`, `tracking.<id>.channels`
and `tracking.<id>.price_log`. All of it lives in `data/private.sops.yaml`.

Today four rules keep that data off the web:

- ADR-002 publishes only `build/public/`.
- ADR-006 keeps the panel a local file.
- The ops runbook forbids floors under `build/public/` even behind Access, because "disabling an
  edge policy must not disclose them".
- The age key exists only on the owner's machine.

`/seller/` is already behind Cloudflare Access: One-time PIN, owner email only, on `seller` and
`seller/*` of `leaving-denver.pages.dev` and `*.leaving-denver.pages.dev`. Behind it,
`functions/_middleware.js` verifies the Access JWT against `ACCESS_TEAM_DOMAIN` and `ACCESS_AUD`
and answers 503 when either binding is missing. The repository is public, and every push to
`main` deploys.

The runbook rule stands for plaintext. What the owner decided is how private data can reach the
phone without breaking it.

## Decision

### 1. What "private" means from now on

**Plaintext never leaves the owner's machine.** Its ciphertext may leave, sealed under a
passphrase only the owner knows. It may be stored in a GitHub environment secret and served
inside `/seller/`, behind Access. Nowhere else.

Access is the first lock and the passphrase the second. Either alone must be enough to keep
the data from a buyer.

### 2. One seller tool, behind Access

`/seller/` stays where it is, under the Access application and the fail-closed middleware above.
Nothing in this ADR relaxes either. The ciphertext is embedded in `/seller/index.html` only, as
a non-executing `<script type="application/json">` block. No other file under `build/public/`
carries it.

### 3. The seal

Sealing happens inside `make ci-secrets`, on the owner's machine:

1. **Decrypt in process.** `decrypt_private()` decrypts sops, as `make sold` does today. Nothing
   is written to disk or printed.
2. **Build the payload from an allow-list**: `floors`, `targets`, `sales`, `tracking`, `notes`,
   and `sealed_at` (the date and time of the seal). `seller.phone` and `cloudflare_pages_token`
   are never in it; the phone keeps its own secret (`SELLER_PHONE`, ADR-002).
3. **Read the passphrase from the terminal**, twice, with echo off. Never from argv, the
   environment or a pipe. With no TTY, the target refuses. An agent shell has no TTY, so an
   agent cannot run it.
4. **Encrypt with WebCrypto in Node** (`crypto.subtle`). It is the same API the page decrypts
   with, and Node 24 is already required for Tailwind, so there is no new dependency. The
   payload and the passphrase reach the Node child on stdin.
5. **Check the result.** The target decrypts its own envelope and compares it with the payload,
   then checks the size budget (decision 6).
6. **Upload.** It pipes the envelope on stdin to
   `gh secret set SELLER_SEALED --env production` and `--env preview`, the same way as
   `SELLER_PHONE`, and removes any repository-level copy.

The age key never goes to CI. CI never sees plaintext.

### 4. Crypto parameters

| Parameter | Value |
|---|---|
| Cipher | AES-256-GCM (WebCrypto `AES-GCM`, 128-bit tag) |
| KDF | PBKDF2-HMAC-SHA256, **1,000,000 iterations**. The build refuses an envelope below 600,000, the OWASP 2023 floor for this hash. |
| Salt | 16 random bytes, new on every seal |
| IV | 12 random bytes, new on every seal |
| Additional data | the envelope header (`v`, `kdf`, `iter`, `salt`), so a header that was edited fails decryption |
| Envelope | `{"v":1,"kdf":"PBKDF2-SHA256","iter":1000000,"salt":"<b64>","iv":"<b64>","ct":"<b64>"}` |
| Passphrase | at least 5 distinct words from the EFF large wordlist (7,776 words), separated by spaces or hyphens. A random 5-word phrase is 64.6 bits. |

**Salt and IV are per seal, not per build.** CI holds no key, so it cannot re-encrypt. Every build
of one secret embeds the same bytes. That is safe: GCM is broken by reusing an IV with *different*
plaintext under one key, and every new seal draws a new salt, which gives a new key, and a new IV.

**PBKDF2 over Argon2id.** PBKDF2 is native to WebCrypto in every browser and in Node. Argon2id would
need a vendored WASM build, an opaque binary, in the one page that holds plaintext and on the
sealing side. It would also need memory settings that mobile Safari can run. Argon2id resists GPUs
better. Here the passphrase floor already makes a brute force hopeless within the data's useful
life, so that advantage buys little.

**Why the floor is enough.** The data is worth something to a buyer until the sale ends (the
departure on 2026-11-09). At 1,000,000 PBKDF2 iterations, a high-end GPU tries on the order of
10^4 passphrases per second. Searching half of 2^64.6 with a thousand such GPUs takes tens of
thousands of years.

**The rule the target enforces.** The target cannot tell whether words were chosen at random, so
it checks only what it can measure: the word count, the words are on the list, no word repeats,
and both entries match. It offers to generate a passphrase with `secrets.choice` and writes it to
the TTY only.

### 5. The page

- **No secret in the build.** This is the state of the `test` job and of every PR. The private
  section says "No private data in this build". The public half of the tool works unchanged.
- **Malformed envelope.** The build fails. The builder checks the version, the KDF name,
  `iter` >= 600,000 and the salt and IV lengths.
- **Wrong passphrase.** The GCM tag fails. The page shows one message: "That passphrase does not
  open the private data." It renders no private element, keeps no partial result, does not count
  attempts and does not lock out. A counter in the browser means nothing to an attacker who holds
  the ciphertext offline.
- **Right passphrase.** The page shows the private views and "Private data as of
  `<sealed_at>`". `sealed_at` is inside the ciphertext, so even the date of the last update is
  hidden.
- **Remembering the passphrase.** Not persisted. The derived key is a non-extractable `CryptoKey`
  held in memory. There is nothing in `localStorage`, `sessionStorage`, IndexedDB or cookies. A
  "Lock" button and `pagehide` drop the key and clear the private DOM, and a reload asks again.
  The phone's own password manager may fill the field (`autocomplete="current-password"`). That
  store is the device's, guarded by its unlock, not the site's. sessionStorage was rejected:
  phone tabs live for days, so the passphrase would sit in plain text in origin storage for any
  script on the page to read.
- **No third-party script and no network after unlock.** `/seller/*` gets its own
  `Content-Security-Policy`: scripts from `'self'` only, `connect-src 'none'`, and
  `frame-ancestors 'none'`. That policy blocks the Web Analytics beacon Cloudflare injects
  (ADR-005) **on `/seller/` only**. The owner's own visits are not worth counting, and a
  third-party script in the page that holds decrypted floors is not acceptable.
  `test_no_csp_stops_the_cloudflare_beacon` is narrowed to every path except `/seller/*`.

### 6. Size

GitHub caps a secret at 48 KB (49,152 bytes). The target refuses an envelope over **40,000
bytes** and sets nothing.

| Data | Shape | Plaintext JSON |
|---|---|---|
| `tests/fixtures/private.example.yaml`, allow-listed | 6 floors, 4 targets, 1 sale, 4 tracked items | about 0.7 KB (about 120 B per item) |
| Worst case at departure | 18 items, each with a floor, a target and a sale; 5 channels with 6 dates each; 6 price-log entries; a 500-character note | about 24 KB |

At the worst case the envelope is about 32 KB: 24 KB plus the 16-byte tag, times 4/3 for
base64, plus about 100 B of header. That is under the budget. If it ever is not, compress before
sealing (`CompressionStream` in Node and the browser) under envelope `v: 2`. No attacker-chosen
input is mixed into the payload, so compressing before encrypting leaks only the length.

### 7. Read anywhere, write on the computer

- **Reads** work on any device that passes Access and knows the passphrase.
- **Writes** stay `make post`, `make sold` and `make reprice` on the computer. They change only
  `data/private.sops.yaml`.
- There is no backend.

### 8. Owner answers (2026-10-01)

- **One tool.** `make panel` and `build/private/panel.html` are retired in PR 2. `/seller/`
  shows the same data. Recording stays `make post|sold|reprice`.
- **Passphrase.** It is generated: 5 words from the EFF list, offered by the target, as in
  decision 4. There is no owner-chosen phrase and no strength-estimator dependency.
- **Re-seal on record.** After `make post|sold|reprice` succeeds, the target asks whether to
  update `/seller/` now. On yes, it asks for the passphrase, seals, sets the secret and
  dispatches the deploy. On no, nothing else happens.
- **Notes.** Free text, one note per item, up to 500 characters, edited with `make secrets`.

## Consequences

### Positive

- The phone has floors, notes and tracking, and `poster_assistant.html`, its JavaScript PIN
  (`8011`) and the local-only workspace can go (FEAT-009 PR 2, step 4).
- Each failure below exposes ciphertext only:
  - Access failing open: a deleted application, a route not covered, a path the middleware
    misses, a deploy without Functions;
  - the owner's email OTP compromised;
  - anyone with Cloudflare or GitHub access reading the deployment or the secret.

### Negative

- **Staleness.** `/seller/` shows the data as of the last `make ci-secrets` *and* the deploy
  after it. A deploy uses the secret as it was when it started. `make post` alone changes
  nothing on the phone. The page shows `sealed_at` so the owner can tell.
- **One more interactive step.** `make ci-secrets` now asks for the passphrase, and the deploy
  job refuses to run without `SELLER_SEALED`, as it does without `SELLER_PHONE`. Run
  `make ci-secrets` before merging PR 2.
- **Rotation (passphrase leaked or suspected).**
  1. Run `make ci-secrets` with a new passphrase.
  2. Redeploy production and dispatch a preview.
  3. **Delete every earlier Pages deployment.** Each stays reachable at its own
     `<hash>.leaving-denver.pages.dev` URL with the old ciphertext, behind Access but under
     the leaked key.
  4. Treat the floors as known to whoever holds the old passphrase.
  5. If Access or the email account is also suspect, fix it first.
- **The passphrase is the whole defence once Access fails.** A weak or reused one undoes this
  ADR. The target's word rule is a floor, not proof.
- **What this does not cover:** a compromised phone or computer, a keylogger, or a malicious
  script running in `/seller/` after unlock. The CSP narrows the last one; it does not remove it.

### Neutral

- `data/private.sops.yaml` stays committed and encrypted to the age key (ADR-006). That is a
  random 256-bit key, which no one can guess. The sealed envelope is not committed: its key comes
  from a passphrase, which can be guessed.
- ADR-006 decisions 1, 2 and 4 are unchanged. Decision 3 now reads: the panel's views may also be
  served as ciphertext in `/seller/`. Whether `build/private/panel.html` survives PR 2 is FEAT-009's
  decision.

## Alternatives considered

- **Ciphertext committed to the public repository.** Rejected:
  - Anyone could take the ciphertext, not only someone past a broken Access, and work on it
    offline with no deadline.
  - It could never be withdrawn. History and `refs/pull/*` are permanent (lesson-006), so a
    leaked passphrase would open every committed version for good.
  - Every `make post` would cost a commit, a review and a deploy, which is the cost ADR-006
    already refused.
- **Age key in CI.** Rejected:
  - CI would hold plaintext, which breaks decision 1.
  - That key opens the whole sops file, the Cloudflare token and the phone included. A runner
    and every action in the deploy job (wrangler-action among them) would be one step from all
    of it.
  - It also changes nothing for the page: it would still need either this envelope or plaintext
    behind Access.
- **Plaintext behind Access only.** Rejected. It leaves one control, and every failure in the
  positive consequences above would disclose the floors at once. Access was verified once, at
  one point in time.
- **A backend with KV** (Pages Functions plus Workers KV, writes from the phone). Rejected:
  - It adds a store holding plaintext, or a key held by a server.
  - Writes would need their own authentication.
  - There would be a second source of truth beside sops, to keep in sync.
  - That is a lot of new code six weeks before departure. The owner chose reads anywhere,
    writes on the computer.
- **Argon2id via WASM** and **remembering the passphrase in sessionStorage**: see decisions 4
  and 5.

## Revisit when

- **The passphrase leaks, or Access is found open:** rotate (above). The decision itself stands.
- **Writes on the phone become necessary:** if staleness makes the owner quote or record a wrong
  price more than once, the KV backend is reopened.
- **The envelope passes 32 KB:** compress (`v: 2`) before the 40,000-byte refusal is reached.
- **The sale ends** (2026-11-09):
  - delete `SELLER_SEALED` from both environments;
  - redeploy;
  - delete the deployments that carry an envelope.

  This ADR then describes nothing live.

## References

- ADR-002 (output isolation), ADR-005 (Web Analytics), ADR-006 (seller tracking)
- Spec: `specs/FEAT-009-one-seller-tool/` (PR 2: `pr2-encrypted-private-data.md`)
- Runbook: `docs/runbooks/ops.md`, "Owner-only mobile listing copy (Cloudflare Access)"
- `docs/lessons/lesson-006-extract-private-data-before-first-public-push.md`
- `functions/_middleware.js`, `src/leaving_denver/private_data.py`, `tests/fixtures/private.example.yaml`
