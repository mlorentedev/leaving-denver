"""Shared guards for the whole suite."""

import shutil

import pytest
import yaml

from leaving_denver import config, private_data, seal, site_builder


@pytest.fixture(autouse=True)
def never_write_the_owners_private_file(monkeypatch):
    """No test may change data/private.sops.yaml.

    `sold` without a price once reached the real `sops set` from a test that stubbed everything
    else, and wrote a bogus sale into the owner's encrypted file. A test that records anything
    points `private_data.PRIVATE_SOPS_YAML` at a file of its own, or stubs the recorder."""
    real = private_data.set_private

    def guarded(keys, value):
        if private_data.PRIVATE_SOPS_YAML.resolve() == config.PRIVATE_SOPS_YAML.resolve():
            pytest.fail(f"a test tried to write {keys} into the real data/private.sops.yaml")
        return real(keys, value)

    monkeypatch.setattr(private_data, "set_private", guarded)


@pytest.fixture(autouse=True)
def no_test_asks_a_terminal_or_reaches_the_real_gh(monkeypatch):
    """`pytest -s` in a terminal must not hang on a prompt, and no test may set a secret or
    dispatch a deploy on the real repository, or write to the owner's Bitwarden.

    The terminal is off unless a test turns it on, and `gh` runs only when PATH resolves it to
    a fake (tests/sealed_helpers.install_fakes puts one in a `fake-bin` directory)."""
    real = seal.gh

    def guarded(*args, **kwargs):
        found = shutil.which("gh") or ""
        if "fake-bin" not in found:
            pytest.fail(f"a test reached the real gh: gh {' '.join(args[:2])}")
        return real(*args, **kwargs)

    real_dotf = seal.run_dotf

    def guarded_dotf(*args, **kwargs):
        if "fake-bin" not in (shutil.which("dotf") or ""):
            pytest.fail("a test reached the real dotf")
        return real_dotf(*args, **kwargs)

    monkeypatch.setattr(seal, "has_tty", lambda: False)
    monkeypatch.setattr(seal, "gh", guarded)
    # The owner's real dotf (and so their Bitwarden) is never seen: only a fake in fake-bin is.
    monkeypatch.setattr(seal, "have_dotf", lambda: "fake-bin" in (shutil.which("dotf") or ""))
    monkeypatch.setattr(seal, "run_dotf", guarded_dotf)


