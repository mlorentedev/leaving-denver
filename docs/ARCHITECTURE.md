# Leaving Denver Platform — System Architecture & Data Flow

This project implements an automated, privacy-first inventory management and sales platform for a 3-week international relocation moving sale in Denver Tech Center (DTC / 80111), Colorado.

---

## 1. Architectural Philosophy

1. **Single Source of Truth (SSOT):**  
   The file `data/inventory.yaml` is the sole authoritative definition of all 14 items, bundled packages, retail pricing, recommended list prices, and internal firm floor prices.
2. **Folder-Convention Media Ingestion:**  
   Dropping an image (JPEG, PNG, WebP, or iPhone HEIC) into `content/photos/<item_id>/` auto-triggers discovery, format conversion, EXIF scrubbing, and registration into the SSOT.
3. **Strict Security Isolation:**  
   Public assets (`dist/`) and private seller tools (`dist_private/`) are physically decoupled. Firm reserve floor prices and seller negotiation tools are never compiled into the public deployment.

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
│   ├── config.py                  <-- Paths, quality standards, obfuscation secrets
│   ├── image_processor.py         <-- Auto-discovery, HEIC decode, EXIF scrubber
│   ├── site_builder.py            <-- Compiles public/private sites & verifies leaks
│   └── n8n_integration.py         <-- Webhook dispatcher for kubelab stack
├── dist/                          <-- 100% Sanitized Public Build (Cloudflare Pages)
│   ├── index.html                 <-- 46KB high-speed catalog
│   ├── robots.txt                 <-- Disallow: / crawler blocker
│   └── catalog/                   <-- Optimized, EXIF-scrubbed images (<300KB each)
├── dist_private/                  <-- Private Local Seller Workspace (gitignored)
│   ├── poster_assistant.html      <-- Multi-portal copy generator (FB/CL/OfferUp/Nextdoor)
│   └── inventory.json             <-- Private inventory with floor prices
├── n8n/                           <-- Kubelab integration workflows
│   └── workflows/
├── docs/                          <-- Architecture & seller playbooks
├── tests/                         <-- Pytest regression suite
└── manage.py                      <-- Master orchestration CLI
```

---

## 3. Threat Model & Privacy Engineering

### Threat A: Reverse Engineering Reserve Floors (`firm_floor_price`)
* **Mitigation:** `site_builder.py` invokes `sanitize_public_inventory()`. All `firm_floor_price` attributes and negotiation notes are dropped before building `dist/index.html`. Automated tests in `tests/test_security_isolation.py` assert zero occurrences of `firm_floor_price` in `dist/`.

### Threat B: Web Scraping & Robocall Harvesting
* **Mitigation 1 (Robots):** `dist/robots.txt` specifies `User-agent: * \n Disallow: /` and `dist/index.html` has `<meta name="robots" content="noindex, nofollow, noarchive, nosnippet">`.
* **Mitigation 2 (DOM Obfuscation):** Telephone numbers do not exist as plaintext strings in static HTML attributes (`href="sms:..."`). The phone number is assembled in memory at runtime via client JavaScript upon user interaction.

### Threat C: Physical Location & GPS Metadata (EXIF Scrubbing)
* **Mitigation:** `src/image_processor.py` opens raw images via Pillow, transforms them into fresh RGB buffers, and saves progressive JPEGs without preserving EXIF metadata. Precise apartment numbers are omitted from the catalog; physical address is shared only via private SMS upon scheduled appointment.
