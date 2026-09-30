# Leaving Denver — Moving Sale Automation Platform

A privacy-focused inventory management, automated photo ingestion, and multi-portal liquidation system designed for an international relocation sale in Denver Tech Center (DTC / 80111), Colorado.

---

## Key Features

- **Single Source of Truth (`data/inventory.yaml`):** Human-readable YAML configuration managing all 14 items, value bundles, pricing tiers, and descriptions.
- **Folder-Convention Media Pipeline:** Drop any photo (including iPhone HEIC) into `content/photos/<item_id>/` and run `leaving-denver build` to auto-discover, strip GPS EXIF metadata, optimize (<300 KB), and compile.
- **Data & Privacy Isolation:** Public build in `build/public/` is completely stripped of internal reserve floor prices, negotiation notes, and seller admin tools.
- **Bot & Scraper Defense:** Telephone numbers are obfuscated and assembled dynamically via client JS. Static HTML attributes contain no harvestable numbers. `robots.txt` enforces `Disallow: /`.
- **Departure-Date Pricing Schedule:** `leaving-denver drops` derives the active drop, floor, and giveaway windows from `seller.departure_date`; prices come from the inventory and encrypted reserve data.
- **Multi-Portal Copy Generator:** Instant copy-paste listings tailored for Facebook Marketplace, Craigslist Denver, OfferUp, and Nextdoor.
- **Bilingual Catalog:** The same sanitized inventory renders in English at `/` and neutral Latin American Spanish at `/es/`, with localized SMS intents.
- **Kubelab Integration:** Ready-to-import n8n workflows for Telegram push alerts, Vikunja task creation, and 48-hour Craigslist bump reminders.

---

## Quickstart

### 1. Requirements
- Python 3.12+ and [`uv`](https://github.com/astral-sh/uv)
- Node.js 24+ and npm (locked Tailwind v4 CLI; CSS is built locally, not loaded from a runtime CDN)
- `ffmpeg` (for iPhone HEIC conversion)
- `git-lfs`, and `sops` + an age key for the private data
- `make install` (`uv sync --extra dev` and `npm ci`) installs locked deps and the `leaving-denver` CLI

### 2. Common Commands

```bash
# Compile SSOT, process new photos, build public & private sites
uv run leaving-denver build

# Auto-discover photos and update data/inventory.yaml
uv run leaving-denver sync

# View date-derived schedule windows and inventory/reserve-based price tiers
uv run leaving-denver drops

# Mark an item as sold and trigger automatic site rebuild
uv run leaving-denver sold sofa-sleeper 200

# Start local preview server (Port 8088)
uv run leaving-denver serve --port 8088

# Lint, build and test (what CI runs)
make check
```

`make build` and direct `leaving-denver build` compile separate Tailwind CSS
stylesheets into `build/public/styles.css` (shared by EN/ES) and
`build/private/styles.css` (local only). Run `make install` first: a missing
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
- The **private workspace** and `uv run leaving-denver drops` need the floors, so they only work where the file decrypts.
- Photos under `content/photos/` are stored with Git LFS (`git lfs install --local --skip-repo`).

---

## Accessing Local Workspaces

When running `uv run leaving-denver serve`:
- **Public Minimalist Catalog:** `http://127.0.0.1:8088/`
- **Spanish Public Catalog:** `http://127.0.0.1:8088/es/`
- **Private Seller Workspace (local only):** `http://127.0.0.1:8088/poster_assistant.html`. `make serve` binds loopback only and refuses paths outside `build/`. The PIN screen is a UI gate against shoulder-surfing, not access control: the PIN is in the page's JavaScript and the tool is never deployed.

---

## Project Structure

```text
├── data/
│   ├── inventory.yaml             # SSOT (Item specifications, pricing, bundles)
│   └── inventory.json             # Internal compiled inventory with floor prices
├── content/
│   └── photos/                    # Drop photos here by item ID
├── locales/                       # English and Spanish public UI strings
├── src/
│   └── leaving_denver/
│       ├── cli.py                 # Master orchestration CLI
│       ├── config.py              # Core configuration & secrets
│       ├── image_processor.py     # HEIC decoder & EXIF metadata scrubber
│       ├── site_builder.py        # Site compiler with leak detection
│       └── n8n_integration.py     # Kubelab webhook integration
├── build/
│   ├── public/                    # Public sanitized distribution (Deploy to Cloudflare)
│   └── private/                   # Private seller workspace with PIN lock
├── integrations/
│   └── n8n/                       # Kubelab n8n workflows (Telegram, Vikunja, Reminders)
├── docs/                          # Architecture, Playbooks, and Kubelab guide
└── tests/                         # Integrity & security regression tests
```

---

## Testing & Quality Assurance

Run the test suite to verify SSOT integrity and security boundaries:

```bash
uv run pytest
```