# The end of the sale (OPS-011). With `seller.sale_over: true` committed, `make check` builds one
# page and no catalog, so the tests that read the catalog's live output (build/public/index.html,
# its share pages, /seller/) have nothing to read. They are skipped one by one, never by module:
# a module also holds tests that still apply (the Access guard on /seller/*, the phone and the
# realized price staying out of the public data), and a test added later must not be silenced
# with them. A new catalog test fails on the day the switch flips, in the PR that flips it, and
# joins this list there. The decommission runbook says to run `make check` with the switch on
# before pushing it.
CATALOG_TESTS = {
    "test_end_of_sale.py": ("test_the_switch_is_off_until_the_owner_ends_the_sale",),
    "test_browser_harness_portability.py": ("test_the_first_command_waits_for_chrome_to_start",),
    "test_catalog_flows_browser.py": (
        "test_a_drag_from_the_panel_onto_the_backdrop_keeps_the_sheet",
        "test_a_linked_item_opens_and_drops_the_hash",
        "test_a_press_on_the_backdrop_closes_the_sheet",
        "test_a_refused_clipboard_selects_the_number",
        "test_a_reload_with_a_sheet_open_leaves_no_stale_entry",
        "test_a_sheet_opened_twice_owns_one_history_entry",
        "test_a_text_link_on_a_touch_screen_keeps_the_native_hand_off",
        "test_a_text_link_with_a_mouse_opens_the_contact_sheet",
        "test_an_item_text_link_carries_its_message_into_the_contact_sheet",
        "test_an_unknown_linked_item_opens_nothing",
        "test_back_closes_a_contact_sheet_over_an_item_one_level_at_a_time",
        "test_back_closes_the_sheet_and_stays_on_the_catalog",
        "test_escape_closes_a_contact_sheet_over_an_item_one_level",
        "test_escape_closes_the_sheet_and_its_history_entry",
        "test_the_close_button_closes_the_sheet_and_its_history_entry",
        "test_the_close_button_of_other_sheets_closes_them",
        "test_the_contact_sheets_own_link_hands_off_to_messages",
    ),
    "test_copy_vin_browser.py": (
        "test_the_copy_button_puts_the_vin_on_the_clipboard",
        "test_without_a_clipboard_the_vin_is_selected_to_copy_by_hand",
    ),
    "test_desktop_contact.py": (
        "test_contact_sheet_ships_empty",
        "test_filtering_announces_the_result_count",
        "test_fine_pointer_text_links_open_the_contact_sheet",
        "test_sheet_keeps_a_native_sms_way_out",
        "test_sticky_bar_clears_the_home_indicator",
    ),
    # Reads the live /flyer/, which an end build does not make (the scratch builds in test_flyer.py
    # keep running).
    "test_flyer_browser.py": (
        "test_the_flyer_fits_the_letter_content_box",
        "test_the_flyer_prints_on_exactly_one_letter_sheet",
    ),
    "test_photo_gallery_browser.py": (
        "test_a_mouse_press_released_off_the_photo_leaves_no_swipe_behind",
        "test_a_real_press_on_an_arrow_steps_once",
        "test_a_sideways_swipe_steps_and_a_vertical_drag_does_not",
        "test_an_item_with_one_photo_shows_no_arrows",
        "test_reopening_starts_at_the_first_photo",
        "test_the_arrow_keys_step_through_the_photos",
        "test_the_arrows_step_and_wrap",
    ),
    "test_inventory_ssot.py": (
        "test_no_stale_or_unbacked_pickup_facts",
        "test_no_unbacked_vehicle_claims",
    ),
    "test_item_cta_browser.py": ("test_the_button_and_text_say_what_the_buyer_wants",),
    "test_item_sheet_browser.py": ("test_the_sheet_shows_the_whole_item",),
    "test_item_sheet_detail.py": (
        "test_every_item_publishes_all_its_specs_and_what_is_included",
        "test_the_car_has_more_specs_than_its_card_shows",
        "test_the_footer_holds_only_the_credit_and_the_build",
        "test_the_included_list_has_a_heading",
        "test_the_sheet_renders_every_spec_the_details_and_the_included_list",
        "test_the_spanish_sheet_has_spanish_details",
    ),
    "test_native_dialogs.py": (
        "test_backdrop_close_needs_a_press_on_the_backdrop",
        "test_every_sheet_is_a_labelled_dialog",
        "test_sheets_open_modally_and_back_closes_them",
    ),
    "test_ops_runbook.py": ("test_the_uptime_keyword_is_on_the_page_the_monitor_fetches",),
    "test_responsive_images.py": (
        "test_a_dpr3_phone_never_falls_back_to_the_hero_jpeg",
        "test_cards_ask_for_half_a_phone_screen",
        "test_every_catalog_img_is_responsive",
        "test_item_dialog_uses_srcset",
        "test_phone_downloads_a_third_of_the_full_covers",
        "test_the_budget_catches_a_card_sized_to_the_viewport",
        "test_vehicle_hero_loads_first",
    ),
    "test_richer_item_fields.py": (
        "test_every_real_item_shows_its_own_discount_on_the_card",
        "test_the_page_shows_the_scale_label_in_its_language",
        "test_the_published_price_is_the_one_in_the_data",
        "test_the_real_big_items_say_so",
        "test_the_real_grid_runs_from_cheap_to_dear_with_sold_last",
        "test_the_sheet_template_lists_flaws_as_text_and_hides_the_empty_list",
    ),
    "test_richer_item_fields_browser.py": ("test_the_sheet_shows_badges_and_flaws_from_the_data",),
    "test_seller_browser.py": (
        "test_a_count_turns_red_when_an_edit_passes_the_platform_limit",
        "test_choosing_a_spanish_channel_rewrites_the_listing_in_spanish",
        "test_every_channel_renders_for_every_item_without_an_error",
        "test_every_copy_button_copies_what_is_on_screen",
        "test_the_counters_the_creator_link_and_the_tags_follow_the_choice",
    ),
    "test_seller_copy.py": (
        "test_craigslist_replies_through_its_relay_and_chat_channels_through_chat",
        "test_each_channel_gets_its_own_attribution_and_the_link_stays_out_of_the_listing",
        "test_each_channel_opens_its_listing_creator_and_the_car_the_vehicle_one",
        "test_every_listing_fits_its_platform_without_cutting_anything",
        "test_every_listing_says_no_holds_and_no_deposits",
        "test_household_copy_takes_the_catalogs_payment_wording",
        "test_six_scam_replies_each_have_english_and_spanish_with_copy_buttons",
        "test_the_car_copy_is_vehicle_copy_not_furniture_copy",
        "test_the_cars_copy_names_the_bank_payments_from_the_data_on_every_channel",
        "test_the_copy_carries_the_price_digits_tags_and_the_full_listing",
        "test_the_copy_is_singular_plain_and_phone_free",
        "test_the_english_channels_stay_english",
        "test_the_origin_the_page_links_to_is_the_builders",
        "test_the_replies_come_from_the_data_with_the_car_payment_filled_in",
        "test_the_spanish_channels_write_the_listing_from_the_spanish_overlay",
        "test_the_spanish_overlay_is_complete_for_every_listable_item",
    ),
    "test_seller_layout_browser.py": ("test_the_seller_page_keeps_a_gutter_on_a_phone",),
    "test_share_button_browser.py": (
        "test_a_cancelled_share_sheet_does_nothing",
        "test_a_failed_share_copies_the_link",
        "test_a_refused_clipboard_shows_the_link_selected",
        "test_no_clipboard_at_all_shows_the_link",
        "test_reopening_for_another_item_resets_the_button",
        "test_the_spanish_page_shares_the_spanish_share_page",
    ),
    "test_smoke_script.py": (
        "test_a_path_that_is_not_ready_yet_is_retried",
        # A positive control for the catalog's smoke path (the end smoke needs the redirects a
        # static stub cannot serve); the leak test beside it still runs in both modes.
        "test_a_redirect_in_front_of_the_seller_page_passes_the_smoke",
        "test_robots_txt_served_as_the_catalog_is_retried",
        "test_robots_txt_that_stays_the_catalog_fails_as_such",
        # The catalog smoke path (the 404 body, the og:image cover); the end smoke never reaches it.
        "test_a_404_with_another_body_first_is_retried",
        "test_a_page_still_naming_a_deleted_cover_is_fetched_again",
        "test_a_cover_that_stays_missing_fails",
    ),
    "test_verify_sheet_browser.py": (
        "test_a_press_on_the_backdrop_closes_the_sheet",
        "test_back_closes_the_sheet_and_stays_on_the_catalog",
        "test_escape_closes_the_sheet_and_its_history_entry",
        "test_the_button_opens_the_sheet_with_the_vin_and_the_three_official_links",
        "test_the_cars_deep_link_still_opens_the_item_sheet_and_not_the_verify_sheet",
        "test_the_close_button_closes_the_sheet_and_its_history_entry",
        "test_the_sheet_can_be_reopened_after_closing",
    ),
    "test_verify_the_car.py": (
        "test_every_link_is_https_on_an_official_host_or_one_of_the_cars_photos",
        "test_evidence_links_to_photos_the_car_has_and_the_build_ships",
        "test_the_car_card_offers_only_specs_and_verify",
        "test_the_checks_open_from_a_button_on_the_car_card_and_are_not_inline",
        "test_the_emissions_note_says_passed_already_used_and_a_new_test_is_coming",
        "test_the_section_claims_no_service_history_and_shows_no_personal_data",
        "test_the_section_shows_the_vin_and_the_three_official_hosts",
        "test_the_share_page_still_sends_buyers_to_the_car",
    ),
}
# Names that look like they guard the phone or private data and are skipped all the same, each with
# the reason nothing is lost. The end build's own guarantees are in test_end_of_sale.py.
SKIPPED_DESPITE_ITS_NAME = {
    "test_responsive_images.py::test_a_dpr3_phone_never_falls_back_to_the_hero_jpeg": "a phone screen",
    "test_responsive_images.py::test_cards_ask_for_half_a_phone_screen": "a phone screen",
    "test_responsive_images.py::test_phone_downloads_a_third_of_the_full_covers": "a phone screen",
    "test_seller_layout_browser.py::test_the_seller_page_keeps_a_gutter_on_a_phone": "a phone screen",
    "test_seller_copy.py::test_the_copy_is_singular_plain_and_phone_free": "reads /seller/, not built",
}


def sale_is_over() -> bool:
    data = yaml.safe_load(config.INVENTORY_YAML.read_text(encoding="utf-8"))
    return data["seller"].get("sale_over") is True


def pytest_collection_modifyitems(items):
    if not sale_is_over():
        return
    skip = pytest.mark.skip(reason="seller.sale_over is on: the catalog is not built")
    for item in items:
        if item.originalname in CATALOG_TESTS.get(item.path.name, ()):
            item.add_marker(skip)


@pytest.fixture(autouse=True)
def tests_build_the_catalog_whatever_the_committed_switch_says(monkeypatch):
    """A test that builds a scratch site from the committed inventory means the catalog, and the
    switch (`seller.sale_over`) must not turn it into the end page when the owner commits it on.
    Only the real file is read this way: a test's own inventory file keeps its switch."""
    real = site_builder.load_inventory_yaml

    def load():
        data = real()
        if site_builder.INVENTORY_YAML.resolve() == config.INVENTORY_YAML.resolve():
            data["seller"].pop("sale_over", None)
        return data

    monkeypatch.setattr(site_builder, "load_inventory_yaml", load)
