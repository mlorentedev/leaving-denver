# Site operations

The catalog deploys automatically on tested pushes to `main`. The public inventory lives in
`data/inventory.yaml`; encrypted phone, reserve floors, and deployment token
live in `data/private.sops.yaml`. Only `build/public/` is published.
On a fresh checkout, install Node.js 24+, npm, and `uv`, then run `make install`
before `make check` or direct `uv run leaving-denver build`. Builds compile
Tailwind CSS locally from pinned npm dependencies; if the CLI is missing, stop
and run `npm ci` rather than publishing old assets. Verify `/styles.css` loads
for both `/` and `/es/`; the private assistant's stylesheet remains under
`build/private/` and is never uploaded to Pages.

Before merging CD, run `make protect-main` and `make ci-secrets` from a machine
with the age key. This restricts both GitHub deployment environments to the
`main` workflow ref, moves the Cloudflare token out of repository-wide secrets,
and refreshes the contact secret. Verify the environments still allow only
`main` after changing deployment settings. A branch workflow must never receive
a production-capable Pages token, even for a preview. `make protect-deploy`
removes any stale extra branch or tag policies as well as ensuring the `main`
branch policy exists.

## Deploy and roll back

1. Merge the intended change into `main`. The push tests and automatically
   deploys production only if the test job passes. PR runs never deploy.
2. Find the run with `gh run list --workflow ci.yml --event push --branch main --limit 3`,
   then use `gh run watch <run-id> --exit-status`. For a manual preview, dispatch
   `gh workflow run ci.yml --ref main -f branch=preview`; to redeploy production
   explicitly, use `gh workflow run ci.yml --ref main -f branch=main`. The deploy job
   rebuilds with the real `SELLER_PHONE`, runs `make check`, publishes to Pages
   and invokes `scripts/smoke.sh` against the deployment URL.
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
or the local private assistant. There is no server-side AI endpoint or shared
JavaScript PIN: select an item and platform, then copy the editable title,
description, and UTM-attributed item link on a phone. Until Access is
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

The seller workspace at `build/private/` is **never** uploaded. Never put
floors, private drafts, or a plaintext PIN under `build/public/`, even behind
Access: disabling an edge policy must not disclose them. The buyer catalog
must stay reachable anonymously.

## Inventory and contact

- **Sold:** `uv run leaving-denver sold <item-id> <realized-usd>` records the
  price in `data/private.sops.yaml` (`sales.<item-id>`, needs sops and the age
  key; nothing changes if that fails), marks the item Sold in the YAML and
  rebuilds locally. The repository is public: a realized price never goes in
  `data/inventory.yaml`. Inspect the diff, commit and merge both
  `data/inventory.yaml` and `data/private.sops.yaml`, then verify the automatic deployment. Take down marketplace listings
  separately.
- **Reserved:** `uv run leaving-denver pending <item-id>` when a buyer agrees a
  pickup: the card shows "Pending pickup" and its bundles go off sale. If the
  pickup falls through, `uv run leaving-denver available <item-id>` puts it
  back. Commit and merge either change like a sale.
- **Price:** edit the item's `recommended_list_price` in
  `data/inventory.yaml`; run `make check`, inspect the diff, commit and merge,
  then verify the automatic deployment. Never put reserve floors in public inventory.
- **Phone spam:** obtain and test a Google Voice number first. Run
  `make secrets` to update `seller.phone` in `data/private.sops.yaml`. On a
  machine with the age key, run `make ci-secrets` **before** merging to refresh
  the `SELLER_PHONE` Actions secret; otherwise the automatic deployment uses
  the old phone. Commit only the encrypted file, merge, then verify the
  automatic deployment and test the SMS CTA. Update marketplace listings
  separately. Push CI uses a placeholder phone, so its green check alone
  does not validate the production contact.
- **New machine:** restore the canonical dotfiles age identity using dotfiles
  `docs/runbooks/guide-secrets-governance.md`. Install `sops`, `uv` and Git
  LFS; confirm access without printing the phone:
  `sops -d --extract '["seller"]["phone"]' data/private.sops.yaml >/dev/null`.
  If decryption fails, stop; never replace the encrypted file or publish with
  an unverified phone. Run `make ci-secrets` only if CI secrets need refreshing.

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

## Minimal monitoring (owner setup)

- Configure one free external HTTP monitor for
  `https://leaving-denver.pages.dev/`, alerting the owner's phone. Test the
  alert. On failure check Pages and run the smoke script; roll back if needed.
- Enable Cloudflare Web Analytics for the Pages project and verify a test visit
  appears. Share distinct campaign links, e.g.
  `?utm_source=nextdoor&utm_campaign=moving-sale`, and check whether the
  dashboard actually reports channel attribution before relying on UTMs;
  otherwise use its referrer data. Do not put personal data in URL parameters.

Neither the external monitor nor Analytics is enabled by this repository or
its CI; both dashboard steps require the owner to complete and verify them.
