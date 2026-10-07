# Leaving Denver — Moving Sale Automation Platform

A privacy-focused inventory management, automated photo ingestion, and multi-portal liquidation system designed for an international relocation sale in Denver Tech Center (DTC / 80111), Colorado.

---

## Key Features

- **Single Source of Truth (`data/inventory.yaml`):** Human-readable YAML configuration managing all 14 items, value bundles, pricing tiers, and descriptions.
- **Folder-Convention Media Pipeline:** Drop any photo (including iPhone HEIC) into `content/photos/<item_id>/` and run `leaving-denver build` to auto-discover, strip GPS EXIF metadata and compile. Each photo becomes one JPEG capped at 1600 px on its longer side (quality 85) plus WebP copies at 480, 800, 1200 and 1600 px wide that the page's `srcset` picks from (never upscaled); a photo whose source and settings have not changed is skipped.
- **Data & Privacy Isolation:** Public build in `build/public/` is completely stripped of internal reserve floor prices, negotiation notes, and seller admin tools.
- **Bot & Scraper Defense:** Telephone numbers are obfuscated and assembled dynamically via client JS. Static HTML attributes contain no harvestable numbers. `robots.txt` disallows every crawler except link-preview fetchers (Facebook, X, Telegram, WhatsApp; ADR-004) and the assistants a person asked to read a page (ChatGPT-User, Claude-User, Perplexity-User, MistralAI-User; ADR-009); every response also carries `X-Robots-Tag: noindex`.
- **Two Deadlines and a Written-Down Price Schedule (seller-only, never shown publicly):** household items go by `seller.household_deadline` and the car by `seller.vehicle_deadline`; no public page, the flyer or a listing shows either date (FEAT-014), they only drive the seller tool, the price windows and the end-of-sale switch; `leaving-denver drops` prints the drop, floor and giveaway windows from `seller.price_schedule`, and prices come from the inventory and encrypted reserve data.
- **Multi-Portal Copy Generator:** Instant copy-paste listings tailored for Facebook Marketplace, Craigslist Denver, OfferUp, Nextdoor and the car's vehicle form, written at `/seller/`. The complex portal (ActiveBuilding) is tracked as a channel too.
- **Bilingual Catalog:** The same sanitized inventory renders in English at `/` and neutral Latin American Spanish at `/es/`, with localized SMS intents.
- **Craigslist Bump Reminder:** A ready-to-import n8n workflow that sends a Telegram reminder to renew listings every 48 hours.

---

## Quickstart

