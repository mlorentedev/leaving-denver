---
tags: [spec, verification]
created: "2026-10-03"
---

# Verification - FEAT-015-sale-metrics

## Evidence

- [x] AC1 (validation) -> `tests/test_hit_function.py`: the shape (`test_a_visit_writes_one_data_point_and_answers_204`, `test_a_text_tap_carries_its_item_and_a_bundle_tap_its_bundle`), 13 bad bodies and an oversize one are 400 with no write, slug and source and locale normalization, a missing or throwing binding is a 204, only POST (405 otherwise). Mutation: widening the slug rule to `+` fails the 65-character case.
- [x] AC2 (nothing personal) -> `::test_nothing_of_the_request_is_read_but_its_body` (`headers` and `cf` are getters that record a read), `::test_extra_fields_are_never_stored`.
- [x] AC3 (the visit) -> `tests/test_metrics_beacon_browser.py::test_a_flyer_scan_sends_one_visit_and_leaves_no_utm_in_the_address`, `::test_only_the_utm_parameters_leave_the_address`, `::test_a_page_with_no_utm_sends_nothing_on_load`, `::test_a_reload_after_the_strip_is_not_a_second_visit`, `::test_the_spanish_page_says_so`.
- [x] AC4 (the taps) -> `::test_each_way_to_text_reports_one_tap_and_keeps_its_link` (five links, with and without a landing source: one tap, the right id, the `sms:` href unchanged, the click not cancelled), `::test_a_tap_on_a_desktop_is_one_count_and_the_contact_sheets_hand_off_is_not_another`. Mutation: counting the native hand-off fails the desktop test.
- [x] AC5 (the views) -> `::test_opening_an_item_is_a_view_with_the_landing_source`, `::test_an_unknown_item_is_not_a_view`, `::test_a_linked_item_is_a_view_with_the_source_of_the_landing`.
- [x] AC6 (ADR-002, CSP) -> `::test_no_payload_holds_the_phone_or_an_sms_uri` (the page's own number, in digits and in its parts, against five different taps), `::test_a_flyer_scan_reaches_the_endpoint_under_connect_src_self` (real `sendBeacon`, real HTTP, `connect-src 'self'`, no violation), `::test_the_check_notices_a_beacon_to_another_origin` (a `connect-src 'none'` control shows the violation; pointing the beacon at another host fails 18 tests), `tests/test_metrics_beacon.py` (one `sendBeacon`, to `/api/hit`; inline handlers may only go down from the 6 the page had; no other request API; `track()` names no contact data; no other template reports).
- [x] AC7 (share links) -> `::test_a_seller_tool_share_link_keeps_its_source_to_the_catalog` (`/i/<id>/?utm_source=facebook`, both languages, over HTTP: the server receives `visit` then `view_item`, both `facebook`), `tests/test_link_previews.py` (the template text).
- [x] AC8 (the binding) -> `tests/test_hit_function.py::test_the_binding_the_function_writes_to_is_declared_for_pages`, `::test_the_function_is_not_under_seller_and_the_middleware_lets_it_through`.
- [x] AC9 (the workflow) -> `tests/test_sale_metrics_workflow.py`: structure and chain, 08:00 America/Denver, SMTP node with `$env` addresses and no address in the file, named credentials only, no secret-shaped string or Telegram, no price or item or bundle id, account id and dataset equal to `Makefile` and `wrangler.toml`, a failed request does not stop the email, and the Code node run in Node on the rows `hit.js` writes (mapping parsed from the workflow's own SQL).
- [x] AC10 (docs) -> `docs/adr/adr-011-first-party-event-metrics-for-the-sale.md`, `docs/runbooks/ops.md` "Sale metrics", `docs/runbooks/kubelab-integration.md` section 3, `docs/runbooks/decommission.md` (By Nov 9 step 8, By Nov 15 step 2); `tests/test_sale_metrics_workflow.py::test_every_variable_and_credential_the_workflow_uses_is_in_the_runbooks` and the two after it.
- [x] AC11 (end of the sale) -> the new browser tests are in `CATALOG_TESTS` (and the one named for a phone has its reason in `SKIPPED_DESPITE_ITS_NAME`, which `tests/test_end_of_sale.py` demands).

## Test status

- `SELLER_PHONE=+13035550100 make check` -> exit 0, `1229 passed, 8 skipped` (after rebasing onto main at 4830507, #181 and #183 in), ruff clean.
- `make check` with `seller.sale_over: true` in a scratch edit of `data/inventory.yaml` (reverted with `git checkout data/inventory.yaml`) -> exit 0, `1008 passed, 229 skipped`. It first failed on tests of other changes that read the catalog and were missing from `CATALOG_TESTS` (`test_item_cta_browser.py`, `test_photo_gallery_browser.py`, three in `test_smoke_script.py`); the gallery ones were later added on main too, so only the smoke ones remain here.
- Under #181's policy: `test_the_beacon_fires_under_the_sites_real_content_security_policy` and `test_a_share_link_keeps_its_source_under_the_real_policy` serve the build with its real `_headers` Content-Security-Policy and a recording `/api/hit`; the events arrive and no violation or console error is logged. `tests/test_public_csp.py` passes with the beacon in the page.

## Not run here

- The Analytics Engine write, the SQL API, the Web Analytics GraphQL query and the SMTP send, against the live services. Bindings cannot be used locally and no deploy or Cloudflare resource is in scope; the owner's first-run steps are in `docs/runbooks/ops.md` "Sale metrics".

## Promotion candidates

- [x] Lesson for the repo's `docs/lessons/`? yes: docs/lessons/lesson-029-a-redirect-that-rebuilds-the-url-drops-the-query.md
- [x] ADR-worthy decision for the repo's `docs/adr/adr-XXX.md`? yes: docs/adr/adr-011-first-party-event-metrics-for-the-sale.md
- [x] New pattern candidate for `00_meta/patterns/`? no: first-party counting without personal data is specific to this sale's endpoint and ADR-002

## Independent review (2026-10-08)

The owner chose an independent reviewer subagent for these archives (the repo has no reviewer pool, so `dotf spec review` cannot run). The reviewer was not the implementer. It worked read-only on main at 077360f, checking each criterion against the code and the tests. The `features.json` commands were run again on 9659d65 before archiving, and all of them pass.

- Verdict: ready.
- AC1–AC8, AC10 and AC11 hold.
- AC9 is superseded. The digest workflow moved to kubelab (ADR-011 amendment, #228; kubelab#2090, #2095, #2106). This repo now keeps only the pointer, the runbooks and the `hit.js` ↔ SQL contract (`tests/test_sale_metrics_workflow.py`, 7 passed, 2 skipped without `KUBELAB_SALE_DIGEST_JSON`).
- Stale citations above: the AC9 and AC10 lines describe the in-repo workflow file, which no longer exists, and the test totals predate later PRs.
- Minor: `hit.js` reads the body before the `MAX_BODY` check. Cloudflare caps the body upstream, so this is theoretical. Ticketed in #238.
