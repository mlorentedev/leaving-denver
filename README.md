# Leaving Denver — Moving Sale Automation Platform

A privacy-focused inventory management, automated photo ingestion, and multi-portal liquidation system designed for an international relocation sale in Denver Tech Center (DTC / 80111), Colorado.

---

## Key Features

- **Single Source of Truth (`data/inventory.yaml`):** Human-readable YAML configuration managing all 14 items, value bundles, pricing tiers, and descriptions.
- **Folder-Convention Media Pipeline:** Drop any photo (including iPhone HEIC) into `content/photos/<item_id>/` and run `./manage.py build` to auto-discover, strip GPS EXIF metadata, optimize (<300 KB), and compile.
- **Data & Privacy Isolation:** Public build in `dist/` is completely stripped of internal reserve floor prices, negotiation notes, and seller admin tools.
- **Bot & Scraper Defense:** Telephone numbers are obfuscated and assembled dynamically via client JS. Static HTML attributes contain no harvestable numbers. `robots.txt` enforces `Disallow: /`.
- **Hormozi 3-Week Staging Bar:** Toggles between Week 1 (List / $12,213), Week 2 (Drop / 12% off), and Week 3 (Liquidation floor).
- **Multi-Portal Copy Generator:** Instant copy-paste listings tailored for Facebook Marketplace, Craigslist Denver, OfferUp, and Nextdoor.
- **Kubelab Integration:** Ready-to-import n8n workflows for Telegram push alerts, Vikunja task creation, and 48-hour Craigslist bump reminders.

---

## Quickstart

### 1. Requirements
- Python 3.10+
- `ffmpeg` (for iPhone HEIC conversion)
- `git-lfs`, and `sops` + an age key for the private data
- Python packages: `pip install pyyaml pillow pytest`

### 2. Common Commands

```bash
# Compile SSOT, process new photos, build public & private sites
./manage.py build

# Auto-discover photos and update data/inventory.yaml
./manage.py sync

# View Hormozi 3-week staged pricing drops
./manage.py drops

# Mark an item as sold and trigger automatic site rebuild
./manage.py sold sofa-sleeper 200

# Start local preview server (Port 8088)
./manage.py serve --port 8088

# Deploy public site to Cloudflare Pages (100% free)
./manage.py deploy-cf --project-name leaving-denver

# Run test suite
./manage.py test
```

---

## Private Seller Data

Reserve floors and the seller phone never live in plaintext in this repo. They are
in `data/private.sops.yaml`, encrypted with [sops](https://github.com/getsops/sops)
to the canonical dotfiles age key (see `.sops.yaml`). On a new machine, restore the key per the dotfiles secrets runbook and clone this repo.

```bash
sops data/private.sops.yaml          # edit floors / phone
```

- The **public build** only needs the phone: from `SELLER_PHONE` (CI secret) or the sops file.
- The **private workspace** and `./manage.py drops` need the floors, so they only work where the file decrypts.
- Photos under `content/photos/` are stored with Git LFS (`git lfs install --local --skip-repo`).

---

## Accessing Local Workspaces

When running `./manage.py serve`:
- **Public Minimalist Catalog:** `http://localhost:8088/`
- **Private Seller Workspace (PIN-gated, local only):** `http://localhost:8088/poster_assistant.html`

---

## Project Structure

```text
├── data/
│   ├── inventory.yaml             # SSOT (Item specifications, pricing, bundles)
│   └── inventory.json             # Internal compiled inventory with floor prices
├── content/
│   └── photos/                    # Drop photos here by item ID
├── src/
│   ├── config.py                  # Core configuration & secrets
│   ├── image_processor.py         # HEIC decoder & EXIF metadata scrubber
│   ├── site_builder.py            # Site compiler with leak detection
│   └── n8n_integration.py         # Kubelab webhook integration
├── dist/                          # Public sanitized distribution (Deploy to Cloudflare)
├── dist_private/                  # Private seller workspace with PIN lock
├── n8n/                           # Kubelab n8n workflows (Telegram, Vikunja, Reminders)
├── docs/                          # Architecture, Playbooks, and Kubelab guide
├── tests/                         # Integrity & security regression tests
└── manage.py                      # Master orchestration CLI
```

---

## Testing & Quality Assurance

Run the test suite to verify SSOT integrity and security boundaries:

```bash
pytest tests/
```
