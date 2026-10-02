# Leaving Denver Platform — System Architecture & Data Flow

This project implements an automated, privacy-first inventory management and sales platform for an international relocation moving sale in Denver Tech Center (DTC / 80111), Colorado. The sale has two deadlines, household items and the car, and the household price schedule is written down in the seller's `price_schedule`.

---

## 1. Architectural Philosophy

1. **Single Source of Truth (SSOT):**  
   The file `data/inventory.yaml` is the authoritative definition of all 14 items, bundled packages, public copy, retail pricing, and recommended list prices. Internal firm floor prices, targets, sales, tracking and notes are sourced only from encrypted `data/private.sops.yaml`; the build never reads that file (ADR-007).
2. **Folder-Convention Media Ingestion:**  
   Dropping an image (JPEG, PNG, WebP, or iPhone HEIC) into `content/photos/<item_id>/` auto-triggers discovery, format conversion, EXIF scrubbing, and registration into the SSOT.
3. **Strict Security Isolation:**  
   There is one build output, `build/public/`, and no private one. Firm reserve floor prices and the rest of the owner's private data are never compiled into it in the clear: they travel as one AES-256-GCM envelope, sealed on the owner's machine under a passphrase (ADR-007), held in the `SELLER_SEALED` CI secret, embedded in `/seller/index.html` only, and opened in the phone's browser. `/seller/` is also behind Cloudflare Access and carries its own CSP (`script-src 'self'`, `connect-src 'none'`).

---

## 2. Directory Layout & Data Flow

```text
leaving-denver/
├── data/
│   ├── inventory.yaml             <-- SSOT (Human-editable YAML)
│   └── inventory.json             <-- Internal compiled JSON (with floor prices)
├── content/
│   └── photos/                    <-- Photo Drop (folder per item ID)
│       ├── sofa-sleeper/
│       ├── 2019-ford-escape-sel-awd/
│       └── ...
├── src/
│   └── leaving_denver/
│       ├── cli.py                 <-- Master orchestration CLI
│       ├── config.py              <-- Paths, quality standards, obfuscation secrets
│       ├── image_processor.py     <-- Auto-discovery, HEIC decode, EXIF scrubber
│       ├── seal.py                <-- `leaving-denver seal`: seals the private data, sets SELLER_SEALED
│       ├── channels.py            <-- Listing channels and renewal rules (shared by the CLI and the page)
│       └── site_builder.py        <-- Compiles the public site & verifies leaks
├── build/
│   ├── public/                    <-- 100% Sanitized Public Build (Cloudflare Pages)
│   │   ├── index.html             <-- Generated public catalog
│   │   ├── robots.txt             <-- Disallow: / crawler blocker
│   │   └── catalog/               <-- Optimized, EXIF-scrubbed images (<300KB each)
│   └── seller/index.html          <-- Seller tool: public copy tools, plus the sealed envelope (ciphertext)
├── integrations/
│   └── n8n/                       <-- Kubelab integration workflows
│       └── workflows/
├── docs/                          <-- Architecture & seller playbooks
└── tests/                         <-- Pytest regression suite
```

---

## 3. Threat Model & Privacy Engineering

### Threat A: Reverse Engineering Reserve Floors (`firm_floor_price`)
* **Mitigation:** `site_builder.py` invokes `sanitize_public_inventory()`. All `firm_floor_price` attributes and negotiation notes are dropped before building `build/public/index.html`. Automated tests in `tests/test_security_isolation.py` assert zero occurrences of `firm_floor_price` in `build/public/`. The page is rendered with Jinja2 (ADR-003) from the sanitized dict only; `test_template_sees_only_sanitized_data` plants private fields in the data and asserts none reaches the template context.

### Threat A2: The Private Data Reaching the Phone (ADR-007)
* **Mitigation:** the data is sealed with Node WebCrypto (PBKDF2-SHA256, 1,000,000 iterations, AES-256-GCM, the header as additional data) under a five-word passphrase; the seal needs a terminal and writes no file. The builder refuses a malformed envelope, one with fewer than 600,000 iterations or over 40,000 bytes, and `verify_security_guarantees` fails the build if the envelope or any plaintext marker is outside `seller/index.html`. The page opens it in the browser, drops the key at once, touches no storage API and clears the DOM on Lock and on leaving. What it does not defend: the owner's passphrase, and a phone that is already compromised. A leaked envelope is brute-forced offline, so the passphrase floor is the only protection; rotate as the ops runbook says.

### Threat B: Web Scraping & Robocall Harvesting
* **Mitigation 1 (Robots):** `build/public/robots.txt` specifies `User-agent: * \n Disallow: /` and `build/public/index.html` has `<meta name="robots" content="noindex, nofollow, noarchive, nosnippet">`.
* **Mitigation 2 (DOM Obfuscation):** Telephone numbers do not exist as plaintext strings in static HTML attributes (`href="sms:..."`). The phone number is assembled in memory at runtime via client JavaScript upon user interaction.

### Threat C: Physical Location & GPS Metadata (EXIF Scrubbing)
* **Mitigation:** `src/image_processor.py` opens raw images via Pillow, transforms them into fresh RGB buffers, and saves progressive JPEGs without preserving EXIF metadata. Precise apartment numbers are omitted from the catalog; physical address is shared only via private SMS upon scheduled appointment.
