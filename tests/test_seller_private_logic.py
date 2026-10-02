"""
The control panel's row logic, now in the browser (ADR-007 decision 8; FEAT-009 PR 2, AC12):
`buildRows` in seller.mjs turns the public roster and the decrypted private data into one row
per item, the way panel.py did (FEAT-004). It runs in Node here, on the real inventory and the
fixture's private data, so the cases are the panel's own.

The JavaScript computes it, not Python: the envelope holds the allow-list only (AC1), and
"overdue" depends on today, which a seal would freeze.
"""

import copy
import json

import pytest
import yaml
from sealed_helpers import FIXTURE, node

from leaving_denver import pricing
from leaving_denver.site_builder import (
    load_inventory_yaml,
    sale_schedule,
    sanitize_public_inventory,
    seller_drops,
    seller_roster,
)

TODAY = "2026-10-07"
# Halfway from the monitor's asking price to its $61 floor, to the nearest $5.
MONITOR_DROP = 80

SCRIPT = """
import { buildRows } from './src/leaving_denver/assets/seller.mjs';
let raw = '';
for await (const chunk of process.stdin) raw += chunk;
const { roster, payload, config, today } = JSON.parse(raw);
process.stdout.write(JSON.stringify(buildRows(roster, payload, config, today)));
"""


@pytest.fixture
def inventory():
    return load_inventory_yaml()


@pytest.fixture
def private():
    return yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))


def rows_by_id(inventory, private, today=TODAY):
    public = sanitize_public_inventory(copy.deepcopy(inventory))
    config = {
        "drops": seller_drops(inventory["seller"]),
        "renew_after_days": {"facebook": 7},
    }
    payload = {
        key: private.get(key) or {} for key in ("floors", "targets", "sales", "tracking", "notes")
    }
    result = node(
        SCRIPT,
        json.dumps(
            {"roster": seller_roster(public), "payload": payload, "config": config, "today": today}
        ),
    )
    assert result.returncode == 0, result.stderr
    return {row["id"]: row for row in json.loads(result.stdout)}


def with_item(inventory, item_id, **fields):
    data = copy.deepcopy(inventory)
    next(i for i in data["items"] if i["id"] == item_id).update(fields)
    return data


def with_log(private, item_id, *dates):
    data = copy.deepcopy(private)
    data["tracking"].setdefault(item_id, {})["price_log"] = [{"at": d, "price": 1} for d in dates]
    return data


def test_the_fixture_names_only_items_the_inventory_has(inventory, private):
    ids = {item["id"] for item in inventory["items"]}
    for section in ("floors", "targets", "sales", "tracking"):
        assert set(private[section]) <= ids, section


def test_the_drop_windows_are_the_schedules_opening_days(inventory):
    schedule = sale_schedule(inventory["seller"])
    assert seller_drops(inventory["seller"]) == {
        window: schedule[window][0].isoformat() for window in pricing.DROP_WINDOWS
    }


# One tier function for `drops` (Python) and the page (JavaScript)

TIER_SCRIPT = """
import { priceTiers } from './src/leaving_denver/assets/seller.mjs';
let raw = '';
for await (const chunk of process.stdin) raw += chunk;
process.stdout.write(JSON.stringify(JSON.parse(raw).map(c => priceTiers(c.item, c.floor))));
"""


def test_the_page_and_the_drops_command_agree_on_every_tier():
    """Python rounds a half to the even number and JavaScript up; the page must not differ
    from `make drops` by $5 on a midpoint that lands exactly between two steps."""
    cases = [
        {"item": {"price": price, "category": category}, "floor": floor}
        for category in ("Living Room", "Vehicle")
        for price in range(0, 400, 5)
        for floor in (None, *range(0, price + 1, 5))
    ]
    cases += [
        {"item": {"price": price, "category": "Vehicle"}, "floor": floor}
        for price, floor in ((11875, 10650), (12000, 10900), (10500, 9800), (11300, 10500))
    ]
    result = node(TIER_SCRIPT, json.dumps(cases))
    assert result.returncode == 0, result.stderr
    for case, tiers in zip(cases, json.loads(result.stdout), strict=True):
        python = pricing.price_tiers(
            {"recommended_list_price": case["item"]["price"], "category": case["item"]["category"]},
            case["floor"],
        )
        assert tuple(tiers) == python, case


# The ten fields


