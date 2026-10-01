# Leaving Denver Platform — System Architecture & Data Flow

This project implements an automated, privacy-first inventory management and sales platform for an international relocation moving sale in Denver Tech Center (DTC / 80111), Colorado. The sale schedule is derived from the seller's `departure_date`.

---

## 1. Architectural Philosophy

1. **Single Source of Truth (SSOT):**  
   The file `data/inventory.yaml` is the authoritative definition of all 14 items, bundled packages, public copy, retail pricing, and recommended list prices. Internal firm floor prices are sourced only from encrypted `data/private.sops.yaml`; the build generates ignored private copies in `data/inventory.json` and `build/private/inventory.json`.
2. **Folder-Convention Media Ingestion:**  
   Dropping an image (JPEG, PNG, WebP, or iPhone HEIC) into `content/photos/<item_id>/` auto-triggers discovery, format conversion, EXIF scrubbing, and registration into the SSOT.
3. **Strict Security Isolation:**  
   Public assets (`build/public/`) and private seller tools (`build/private/`) are physically decoupled. Firm reserve floor prices and seller negotiation tools are never compiled into the public deployment.

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
│       └── site_builder.py        <-- Compiles public/private sites & verifies leaks
├── build/
│   ├── public/                    <-- 100% Sanitized Public Build (Cloudflare Pages)
│   │   ├── index.html             <-- Generated public catalog
│   │   ├── robots.txt             <-- Disallow: / crawler blocker
│   │   └── catalog/               <-- Optimized, EXIF-scrubbed images (<300KB each)
│   └── private/                   <-- Private Local Seller Workspace (gitignored)
│       ├── poster_assistant.html  <-- Multi-portal copy generator (FB/CL/OfferUp/Nextdoor)
│       └── inventory.json         <-- Private inventory with floor prices
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

### Threat B: Web Scraping & Robocall Harvesting
* **Mitigation 1 (Robots):** `build/public/robots.txt` specifies `User-agent: * \n Disallow: /` and `build/public/index.html` has `<meta name="robots" content="noindex, nofollow, noarchive, nosnippet">`.
* **Mitigation 2 (DOM Obfuscation):** Telephone numbers do not exist as plaintext strings in static HTML attributes (`href="sms:..."`). The phone number is assembled in memory at runtime via client JavaScript upon user interaction.

### Threat C: Physical Location & GPS Metadata (EXIF Scrubbing)
* **Mitigation:** `src/image_processor.py` opens raw images via Pillow, transforms them into fresh RGB buffers, and saves progressive JPEGs without preserving EXIF metadata. Precise apartment numbers are omitted from the catalog; physical address is shared only via private SMS upon scheduled appointment.
