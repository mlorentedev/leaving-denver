# Decommission runbook: end of the sale

The seller leaves Denver on 2026-11-09. The site must not outlive the sale with a phone number
behind it: that number would keep drawing spam and scam messages nobody can answer. Two steps,
in this order. Spec: `specs/OPS-011-end-of-sale/`. The Pages project stays (ADR-008).

Run every command from a clone of the repository, in a shell where `gh` is logged in as the
owner. Nothing here prints a secret.

## Before Nov 8: rehearse the end deploy on a preview

The candidate smoke runs before production moves, and it fails if Cloudflare Pages does not
answer `/i/*` with the 302 while `functions/_middleware.js` is present. Find that out a week
early, not on the day. A dispatched preview builds `main`, where the switch is off, so rehearse
from this machine. It needs the age key, and it must happen before the token is revoked:

```
sed -i '0,/^seller:/s//seller:\n  sale_over: true/' data/inventory.yaml   # not committed
make deploy BRANCH=preview                                # never main: the live site is untouched
scripts/smoke.sh https://preview.leaving-denver.pages.dev # smoke OK (sale over)
git checkout data/inventory.yaml
```

This was proven once, on 2026-10-01: an end build deployed with `make deploy
BRANCH=endsale-rehearsal` answered `/` and `/es/` with 200, `/i/sofa-sleeper/` with a 302 to `/`,
`/es/i/sofa-sleeper/` with a 302 to `/es/` and `/seller/` with a 302 to the Access login, and
the smoke printed `smoke OK (sale over)`. The deployment was deleted afterwards. Repeat it a
week before Nov 8 anyway: Pages, the middleware or the Access app may have changed since.

If the smoke reports an old share link that does not redirect, `_redirects` is not applied
there: fix that before Nov 8 (a redirect in the middleware, or a `functions/i` route). Do not
flip the switch on a failing rehearsal. Delete the rehearsal deployment when done (Nov 8, step 4).

## Nov 8: turn the sale off

The deploy job refuses to run without the `SELLER_PHONE` secret (and, while the sale is on,
without `SELLER_SEALED`; the switch lifts that one), so the secrets stay in place until the end
page is live. Deleting them first would leave the catalog up and make the deploy
that replaces it fail.

1. Flip the switch on a branch and see the gate pass. The end build needs no phone and no key:

   ```
   git switch -c chore/end-the-sale main
   sed -i '0,/^seller:/s//seller:\n  sale_over: true/' data/inventory.yaml
   git diff data/inventory.yaml   # one added line under seller:
   make check
   ```

   `make check` skips the catalog's tests by name while the switch is on (`tests/conftest.py`).
   A skipped list that is out of date shows up here, not in production.

2. Merge it through a pull request, as for any change to `main`:

   ```
   git commit -am "feat: end the sale"
   git push -u origin chore/end-the-sale
   gh pr create --fill
   ```

   After the owner merges, the push to `main` deploys. Watch it:
   `gh run list --workflow ci.yml --event push --branch main --limit 1`, then
   `gh run watch <run-id> --exit-status`. The candidate smoke and the canonical smoke both
   recognise the end page and also check that `/i/*` and `/es/i/*` answer with a 302.

3. Check the live site yourself:

   ```
   scripts/smoke.sh https://leaving-denver.pages.dev      # smoke OK (sale over)
   curl -s https://leaving-denver.pages.dev/ | grep -ciE '\b(sms|tel):'   # 0
   curl -sI https://leaving-denver.pages.dev/i/sofa-sleeper/ | head -3    # 302, Location: /
   ```

4. Delete the old deployments. Each deploy keeps its own URL, and the old ones still serve the
   catalog and the phone fragments. Cloudflare dashboard > Workers & Pages > `leaving-denver` >
   Deployments: for every deployment except the current production one, open its menu and choose
   Delete deployment. Do this before the API token is revoked in the next section, and
   include the `candidate` and `preview` branch deployments.

5. Take down every listing, and the flyer. Each one points here and shows the phone:
   - Facebook Marketplace: Marketplace > Your listings > each listing > Delete listing.
   - Craigslist: your account page > each posting > delete.
   - OfferUp: Profile > My items > each item > Remove.
   - Nextdoor: For Sale & Free > My listings > each listing > Delete.
   - ActiveBuilding (the complex portal): remove the post.
   - The building flyer: take the paper down; its QR code now opens the end page.

   Where each item was posted is the `tracking` section of the encrypted file: `make secrets`
   opens it in your editor (it needs the age key; close without changing anything). `/seller/`
   shows the same until the end page replaces it, so read it there first if you can. The
   `make sold` takedown list names the channels an item was posted on, too.

