"""
The private control panel (FEAT-004): one row per item from the inventory and the private data.

Every test runs against tests/fixtures/private.example.yaml, which holds fake numbers; the real
data/private.sops.yaml is never read here.
"""

import copy
import re
import stat
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from leaving_denver import cli, panel, pricing
from leaving_denver.config import PANEL_MARKER
from leaving_denver.site_builder import load_inventory_yaml, sale_schedule

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "private.example.yaml"
TODAY = date(2026, 10, 7)


@pytest.fixture
def private():
    return yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture
def inventory():
    return load_inventory_yaml()


def rows_by_id(inventory, private, today=TODAY):
    return {row["id"]: row for row in panel.panel_rows(inventory, private, today)}


def test_the_fixture_names_only_items_the_inventory_has(inventory, private):
    ids = {item["id"] for item in inventory["items"]}
    for section in ("floors", "targets", "sales", "tracking"):
        assert set(private[section]) <= ids, section


# AC2: one tier function for `drops` and the panel


@pytest.mark.parametrize(
    ("item", "floor", "tiers"),
    [
        # Household items round the midpoint to $5, the car to $100.
        ({"recommended_list_price": 220, "category": "Living Room"}, 173, (220, 195, 173)),
        ({"recommended_list_price": 11875, "category": "Vehicle"}, 10650, (11875, 11300, 10650)),
        # No floor on file: the list price stands in, as `drops` always did.
        ({"recommended_list_price": 55, "category": "Living Room"}, None, (55, 55, 55)),
        ({"category": "Living Room"}, None, (0, 0, 0)),
    ],
)
def test_price_tiers(item, floor, tiers):
    assert pricing.price_tiers(item, floor) == tiers


def test_drops_prints_the_tiers_price_tiers_computes(monkeypatch, capsys, inventory, private):
    monkeypatch.setattr(cli, "load_inventory_yaml", lambda: inventory)
    monkeypatch.setattr("leaving_denver.private_data.floors", lambda: private["floors"])
    cli.cmd_drops(None)
    out = capsys.readouterr().out
    assert re.search(r"sofa-sleeper\s+\$220\s+\$195\s+\$173", out)
    assert re.search(r"2019-ford-escape-sel-awd\s+\$11875\s+\$11300\s+\$10650", out)


# AC1: the ten fields


def test_a_row_carries_every_field_the_issue_asks_for(inventory, private):
    sofa = rows_by_id(inventory, private)["sofa-sleeper"]
    assert sofa["asking"] == 220
    assert sofa["target"] == 191
    assert sofa["floor"] == 173
    assert sofa["status"] == "Available"
    assert sofa["days_listed"] == 8
    assert [c["name"] for c in sofa["channels"]] == ["facebook", "craigslist"]
    assert sofa["renew_due"] == date(2026, 10, 13)
    # The log shows a reprice on 10-03, so the first drop is covered: see AC3 below.
    assert sofa["next_drop"]["price"] == 195


def test_there_is_one_row_per_item_in_inventory_order(inventory, private):
    rows = panel.panel_rows(inventory, private, TODAY)
    assert [r["id"] for r in rows] == [i["id"] for i in inventory["items"]]


def test_an_item_with_no_private_data_has_empty_fields_not_a_crash(inventory, private):
    desk = rows_by_id(inventory, private)["convertible-desk"]
    assert desk["target"] is None
    assert desk["days_listed"] is None
    assert desk["channels"] == []
    assert desk["renew_due"] is None
    assert desk["sale"] is None
    assert desk["price_log"] == []


def test_the_panel_renders_with_no_private_data_at_all(inventory):
    rows = panel.panel_rows(inventory, {}, TODAY)
    assert all(r["floor"] is None and r["target"] is None for r in rows)
    assert "<table" in panel.render_panel(rows, TODAY)


# AC3: the next drop


def with_item(inventory, item_id, **fields):
    data = copy.deepcopy(inventory)
    next(i for i in data["items"] if i["id"] == item_id).update(fields)
    return data


def with_log(private, item_id, *dates):
    data = copy.deepcopy(private)
    data["tracking"].setdefault(item_id, {})["price_log"] = [{"at": d, "price": 1} for d in dates]
    return data


def test_the_next_drop_steps_halfway_to_the_floor_at_the_first_drop_window(inventory, private):
    schedule = sale_schedule(inventory["seller"]["departure_date"])
    car = rows_by_id(inventory, private)["2019-ford-escape-sel-awd"]
    assert car["next_drop"] == {"on": schedule["first_drop"][0], "price": 11300, "overdue": True}


