"""Shared guards for the whole suite."""

import pytest
import yaml

from leaving_denver import config, private_data


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


# The end of the sale (OPS-011). With `seller.sale_over: true` committed, `make check` builds one
# page and no catalog, so the tests that read the catalog's live build have nothing to read. They
# are skipped by name, never silently: a new catalog test fails on the day the switch flips, in
# the PR that flips it, and joins this list there. The decommission runbook says to run
# `make check` with the switch on before pushing it.
CATALOG_MODULES = frozenset(
    f"test_{name}.py"
    for name in (
        "build_contract",
        "catalog_flows_browser",
        "copy_vin_browser",
        "desktop_contact",
        "inventory_ssot",
        "item_sheet_browser",
        "item_sheet_detail",
        "item_status",
        "mobile_poster",
        "native_dialogs",
        "responsive_images",
        "richer_item_fields",
        "richer_item_fields_browser",
        "seller_browser",
        "seller_copy",
        "seller_layout_browser",
        "share_button_browser",
        "verify_sheet_browser",
        "verify_the_car",
    )
)
CATALOG_TESTS = frozenset(
    {
        "test_end_of_sale.py::test_the_switch_is_off_until_the_owner_ends_the_sale",
        "test_browser_harness_portability.py::test_the_first_command_waits_for_chrome_to_start",
        "test_ops_runbook.py::test_the_uptime_keyword_is_on_the_page_the_monitor_fetches",
        "test_security_isolation.py::test_template_sees_only_sanitized_data",
        "test_smoke_script.py::test_a_path_that_is_not_ready_yet_is_retried",
    }
)


def sale_is_over() -> bool:
    data = yaml.safe_load(config.INVENTORY_YAML.read_text(encoding="utf-8"))
    return data["seller"].get("sale_over") is True


def pytest_collection_modifyitems(items):
    if not sale_is_over():
        return
    skip = pytest.mark.skip(reason="seller.sale_over is on: the catalog is not built")
    for item in items:
        module = item.path.name
        if module in CATALOG_MODULES or f"{module}::{item.originalname}" in CATALOG_TESTS:
            item.add_marker(skip)
