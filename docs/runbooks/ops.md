# Site operations

The catalog deploys automatically on tested pushes to `main`. The public inventory lives in
`data/inventory.yaml`; encrypted phone, reserve floors, and deployment token
live in `data/private.sops.yaml`. Only `build/public/` is published, and the only private
thing in it is the sealed envelope inside `/seller/` (see "The sealed private data").
On a fresh checkout, install Node.js 24+, npm, and `uv`, then run `make install`
before `make check` or direct `uv run leaving-denver build`. Builds compile
Tailwind CSS locally from pinned npm dependencies; if the CLI is missing, stop
and run `npm ci` rather than publishing old assets. Verify `/styles.css` loads
for both `/` and `/es/` (the `/seller/` page uses the same stylesheet).

One-time setup (`make cf-project`, `make protect-main`, `make ci-secrets`) is in the
README, section 3. Deploy tokens and the contact reach CI only through the `production`
and `preview` environments, which allow the `main` workflow ref alone: a branch workflow
must never get a production-capable Pages token. `make audit-deploy` checks that.

## Deploy and roll back

1. Merge the intended change into `main`. The push tests and automatically
   deploys production only if the test job passes. PR runs never deploy.
2. Find the run with `gh run list --workflow ci.yml --event push --branch main --limit 3`,
   then use `gh run watch <run-id> --exit-status`. For a manual preview, dispatch
   `gh workflow run ci.yml --ref main -f branch=preview`; to redeploy production
   explicitly, use `gh workflow run ci.yml --ref main -f branch=main`. The deploy job
   rebuilds with the real `SELLER_PHONE` and `SELLER_SEALED` and runs `make check`, which
   validates the envelope. The job fails if either secret is missing.
3. A production deploy publishes to the Pages branch `candidate` first and runs
   `scripts/smoke.sh` against that deployment. Only if it passes does it publish to
   `main` and smoke the canonical `https://leaving-denver.pages.dev`. A failed
   candidate smoke leaves production on the previous deployment: fix forward. A
   manual preview publishes once and smokes its own deployment URL.
4. Check `https://leaving-denver.pages.dev/` and `/es/` on a phone. Verify the
   changed content and SMS CTA on the canonical site, not just the deployment
   URL. Do not share a failed deployment.

If production is broken, roll back to the last known-good **production**
deployment in the Cloudflare Pages dashboard. Recheck the canonical site and
run `scripts/smoke.sh https://leaving-denver.pages.dev` from a shell with
`curl`. A Pages rollback does not revert `main`: fix or revert the offending
commit before the next production dispatch.

## Owner-only mobile listing copy (Cloudflare Access)

The mobile poster at `https://leaving-denver.pages.dev/seller/` is generated
from **published asking prices only**. It does not contain negotiation floors
in the clear. There is no server-side AI endpoint and no PIN: select an item and platform, then copy the editable title,
description (English or Spanish), tags, and UTM-attributed item link on a phone,
and copy a scam reply. Listings never carry the seller's phone number. Until Access is
configured, the Pages middleware responds `503` rather than serving the tool.

To enable it, an administrator of the Cloudflare Zero Trust account must:

1. Enable the **One-time PIN** identity provider. Create a self-hosted
   Cloudflare Access application for
   `leaving-denver.pages.dev/seller` **and** `/seller/*`, with an **Allow**
   policy for the owner's **exact email address only** (not the whole domain).
   Cover preview hostnames (`*.leaving-denver.pages.dev`) and any future custom
   domains with the same paths. A path ending `/*` does not cover its parent.
2. In Workers & Pages > `leaving-denver` > Settings > Variables and Secrets,
   set `ACCESS_TEAM_DOMAIN` to the HTTPS Access team origin
   (`https://<team>.cloudflareaccess.com`) and `ACCESS_AUD` to that application's
   64-character audience. Configure both production and preview environments;
   these values are runtime bindings, **not** fields in public inventory.