def test_a_window_the_price_log_already_covers_is_not_the_next_drop(inventory, private):
    # The sofa was repriced on 10-03, the day the first drop opened: the second drop is next.
    sofa = rows_by_id(inventory, private)["sofa-sleeper"]
    assert sofa["next_drop"] == {"on": date(2026, 10, 15), "price": 195, "overdue": False}


def test_each_drop_recomputes_from_the_asking_price_in_force(inventory, private):
    data = with_item(inventory, "sofa-sleeper", recommended_list_price=195)
    row = rows_by_id(data, private)["sofa-sleeper"]
    assert row["next_drop"]["price"] == 185  # halfway from 195 to the 173 floor, to the $5


def test_the_last_step_is_the_floor_at_the_clear_floors_window(inventory, private):
    schedule = sale_schedule(inventory["seller"]["departure_date"])
    data = with_log(private, "sofa-sleeper", "2026-10-03", "2026-10-15")
    row = rows_by_id(inventory, data)["sofa-sleeper"]
    assert row["next_drop"] == {"on": schedule["clear_floors"][0], "price": 173, "overdue": False}


def test_nothing_is_left_to_drop_once_every_window_is_covered(inventory, private):
    data = with_log(private, "sofa-sleeper", "2026-10-03", "2026-10-15", "2026-10-20")
    assert rows_by_id(inventory, data)["sofa-sleeper"]["next_drop"] is None


@pytest.mark.parametrize(
    ("item_id", "fields"),
    [
        ("air-mattress-twin-pump", {}),  # free with purchase
        ("coffee-table-lift-top", {}),  # no floor on file
        ("onn-43-4k-tv", {"status": "Sold"}),
        ("onn-43-4k-tv", {"status": "Pending"}),
        ("dell-monitor-32", {"recommended_list_price": 61}),  # already at the floor
    ],
)
def test_no_next_drop_when_there_is_nothing_to_drop(inventory, private, item_id, fields):
    data = with_item(inventory, item_id, **fields)
    assert rows_by_id(data, private)[item_id]["next_drop"] is None


def test_a_drop_whose_window_has_not_started_is_not_overdue(inventory, private):
    early = rows_by_id(inventory, private, today=date(2026, 9, 29))
    assert early["2019-ford-escape-sel-awd"]["next_drop"]["overdue"] is False


# AC4: renew due and days listed


def test_facebook_renew_is_due_seven_days_after_the_latest_posting(inventory, private):
    rows = rows_by_id(inventory, private)
    # Posted 09-29 and renewed 10-06: the latest counts.
    assert rows["sofa-sleeper"]["renew_due"] == date(2026, 10, 13)
    assert rows["sofa-sleeper"]["renew_overdue"] is False
    # Posted 09-30: due today.
    assert rows["dell-monitor-32"]["renew_due"] == date(2026, 10, 7)
    assert rows["dell-monitor-32"]["renew_overdue"] is True
    assert rows["2019-ford-escape-sel-awd"]["renew_overdue"] is True


def test_an_item_not_on_facebook_has_no_renew_date(inventory, private):
    data = copy.deepcopy(private)
    del data["tracking"]["sofa-sleeper"]["channels"]["facebook"]
    row = rows_by_id(inventory, data)["sofa-sleeper"]
    assert row["renew_due"] is None
    assert [c["name"] for c in row["channels"]] == ["craigslist"]


def test_days_listed_counts_from_the_earliest_posting_and_stops_at_the_sale(inventory, private):
    data = copy.deepcopy(inventory)
    next(i for i in data["items"] if i["id"] == "onn-43-4k-tv")["status"] = "Sold"
    tv = rows_by_id(data, private)["onn-43-4k-tv"]
    assert tv["sale"] == {"price": 59, "at": date(2026, 10, 12)}
    assert tv["days_listed"] == 13  # 09-29 to 10-12
    assert tv["renew_due"] is None  # nothing left to renew


def test_a_sale_recorded_the_old_way_as_a_bare_price_still_reads(inventory, private):
    data = copy.deepcopy(private)
    data["sales"] = {"onn-43-4k-tv": 59}
    tv = rows_by_id(inventory, data)["onn-43-4k-tv"]
    assert tv["sale"] == {"price": 59, "at": None}