def test_a_row_carries_every_field_the_panel_had(inventory, private):
    sofa = rows_by_id(inventory, private)["sofa-sleeper"]
    assert sofa["asking"] == 220
    assert sofa["target"] == 191
    assert sofa["floor"] == 173
    assert sofa["status"] == "Available"
    assert sofa["daysListed"] == 8
    assert [c["name"] for c in sofa["channels"]] == ["facebook", "craigslist"]
    assert sofa["renewDue"] == "2026-10-13"
    # The log shows a reprice on 10-06, the day the first drop opened, so it is covered.
    assert sofa["nextDrop"]["price"] == 195


def test_there_is_one_row_per_item_in_inventory_order(inventory, private):
    rows = list(rows_by_id(inventory, private))
    published = [i["id"] for i in sanitize_public_inventory(copy.deepcopy(inventory))["items"]]
    assert rows[: len(published)] == published


def test_an_item_with_no_private_data_has_empty_fields_not_a_crash(inventory, private):
    desk = rows_by_id(inventory, private)["convertible-desk"]
    assert desk["target"] is None
    assert desk["daysListed"] is None
    assert desk["channels"] == []
    assert desk["renewDue"] is None
    assert desk["sale"] is None
    assert desk["priceLog"] == []


def test_the_rows_build_with_no_private_data_at_all(inventory):
    rows = rows_by_id(inventory, {})
    assert rows and all(r["floor"] is None and r["target"] is None for r in rows.values())


@pytest.mark.parametrize("section", ["floors", "targets", "sales", "tracking", "notes"])
def test_a_null_section_reads_as_empty(inventory, private, section):
    data = copy.deepcopy(private)
    data[section] = None
    assert rows_by_id(inventory, data)["sofa-sleeper"]["id"] == "sofa-sleeper"


# The next drop


def test_the_next_drop_steps_halfway_to_the_floor_at_the_first_drop_window(inventory, private):
    schedule = sale_schedule(inventory["seller"])
    monitor = rows_by_id(inventory, private)["dell-monitor-32"]
    assert monitor["nextDrop"] == {
        "on": schedule["first_drop"][0].isoformat(),
        "price": MONITOR_DROP,
        "overdue": True,
    }


def test_a_window_the_price_log_already_covers_is_not_the_next_drop(inventory, private):
    # The sofa was repriced on 10-06, the day the first drop opened: the second drop is next.
    sofa = rows_by_id(inventory, private)["sofa-sleeper"]
    assert sofa["nextDrop"] == {"on": "2026-10-12", "price": 195, "overdue": False}


def test_each_drop_recomputes_from_the_asking_price_in_force(inventory, private):
    data = with_item(inventory, "sofa-sleeper", recommended_list_price=195)
    row = rows_by_id(data, private)["sofa-sleeper"]
    assert row["nextDrop"]["price"] == 185  # halfway from 195 to the 173 floor, to the $5


def test_the_last_step_is_the_floor_at_the_clear_floors_window(inventory, private):
    schedule = sale_schedule(inventory["seller"])
    data = with_log(private, "sofa-sleeper", "2026-10-06", "2026-10-12")
    row = rows_by_id(inventory, data)["sofa-sleeper"]
    assert row["nextDrop"] == {
        "on": schedule["clear_floors"][0].isoformat(),
        "price": 173,
        "overdue": False,
    }


def test_nothing_is_left_to_drop_once_every_window_is_covered(inventory, private):
    data = with_log(private, "sofa-sleeper", "2026-10-06", "2026-10-12", "2026-10-16")
    assert rows_by_id(inventory, data)["sofa-sleeper"]["nextDrop"] is None


@pytest.mark.parametrize(
    ("item_id", "fields"),
    [
        ("air-mattress-twin-pump", {}),  # free with purchase
        ("coffee-table-lift-top", {}),  # no floor on file
        ("onn-43-4k-tv", {"status": "Sold"}),
        ("onn-43-4k-tv", {"status": "Pending"}),
        ("dell-monitor-32", {"recommended_list_price": 61}),  # already at the floor
        ("2019-ford-escape-sel-awd", {}),  # the car has no drop schedule (OPS-013)
    ],
)
def test_no_next_drop_when_there_is_nothing_to_drop(inventory, private, item_id, fields):
    data = with_item(inventory, item_id, **fields)
    assert rows_by_id(data, private)[item_id]["nextDrop"] is None