3. Deploy from tested `main`. From an anonymous browser and a preview URL,
   request `/seller/`, `/seller/index.html`, and `/seller/seller.mjs`: none
   may return the HTML/JS (`200`); expect a redirect to Access or a denial.
   Sign in as the allowed owner using the one-time email code, verify the
   poster and copy buttons work on a phone, then test an unlisted identity is
   denied. Only then bookmark or advertise the URL. Recheck after any Access
   policy, Pages hostname, or deployment-route change.

Never put floors, notes, tracking or private drafts under `build/public/` as
plaintext, even behind Access: disabling an edge policy must not disclose them.
The one exception is ADR-007's sealed ciphertext, made on the owner's machine
under a passphrase only the owner knows, and only inside `/seller/`. The buyer
catalog must stay reachable anonymously. The old local workspace (its page, its
folder and its PIN) is gone, and `make serve` serves `build/public/` only.

## The sealed private data (`SELLER_SEALED`)

The owner's floors, targets, sales, listing tracking and notes reach the phone as one
AES-256-GCM envelope (ADR-007), in the CI secret **`SELLER_SEALED`**. The build embeds it in
`/seller/index.html`; the page opens it in the browser with a passphrase of five words. With no
secret the page says "No private data in this build" and the public half still works. The
seller phone and the Pages token are never in it.

**Seal.** `make ci-secrets` (a terminal is required; the seal refuses without one) scopes the
deploy secrets, then seals: it decrypts `data/private.sops.yaml` in process, takes the allow-listed
keys, asks "Passphrase (Enter to generate one):", seals
with Node WebCrypto, and writes `SELLER_SEALED` to both environments with `gh secret set`. To
re-seal without the rest, run `uv run leaving-denver seal`. The envelope has to be under 40,000
bytes (the worst case measures about 33,000). Nothing is written to disk.
After sealing, redeploy: `gh workflow run ci.yml --ref main -f branch=main`.

**The passphrase and Bitwarden.** Press Enter at the prompt to have five words generated. With
`dotf` on `PATH` they are saved to the Bitwarden login item `leaving-denver-seller` (field
`password`, secret id `SELLER_PASSPHRASE`, registered in dotfiles) with
`dotf secrets set SELLER_PASSPHRASE --yes`, and the command prints only "Saved to Bitwarden as
SELLER_PASSPHRASE", never the words. The order is seal, save, then set the secret, so a failed save
stops before anything is uploaded; if the upload fails after a save, Bitwarden already holds the new
passphrase and you run `make ci-secrets` again. Without `dotf`, or if the save fails, the words are
shown on the terminal only, with "Write this down now. It is not stored anywhere.", and you type
them back once to confirm; a wrong confirmation sets nothing. When a save fails the command says
only that `dotf secrets set` failed: run it by hand to see why. A passphrase you type yourself is asked for
twice, and with `dotf` the target offers "Save it to Bitwarden? [y/N]". For autofill on the
phone, open the item in the Bitwarden app and add the URI
`https://leaving-denver.pages.dev/seller/`: the unlock form carries a hidden username field,
`seller`, so Bitwarden offers the saved entry. Check it without printing it:
`dotf secrets verify`.

**After `make post`, `make sold` or `make reprice`** the command asks once whether to update
`/seller/` now. Yes asks for your current passphrase, seals, sets both secrets and dispatches
that deploy; Enter alone does not make a new passphrase (it aborts and says to run
`make ci-secrets`). No, the default, does nothing more. To skip the typing, run the command
under dotf, which puts the passphrase in the environment of that one command:
`dotf secrets run --only SELLER_PASSPHRASE -- make sold ID=sofa-sleeper PRICE=180`. The target
reads the environment under that name only, checks it like a typed passphrase, never prints it and
removes it from the environment of the programs it starts. It cannot tell dotf from a variable you
set by hand, so it still requires a terminal.

**Staleness.** The phone shows the data as of the last `make ci-secrets` and deploy (it says
when it was sealed). A recording made on the laptop does not reach the phone until the next seal
and deploy. Check the "as of" line before trusting a floor.