def test_the_price_log_is_shown_and_flagged_when_it_disagrees_with_asking(inventory, private):
    sofa = rows_by_id(inventory, private)["sofa-sleeper"]
    assert sofa["price_log"] == [{"at": date(2026, 10, 3), "price": 205}]
    assert sofa["log_mismatch"] is True  # asking is still 220
    dell = rows_by_id(inventory, private)["dell-monitor-32"]
    assert dell["log_mismatch"] is False  # nothing logged, nothing to disagree with


def test_dates_that_arrive_as_datetimes_or_timestamps_read_too(inventory, private):
    data = copy.deepcopy(private)
    data["tracking"]["sofa-sleeper"]["channels"] = {
        "facebook": [date(2026, 10, 6), "2026-09-29T00:00:00Z"]
    }
    assert rows_by_id(inventory, data)["sofa-sleeper"]["renew_due"] == date(2026, 10, 13)


# The page


def test_the_page_shows_what_the_rows_say(inventory, private):
    html = panel.render_panel(panel.panel_rows(inventory, private, TODAY), TODAY)
    for shown in ("sofa-sleeper", "$220", "$191", "$173", "$195", "facebook", "Oct 13", "Oct 3"):
        assert shown in html
    assert 'name="robots" content="noindex' in html


def test_the_page_carries_the_marker_the_public_build_guard_looks_for(inventory, private):
    html = panel.render_panel(panel.panel_rows(inventory, private, TODAY), TODAY)
    assert PANEL_MARKER in html


def test_the_page_escapes_what_the_data_holds(inventory, private):
    data = copy.deepcopy(inventory)
    data["items"][0]["title"] = '<script>alert("x")</script>'
    html = panel.render_panel(panel.panel_rows(data, private, TODAY), TODAY)
    assert "<script>alert" not in html


def test_the_page_loads_nothing_from_anywhere(inventory, private):
    html = panel.render_panel(panel.panel_rows(inventory, private, TODAY), TODAY)
    assert not re.search(r"(src|href)=[\"']?(https?:)?//", html)
    assert "<script" not in html


# AC8: the command


def run_panel(tmp_path, **overrides):
    out = tmp_path / "panel.html"
    args = SimpleNamespace(private_file=None, out=out, **overrides)
    return args, out


def test_the_command_renders_from_a_plain_yaml_and_writes_it_private(tmp_path, monkeypatch, capsys):
    args, out = run_panel(tmp_path)
    args.private_file = FIXTURE
    cli.cmd_panel(args)
    assert "$173" in out.read_text(encoding="utf-8")
    assert stat.S_IMODE(out.stat().st_mode) == 0o600
    # The terminal gets counts, never the floors or targets.
    printed = capsys.readouterr().out
    for value in ("173", "191", "10650"):
        assert value not in printed


def test_the_command_fails_closed_when_the_sops_file_cannot_be_read(tmp_path, monkeypatch):
    args, out = run_panel(tmp_path)

    def refuse():
        raise RuntimeError("no key")

    monkeypatch.setattr(cli, "decrypt_private", refuse)
    with pytest.raises(SystemExit) as exit_info:
        cli.cmd_panel(args)
    assert exit_info.value.code != 0
    assert not out.exists()


def test_the_command_reads_the_sops_file_in_process(tmp_path, monkeypatch, private):
    args, out = run_panel(tmp_path)
    monkeypatch.setattr(cli, "decrypt_private", lambda: private)
    cli.cmd_panel(args)
    assert "$191" in out.read_text(encoding="utf-8")


def test_the_makefile_exposes_panel_post_and_reprice():
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    for target in ("panel", "post", "reprice"):
        assert re.search(rf"^{target}:.*##", makefile, re.M), target
    phony = re.search(r"^\.PHONY:(.*)$", makefile, re.M).group(1).split()
    assert {"panel", "post", "reprice"} <= set(phony)


def test_make_serve_shows_the_panel_on_loopback_only_from_the_private_dir():
    assert cli.resolve_request_path("/private/panel.html") == panel.PRIVATE_PANEL_HTML
    assert cli.make_server(0).server_address[0] == "127.0.0.1"


def test_the_runbooks_document_each_command_and_the_targets_step():
    playbook = (ROOT / "docs" / "runbooks" / "seller-playbook.md").read_text(encoding="utf-8")
    for command in ("make panel", "make post", "make reprice", "make sold", "make secrets"):
        assert command in playbook, command
    assert "targets:" in playbook
    ops = (ROOT / "docs" / "runbooks" / "ops.md").read_text(encoding="utf-8")
    assert "seller-playbook.md#the-control-panel" in ops
