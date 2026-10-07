# Leaving Denver Platform — System Architecture & Data Flow

This project implements an automated, privacy-first inventory management and sales platform for an international relocation moving sale in Denver Tech Center (DTC / 80111), Colorado. The sale has two deadlines, household items and the car, and the household price schedule is written down in the seller's `price_schedule`.

---

## 1. Architectural Philosophy

1. **Single Source of Truth (SSOT):**  
   The file `data/inventory.yaml` is the authoritative definition of all 14 items, bundled packages, public copy, retail pricing, and recommended list prices. Internal firm floor prices, targets, sales, tracking and notes are sourced only from encrypted `data/private.sops.yaml`; the build never reads that file (ADR-007).
2. **Folder-Convention Media Ingestion:**  
   Dropping an image (JPEG, PNG, WebP, or iPhone HEIC) into `content/photos/<item_id>/` auto-triggers discovery, format conversion and EXIF scrubbing at build time. The build only reads the SSOT; `leaving-denver sync` is what writes the discovered photo paths into `data/inventory.yaml`, editing only the `primary_image:` and `images:` lines of the items whose photos changed (comments and layout stay).
3. **Strict Security Isolation:**  
   There is one build output, `build/public/`, and no private one. Firm reserve floor prices and the rest of the owner's private data are never compiled into it in the clear: they travel as one AES-256-GCM envelope, sealed on the owner's machine under a passphrase (ADR-007), held in the `SELLER_SEALED` CI secret, embedded in `/seller/index.html` only, and opened in the phone's browser. `/seller/` is also behind Cloudflare Access and carries its own CSP (`script-src 'self'`, `connect-src 'none'`).

---

## 2. Directory Layout & Data Flow

```text
leaving-denver/
├── data/
│   ├── inventory.yaml             <-- SSOT (Human-editable YAML)
│   ├── private.sops.yaml          <-- Encrypted floors, targets, tracking, phone (ADR-006, ADR-007)
│   └── seller-replies.yaml        <-- Scam-reply texts shown at /seller/
├── locales/                       <-- en.yaml, es.yaml, flyer.yaml, not_found.yaml
├── functions/
│   └── _middleware.js             <-- Pages Function: Access on /seller/*, its CSP, end-of-sale redirects
├── content/
│   └── photos/                    <-- Photo Drop (folder per item ID)
│       ├── sofa-sleeper/
│       ├── 2019-ford-escape-sel-awd/
│       └── ...
├── src/
│   └── leaving_denver/
│       ├── cli.py                 <-- Master orchestration CLI
│       ├── config.py              <-- Paths, quality standards, obfuscation secrets
│       ├── pricing.py             <-- Staged price tiers
│       ├── private_data.py        <-- Reads and writes the encrypted private file through sops
│       ├── image_processor.py     <-- Auto-discovery, HEIC decode, EXIF scrubber, JPEG + WebP variants
│       ├── seal.py                <-- `leaving-denver seal`: seals the private data, sets SELLER_SEALED
│       ├── channels.py            <-- Listing channels and renewal rules (shared by the CLI and the page)
│       └── site_builder.py        <-- Compiles the public site & verifies leaks
├── build/
│   ├── public/                    <-- 100% Sanitized Public Build (Cloudflare Pages)
│   │   ├── index.html, es/index.html  <-- Generated public catalog, English and Spanish
│   │   ├── i/<id>/, es/i/<id>/    <-- Per-item share pages (Open Graph tags)
│   │   ├── flyer/                 <-- The building flyer, printed from a browser
│   │   ├── robots.txt             <-- Allow-list: link-preview fetchers and assistants, every other crawler disallowed
│   │   ├── catalog/               <-- EXIF-scrubbed JPEGs (capped at 1600 px) plus WebP width variants
│   │   └── seller/index.html      <-- Seller tool: public copy tools, plus the sealed envelope (ciphertext)
├── infra/
│   └── terraform/cloudflare/      <-- Pages project and Access as Terraform; local, gitignored state (ADR-012)
├── integrations/
│   └── n8n/                       <-- Kubelab integration workflows
│       └── workflows/
├── docs/
│   ├── adr/                       <-- Architecture decision records
│   ├── lessons/                   <-- Lessons learned
│   └── runbooks/                  <-- Ops, seller playbook, vehicle sale, decommission, Kubelab guide
└── tests/                         <-- Pytest regression suite
```

---

## 3. Threat Model & Privacy Engineering

### Threat A: Reverse Engineering Reserve Floors (`firm_floor_price`)
* **Mitigation:** `site_builder.py` invokes `sanitize_public_inventory()`. All `firm_floor_price` attributes and negotiation notes are dropped before building `build/public/index.html`. Automated tests in `tests/test_security_isolation.py` assert zero occurrences of `firm_floor_price` in `build/public/`. The page is rendered with Jinja2 (ADR-003) from the sanitized dict only; `test_template_sees_only_sanitized_data` plants private fields in the data and asserts none reaches the template context.

### Threat A2: The Private Data Reaching the Phone (ADR-007)
* **Mitigation:** the data is sealed with Node WebCrypto (PBKDF2-SHA256, 1,000,000 iterations, AES-256-GCM, the header as additional data) under a five-word passphrase; the seal needs a terminal and writes no file. The builder refuses a malformed envelope, one with fewer than 600,000 iterations or over 40,000 bytes, and `verify_security_guarantees` fails the build if the envelope or any plaintext marker is outside `seller/index.html`. The page opens it in the browser, drops the key at once, touches no storage API and clears the DOM on Lock and on leaving. What it does not defend: the owner's passphrase, and a phone that is already compromised. A leaked envelope is brute-forced offline, so the passphrase floor is the only protection; rotate as the ops runbook says.

### Threat B: Web Scraping & Robocall Harvesting
* **Mitigation 1 (Robots):** `build/public/robots.txt` is an allow-list. It allows link-preview fetchers (`facebookexternalhit`, `Facebot`, `Twitterbot`, `TelegramBot`, `WhatsApp`; ADR-004) and the assistants a person asked to read a page (`ChatGPT-User`, `Claude-User`, `Perplexity-User`, `MistralAI-User`; ADR-009), and ends with `User-agent: *` / `Disallow: /` for every other crawler. `/seller/` is not named in it. Every response carries `X-Robots-Tag: noindex` (`_headers`) and `build/public/index.html` has `<meta name="robots" content="noindex, nofollow, noarchive, nosnippet">`.
* **Mitigation 2 (DOM Obfuscation):** Telephone numbers do not exist as plaintext strings in static HTML attributes (`href="sms:..."`). The phone number is assembled in memory at runtime via client JavaScript upon user interaction.

### Threat C: Physical Location & GPS Metadata (EXIF Scrubbing)
* **Mitigation:** `src/leaving_denver/image_processor.py` opens raw images via Pillow, transforms them into fresh RGB buffers, and saves optimized JPEGs (capped at 1600 px, quality 85) and WebP width variants without preserving EXIF metadata. Precise apartment numbers are omitted from the catalog; physical address is shared only via private SMS upon scheduled appointment.
