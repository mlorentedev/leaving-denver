---
id: "lesson-redact-scanned-documents-on-pixels"
type: lesson
scope: local
tags: [privacy, documents, images, redaction]
created: "2026-09-26"
source: "Publishing the vehicle's recall invoice and emissions report"
---

# Lesson: Redact Scanned Documents on the Pixels, Then Re-Encode

## Context (The Problem/Error)
The vehicle listing gains trust from two paper records: a dealer recall invoice and a state
emissions report. Both carry personal data (owner name, phone, email, customer and invoice
numbers, service advisor, plate, report id and barcode). The title and registration carry even
more and are never published, redacted or not: their layout, numbers and barcodes are raw
material for title fraud. They are shown in person at the sale.

## The Finding (Root Cause/Solution)
A black box drawn in a PDF editor hides text only on screen. A scan run through OCR keeps a text
layer under the box, and copy-paste or `pdftotext` reads it back. So:

1. Check the source with `pdffonts` (no fonts) and `pdfimages -list` (one image per page). That
   means it is image-only, with no text layer.
2. Rasterize with `pdftoppm`, paint the boxes on the pixels, and save a new JPEG. Fresh pixels
   carry no EXIF and no text layer. The build re-encodes again and strips EXIF.
3. Put any caveat on the image itself. The emissions report says it was already used for the
   renewal. A sale in Colorado needs a certificate not used for a registration, so the image
   must not pass for the one the buyer gets.
4. Keep the redaction script, and its coordinates, out of the repo. They describe private
   documents.

The VIN stays visible: it is already public in `data/inventory.yaml`, and buyers need it for a
history report.

## Anti-Pattern (What NOT to do)
Publishing the original PDF with annotations on top. Git LFS objects in a public repo cannot be
taken back, so a leak there is permanent.

Also avoid naming a document so it sorts before the photos. The build takes the first file by
name as the cover (BUG-002), which is why these are `doc_*`.