### 1. Requirements
- Python 3.12+ and [`uv`](https://github.com/astral-sh/uv)
- Node.js 24+ and npm (locked Tailwind v4 CLI; CSS is built locally, not loaded from a runtime CDN)
- `ffmpeg` (for iPhone HEIC conversion)
- `git-lfs`, and `sops` + an age key for the private data
- [Terraform](https://developer.hashicorp.com/terraform/install) 1.9+ (optional: only for `make infra-*`; `make check` skips its part without it)
- `make install` (`uv sync --extra dev` and `npm ci`) installs locked deps and the `leaving-denver` CLI

### 2. Common Commands

```bash
# Compile SSOT, process new photos, build the public site (one output: build/public/)
uv run leaving-denver build

# Auto-discover photos and update data/inventory.yaml
uv run leaving-denver sync

# View the written price windows (seller.price_schedule) and inventory/reserve-based price tiers
uv run leaving-denver drops

# Mark an item as sold and trigger automatic site rebuild
uv run leaving-denver sold sofa-sleeper 200

# Reserve an item for an agreed pickup, or put it back on sale
uv run leaving-denver pending sofa-sleeper
uv run leaving-denver available sofa-sleeper

# Record a posting or renewal, and an asking-price change (written to the encrypted private file)
make post ID=sofa-sleeper CHANNEL=facebook   # channels: facebook, craigslist, offerup, nextdoor, activebuilding, carscom (the car only)
make reprice ID=sofa-sleeper PRICE=190

# Seal the private data for /seller/ and set SELLER_SEALED (needs a terminal)
uv run leaving-denver seal

# Edit the encrypted floors, targets, notes, phone and deploy token
make secrets

# Start local preview server (Port 8088)
uv run leaving-denver serve --port 8088

# Lint, build and test (what CI runs)
make check
```

`make build` and direct `leaving-denver build` compile the Tailwind CSS stylesheet
`build/public/styles.css` (shared by EN/ES and `/seller/`). Run `make install` first: a missing
Tailwind CLI fails the build instead of silently shipping stale or unstyled HTML.
Only `build/public/` is uploaded to Pages.

### 3. Deploy (Cloudflare Pages)

Every push to `main` automatically publishes the live site **after** the CI
tests pass. Pull requests only run tests. For a manual preview (or an explicit
production redeploy), use *Actions → ci → Run workflow* with a `branch` input:
`main` publishes production when dispatched from `main`; any other name
(default `preview`) creates `<branch>.leaving-denver.pages.dev`. The deploy
job rebuilds with the real phone, runs `make check`, deploys with wrangler
and smoke-tests the deployment (`scripts/smoke.sh`).
The bilingual footer links the developer's GitHub profile and, on CI builds,
the deployed commit (`GITHUB_SHA`) so the live version is identifiable.

One-time setup, all idempotent and run from a machine with the age key:

```bash
make cf-project     # create the Pages project if missing
make protect-main   # require the CI `test` check on main
make ci-secrets     # restrict both deploy environments to main, scope the token, set the phone
```

The deploy token (Cloudflare Pages: Edit, this account only) lives in
`data/private.sops.yaml` as `cloudflare_pages_token`; the account id is
`CF_ACCOUNT_ID` in the Makefile (Pages' `wrangler.toml` rejects it). The token
is stored in the `production` and `preview` GitHub environments, **not** as a
repository-wide secret. Both environments accept deployments only from `main`;
manual previews select a Pages branch while running the trusted workflow from
`main`. Re-run `make ci-secrets` after rotating the token. `make deploy
BRANCH=<name>` deploys from this machine as a fallback.
The Pages project and the Cloudflare Access application in front of `/seller/` are Terraform in
`infra/terraform/cloudflare/` (local, gitignored state; ADR-012): `make infra-plan`, read it,
`make infra-apply`. `make infra-fmt` (format and validate, no credentials) runs as part of
`make check` when `terraform` is installed. Setup, the first import and what stays manual are in
[site operations](docs/runbooks/ops.md#cloudflare-configuration-terraform).

For rollbacks, inventory and phone changes, key recovery, and monitoring, see
[site operations](docs/runbooks/ops.md).
For the listing calendar, platform rules and buyer scripts, see the
[seller playbook](docs/runbooks/seller-playbook.md).

---

## Private Seller Data

Reserve floors and the seller phone never live in plaintext in this repo. They are
in `data/private.sops.yaml`, encrypted with [sops](https://github.com/getsops/sops)
to the canonical dotfiles age key (see `.sops.yaml`). On a new machine, restore the key per the dotfiles secrets runbook and clone this repo.

```bash
sops data/private.sops.yaml          # edit floors / phone
```

- The **public build** only needs the phone: from `SELLER_PHONE` (CI secret) or the sops file.
- `uv run leaving-denver drops` and `uv run leaving-denver seal` need the floors, so they only work where the file decrypts. The deployed `/seller/` gets them only as the `SELLER_SEALED` ciphertext (ADR-007).
- Photos under `content/photos/` are stored with Git LFS (`git lfs install --local --skip-repo`).

---

## Accessing Local Workspaces

When running `uv run leaving-denver serve`:
- **Public Minimalist Catalog:** `http://127.0.0.1:8088/`
- **Spanish Public Catalog:** `http://127.0.0.1:8088/es/`
- **Seller tool:** `http://127.0.0.1:8088/seller/`. `make serve` binds loopback only and refuses paths outside `build/public/`. Built without `SELLER_SEALED` it shows the public copy tools only; the private views need the sealed envelope and its passphrase (see [site operations](docs/runbooks/ops.md#the-sealed-private-data-seller_sealed)).
- **Mobile seller listing copy:** `https://leaving-denver.pages.dev/seller/` after owner-only Cloudflare Access is configured and tested. Its private views open only with the sealed envelope's passphrase; missing Access configuration fails closed. Follow [site operations](docs/runbooks/ops.md#owner-only-mobile-listing-copy-cloudflare-access) before using or sharing the URL.

---

## Project Structure

```text
├── data/
│   ├── inventory.yaml             # SSOT (Item specifications, pricing, bundles)
│   ├── private.sops.yaml          # Encrypted floors, targets, tracking, phone (sops + age)
│   └── seller-replies.yaml        # Scam-reply texts shown at /seller/
├── content/
│   └── photos/                    # Drop photos here by item ID
├── locales/                       # Public UI strings: en.yaml, es.yaml, flyer.yaml, not_found.yaml
├── functions/
│   └── _middleware.js             # Pages Function: Cloudflare Access on /seller/*, its CSP, the end-of-sale redirects
├── src/
│   └── leaving_denver/
│       ├── cli.py                 # Master orchestration CLI
│       ├── config.py              # Core configuration & secrets
│       ├── channels.py            # Listing channels, takedown steps and renewal rules
│       ├── pricing.py             # Staged price tiers
│       ├── private_data.py        # Reads and writes the encrypted private file through sops
│       ├── seal.py                # `seal`: encrypts the private data for /seller/
│       ├── image_processor.py     # HEIC decoder, EXIF metadata scrubber, JPEG + WebP variants
│       └── site_builder.py        # Site compiler with leak detection
├── build/
│   └── public/                    # Public sanitized distribution (Deploy to Cloudflare):
│       │                          #   catalog (/, /es/), item share pages (/i/<id>/, /es/i/<id>/),
│       │                          #   the building flyer (/flyer/) and the seller tool (/seller/)
├── infra/
│   └── terraform/cloudflare/      # Pages project and Access as Terraform (ADR-012); state is local
├── integrations/
│   └── n8n/                       # Kubelab n8n workflow (Craigslist bump reminder); the digest lives in kubelab
├── docs/
│   ├── adr/                       # Architecture decision records
│   ├── lessons/                   # Lessons learned
│   └── runbooks/                  # Ops, seller playbook, vehicle sale, decommission, Kubelab guide
└── tests/                         # Integrity & security regression tests
```

---

## Maintenance mode

The build phase is over; what is left is running the sale and closing it:

- [site operations](docs/runbooks/ops.md): marking items sold, pending or available again, repricing,
  recording a posting (`make sold`, `uv run leaving-denver pending`, `make reprice`, `make post`),
  deploys, rollbacks and key recovery.
- [decommission](docs/runbooks/decommission.md): the end of the sale, dated: the household
  close-out on Oct 23, turning the sale off by Nov 9 and removing the credentials and the number.
- [vehicle sale](docs/runbooks/vehicle-sale.md): screening, test drive, payment (a cashier's
  check at the buyer's bank, no deposit) and the Colorado paperwork for the car.

---

## Testing & Quality Assurance

Run the test suite to verify SSOT integrity and security boundaries:

```bash
uv run pytest
```