**Rotation.** To change the passphrase, run `make ci-secrets` again (without `dotf secrets run`)
and press Enter: it generates a new one and overwrites both the `SELLER_SEALED` secret and the
Bitwarden field `SELLER_PASSPHRASE`. A Pages
deployment keeps the envelope it was built with, and an old envelope still opens with the old
passphrase, so after a rotation or a passphrase you believe is known: delete the earlier Pages
deployments in the dashboard (Workers & Pages > `leaving-denver` > Deployments), and keep only
the new one. Rotate the same way if the secret itself leaks.

**Decommission after 2026-11-09.** After the car is handed over (the car deadline, `seller.vehicle_deadline`, is the latest), deploy the end page
(`seller.sale_over: true`) and pass the live checks in [decommission.md](decommission.md). Then delete the
earlier Pages deployments and the Access application for `/seller`, and only then delete the `SELLER_SEALED`
secret from both environments (`gh secret delete SELLER_SEALED --env production`, and `--env preview`).
Do not redeploy afterwards: the deploy job needs the secrets until the end page is live.

**Owner checks (cannot be run from CI).**

- The served CSP. After an Access login, `curl -sI -H "cf-access-token: ..." https://leaving-denver.pages.dev/seller/`
  (or the browser's network tab) must show `content-security-policy` with `script-src 'self'`,
  `connect-src 'none'` and `frame-ancestors 'none'`. Record the result in
  `specs/FEAT-009-one-seller-tool/verification.md`.
- The unlock time on the phone, 3 s or less (AC11). Record it there too. Over 3 s, lower `iter`
  in ADR-007, never below 600,000.

## Inventory and contact

- **Sold:** `make sold ID=<item-id> PRICE=<realized-usd>` records the price and the
  sale date in `data/private.sops.yaml` (`sales.<item-id>` is `{price, at}`; a bare
  price from before still reads; needs sops and the age key; nothing changes if that
  fails), marks the item Sold in the YAML and rebuilds locally. The repository is
  public: a realized price never goes in `data/inventory.yaml`. Inspect the diff,
  commit and merge both `data/inventory.yaml` and `data/private.sops.yaml`, then verify
  the automatic deployment. `sold` lists the marketplaces the item was posted on; take
  those listings down by hand.
- **Tracking:** `make post`, `make reprice` and the private views of `/seller/` are in the
  [seller playbook](seller-playbook.md#the-private-views); their data is encrypted in
  `data/private.sops.yaml` (ADR-006) and reaches the phone only as the sealed envelope.
- **Reserved:** `uv run leaving-denver pending <item-id>` when a buyer agrees a
  pickup: the card shows "Pending pickup" and its bundles go off sale. If the
  pickup falls through, `uv run leaving-denver available <item-id>` puts it
  back. Commit and merge either change like a sale.
- **Price:** edit the item's `recommended_list_price` in
  `data/inventory.yaml`; run `make check`, inspect the diff, commit and merge,
  then verify the automatic deployment. Never put reserve floors in public inventory.
  `recommended_list_price` is the item's one asking price (the build refuses a
  `current_asking`); the "% off" badge and the catalog order follow from it and
  `original_price`.
- **Condition, flaws, size:** `condition` is one of New, Used - Like New, Used - Good,
  Used - Fair (the car keeps its own wording); the Spanish label comes from
  `locales/es.yaml`. List a known flaw under `flaws:` with the same number of lines
  under `es: flaws:`; with none known leave it out. Add `size_in: [w, d, h]` only as
  the owner's own numbers from `dimensions` (as the buyer carries it: omit it for
  things that roll or fold), and `weight_lb` plus `weight_source` only for a weighed
  item. Over 48 in or 50 lb shows "Needs truck/SUV"; over 75 lb also "2-person lift".