def test_a_drop_whose_window_has_not_started_is_not_overdue(inventory, private):
    early = rows_by_id(inventory, private, today="2026-09-29")
    assert early["dell-monitor-32"]["nextDrop"]["overdue"] is False


# Renew due and days listed


def test_facebook_renew_is_due_seven_days_after_the_latest_posting(inventory, private):
    rows = rows_by_id(inventory, private)
    # Posted 09-29 and renewed 10-06: the latest counts.
    assert rows["sofa-sleeper"]["renewDue"] == "2026-10-13"
    assert rows["sofa-sleeper"]["renewOverdue"] is False
    # Posted 09-30: due today.
    assert rows["dell-monitor-32"]["renewDue"] == "2026-10-07"
    assert rows["dell-monitor-32"]["renewOverdue"] is True
    assert rows["2019-ford-escape-sel-awd"]["renewOverdue"] is True


def test_an_item_not_on_facebook_has_no_renew_date(inventory, private):
    data = copy.deepcopy(private)
    del data["tracking"]["sofa-sleeper"]["channels"]["facebook"]
    row = rows_by_id(inventory, data)["sofa-sleeper"]
    assert row["renewDue"] is None
    assert [c["name"] for c in row["channels"]] == ["craigslist"]


def test_days_listed_counts_from_the_earliest_posting_and_stops_at_the_sale(inventory, private):
    data = with_item(inventory, "onn-43-4k-tv", status="Sold")
    tv = rows_by_id(data, private)["onn-43-4k-tv"]
    assert tv["sale"] == {"price": 59, "at": "2026-10-12"}
    assert tv["daysListed"] == 13  # 09-29 to 10-12
    assert tv["renewDue"] is None  # nothing left to renew


def test_a_sale_dated_before_the_first_posting_does_not_show_negative_days(inventory, private):
    data = copy.deepcopy(private)
    data["sales"]["onn-43-4k-tv"] = {"price": 59, "at": "2026-09-01"}
    sold = with_item(inventory, "onn-43-4k-tv", status="Sold")
    assert rows_by_id(sold, data)["onn-43-4k-tv"]["daysListed"] == 0


def test_a_sale_recorded_the_old_way_as_a_bare_price_still_reads(inventory, private):
    data = copy.deepcopy(private)
    data["sales"] = {"onn-43-4k-tv": 59}
    tv = rows_by_id(inventory, data)["onn-43-4k-tv"]
    assert tv["sale"] == {"price": 59, "at": None}


def test_the_price_log_is_shown_and_flagged_when_it_disagrees_with_asking(inventory, private):
    sofa = rows_by_id(inventory, private)["sofa-sleeper"]
    assert sofa["priceLog"] == [{"at": "2026-10-06", "price": 205}]
    assert sofa["logMismatch"] is True  # asking is still 220
    dell = rows_by_id(inventory, private)["dell-monitor-32"]
    assert dell["logMismatch"] is False  # nothing logged, nothing to disagree with


def test_dates_that_arrive_as_timestamps_read_too(inventory, private):
    data = copy.deepcopy(private)
    data["tracking"]["sofa-sleeper"]["channels"] = {
        "facebook": ["2026-10-06", "2026-09-29T00:00:00Z"]
    }
    assert rows_by_id(inventory, data)["sofa-sleeper"]["renewDue"] == "2026-10-13"


# Notes, and what the roster does not know


def test_a_note_rides_on_its_items_row(inventory, private):
    data = copy.deepcopy(private)
    data["notes"] = {"sofa-sleeper": "Firm on the delivery fee."}
    rows = rows_by_id(inventory, data)
    assert rows["sofa-sleeper"]["note"] == "Firm on the delivery fee."
    assert rows["dell-monitor-32"]["note"] is None


def test_private_entries_for_an_unpublished_item_still_show_as_their_own_row(inventory, private):
    """A draft is not in the public roster (its id is not published), but its floor is in the
    envelope: it shows by id, so nothing the owner recorded is silently hidden."""
    data = copy.deepcopy(private)
    data["floors"]["draft-lamp"] = 22
    row = rows_by_id(inventory, data)["draft-lamp"]
    assert row["floor"] == 22
    assert row["unpublished"] is True
    assert row["title"] == "draft-lamp"
    assert row["nextDrop"] is None


def test_a_published_item_is_not_marked_unpublished(inventory, private):
    assert rows_by_id(inventory, private)["sofa-sleeper"]["unpublished"] is False