6. Pause the uptime monitor (ops.md, "Minimal monitoring"). Its keyword was the catalog title,
   which the end page does not carry, so it alerts from its next check. Uptime Kuma on the
   homelab > the `leaving-denver` monitor > Pause (or Delete).

7. Optional: platforms cache link previews for about 30 days. To show "The sale is over" sooner,
   paste `https://leaving-denver.pages.dev/` into the Facebook Sharing Debugger
   (`https://developers.facebook.com/tools/debug/`) and press Scrape Again.

## By Nov 15: remove the credentials and the number

Only after step 3 of Nov 8 passed. From here the CI deploy cannot run again: it needs
`SELLER_PHONE` and the token. The deployed end page keeps serving. A later change to it needs a
new token (ADR-008).

1. Delete the GitHub secrets, in both environments. A name that was never set is only reported:

   ```
   for environment in production preview; do
     for name in CLOUDFLARE_API_TOKEN SELLER_PHONE SELLER_SEALED; do
       gh secret delete "$name" --env "$environment" || echo "$name: not set in $environment"
     done
   done
   ```

   The PR-review key is a repository secret, not an environment one
   (`.github/workflows/pr-agent.yml`): `gh secret delete NAN_API_KEY`, and revoke the key where
   it was issued.

   `CLOUDFLARE_ACCOUNT_ID` is not a secret anywhere: it is the literal `CF_ACCOUNT_ID` in the
   `Makefile` and `accountId` in `.github/workflows/ci.yml`. There is nothing to delete.
   An account id alone grants nothing.

2. Revoke the Cloudflare API token. Cloudflare dashboard > My Profile > API Tokens > the
   Pages deploy token > Delete (or Roll, then discard). The encrypted copy in
   `data/private.sops.yaml` is dead from then on.

3. Keep the Pages project. Do not delete it: ADR-008 says why.

4. Optional: remove the Access app. Zero Trust dashboard (`one.dash.cloudflare.com`) > Access >
   Applications > the `leaving-denver` app for `/seller` > Delete. Workers & Pages >
   `leaving-denver` > Settings > Variables and Secrets: delete `ACCESS_TEAM_DOMAIN` and
   `ACCESS_AUD` in production and preview. `/seller/` is no longer built, so this is tidying.

5. Release the Google Voice number. voice.google.com > Settings > Account > the Google Voice
   number > Delete. Do it after the listings are gone, so no reply lands on a dead number.

6. Delete the Bitwarden item `leaving-denver-seller`, which holds `SELLER_PASSPHRASE`, and
   remove the `SELLER_PASSPHRASE` entry from the dotfiles secrets registry with a dotfiles pull
   request (the registry is described in dotfiles `docs/runbooks/guide-secrets-governance.md`),
   so nothing keeps asking for a secret that no longer exists:

   ```
   export BW_SESSION="$(bw unlock --raw)"            # the session key stays out of the terminal
   bw list items --search leaving-denver-seller | jq -r '.[] | .id + "  " + .name'   # ids only, never the item JSON
   bw delete item <id> --permanent
   unset BW_SESSION
   ```

7. Drop the local backup of the pre-public history, in every clone that has it:

   ```
   git update-ref -d refs/backup/pre-public-main
   ```

8. Archive the repository. Do it last: an archived repository cannot change its secrets or run
   workflows.

   ```
   gh repo archive mlorentedev/leaving-denver --yes
   ```

### Done when

All of these hold, run from a clone before the archive step (the secrets checks need it):

```
# No secret is left, in either environment or at the repository level.
for environment in production preview; do
  test -z "$(gh secret list --env "$environment")" && echo "$environment: no secrets"
done
test -z "$(gh secret list)" && echo "repository: no secrets"

# No phone is served, on any address that still answers.
for host in leaving-denver candidate.leaving-denver preview.leaving-denver; do
  for page in / /es/ /seller/; do
    curl -s "https://$host.pages.dev$page" | grep -ciE '\b(sms|tel):|const _C' || true   # 0 each
  done
done

make audit-deploy        # deploy audit OK
scripts/smoke.sh https://leaving-denver.pages.dev   # smoke OK (sale over)
```

Then the manual ones: the Google Voice number is gone, the token is gone from My Profile > API
Tokens, and no marketplace listing is left (search each site for the item titles).