- **Phone spam:** get a Google Voice number (#29) and test it first. Run
  `make secrets` to change `seller.phone` in `data/private.sops.yaml`, then
  `make ci-secrets` from a machine with the age key and an admin `gh`: it copies the
  phone into the `SELLER_PHONE` secret of both environments. Commit only the encrypted
  file and merge. If `make ci-secrets` ran after the merge, redeploy with
  `gh workflow run ci.yml --ref main -f branch=main`: a deploy uses the secret as it
  was when it started. Then test the SMS CTA on the live site and update marketplace
  listings. Push CI uses a placeholder phone, so its green check does not validate the
  production contact.
- **New machine:** install `sops`, `uv`, Git LFS and `gh`, then restore the age key from
  its offline backup: dotfiles `docs/runbooks/guide-secrets-governance.md`, RECOVER
  step 1. `.sops.yaml` names the recipient the key must match. sops does not look where
  that guide puts the key unless `SOPS_AGE_KEY_FILE` points at it (the dotfiles
  setup persists it; otherwise export it yourself). Confirm access without printing the
  phone: `sops -d --extract '["seller"]["phone"]' data/private.sops.yaml >/dev/null`.
  If decryption fails, stop; never replace the encrypted file or publish with an
  unverified phone. Then `gh auth login`, and run `make ci-secrets` only if the CI
  secrets need refreshing.

## Link previews

- Each item has a share page, `https://leaving-denver.pages.dev/i/<item-id>/`
  (Spanish: `/es/i/<item-id>/`). Share that link rather than the catalog's: its
  preview shows the item's photo, price and status, and it opens the item.
- Platforms cache a preview. After a price or status change, paste the item's link into
  Facebook's Sharing Debugger (`https://developers.facebook.com/tools/debug/`) and
  press "Scrape Again". Messenger and Marketplace use the same cache. X and Telegram
  refresh by themselves within days.
- A preview showing the catalog instead of the item means the crawler reached `/`:
  check that the share page's `og:url` is its own address and that nothing
  redirects it on the server.

## Minimal monitoring

Repo side, nothing to do:

- `scripts/smoke.sh` runs in CI after every deploy: against the `candidate` deployment
  before production moves, then against the canonical site. A red deploy job means
  production did not move, or is wrong: read the run, fix forward or roll back (above).
- `make audit-deploy` reads the live settings: both environments, their single `main`
  branch policy, and (with the owner's `gh`) no deploy secret left at the repository
  level. The `deploy-audit` workflow runs the settings part weekly.

Owner setup (dashboards; this repository cannot enable either). Both are in place since
2026-10-01:

- **Uptime.** An Uptime Kuma monitor on the owner's homelab (kubelab), type
  "HTTP(s) - Keyword", every 300 s, alerting to Telegram.
  - URL: `https://leaving-denver.pages.dev/`.
  - Keyword: `Denver Tech Center Relocation Sale`. That is the page title; an error page
    or a Pages 5xx does not carry it.
  - To rebuild the monitor, set the same fields and press the notification's Test.
  - The monitor lives on the homelab, so a homelab outage silences it. That is accepted:
    the deploy smoke already guards the likelier failure, a bad deploy.
  - On an alert, run `scripts/smoke.sh https://leaving-denver.pages.dev`, check Cloudflare
    Pages status, and roll back if a deploy caused it.
- **Web Analytics.** Enabled in Workers & Pages > `leaving-denver` > Metrics > Web Analytics
  (ADR-005: the repo ships no beacon, and no CSP blocks it).
  - Pages injects the beacon only from the next deployment on. On 2026-10-01 a production
    redeploy (`gh workflow run ci.yml --ref main -f branch=main`) was needed before it
    appeared.
  - Verify with `curl -s https://leaving-denver.pages.dev/ | grep -c cloudflareinsights`
    and a test visit that shows in the dashboard.
  - Share distinct campaign links, e.g. `?utm_source=nextdoor&utm_campaign=moving-sale` (the
    seller tool builds them). Check whether the dashboard reports channel attribution
    before relying on UTMs; otherwise use its referrer data.
  - Do not put personal data in URL parameters.

## End of the sale

The sale has two deadlines: household items by Oct 23 (the unsold ones come off the catalog that day) and the car by Nov 9. Once the car is handed over, and no later than Nov 9, the site becomes one "the sale is over" page; the steps, and what to remove by Nov 15, are in the [decommission runbook](decommission.md).
