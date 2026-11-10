"""
The sale's arithmetic (OPS-018): expected against realized, by group, and the days.

The summary is pure — the private data arrives as arguments — so the arithmetic is tested here
without sops, an age key or the real encrypted file. The command that prints it is tested with a
stubbed reader for the same reason.
"""

import argparse
import json

import pytest

from leaving_denver import cli, private_data, retro

OPENED = "2026-09-25"
SALES = {
    "a": {"price": 150, "at": "2026-10-06"},
    "b": {"price": 500, "at": "2026-10-16"},
    "gift": {"price": 0, "at": "2026-11-09"},
}


def item(item_id, *, category="Living Room", status="Sold", asking=200, disposition=None):
    entry = {
        "id": item_id,
        "category": category,
        "status": status,
        "recommended_list_price": asking,
    }
    if disposition:
        entry["disposition"] = disposition
    return entry


def summarize(items, targets=None, floors=None, sales=None):
    return retro.retro_summary(items, targets or {}, floors or {}, sales or {}, OPENED)


def test_the_field_defaults_to_a_sale():
    assert retro.item_disposition(item("x")) == "sale"
    assert retro.item_disposition(item("x", disposition="giveaway")) == "giveaway"


def test_an_unknown_disposition_is_an_error():
    with pytest.raises(ValueError, match="disposition"):
        retro.item_disposition(item("x", disposition="donated"))


def test_the_end_counts_are_derived_from_the_items():
    from leaving_denver.site_builder import end_counts

    items = [item("a"), item("b"), item("g"), item("g", disposition="giveaway")]
    items.append(item("u", status="Available"))
    assert end_counts(items) == {"total": 5, "sold": 3, "given": 1}


def test_a_target_is_compared_with_what_that_same_item_realized():
    """The car has no target and the bed listed too late: money from items without one must not
    be compared against the targets of the others, which is how a 65% became a 1753%."""
    summary = summarize(
        [item("a", asking=200), item("b", asking=900)],
        targets={"a": 200},
        sales=SALES,
    )
    household = summary["groups"]["household"]
    assert household["realized"] == 650
    assert household["expected"] == 200
    assert household["expected_items"] == 1
    assert household["on_expected"] == 150
    assert household["of_expected_pct"] == 75
    assert household["of_asking_pct"] == round(650 / 1100 * 100)


def test_no_target_means_no_percentage_instead_of_zero():
    summary = summarize([item("b", asking=900)], sales=SALES)
    assert summary["groups"]["household"]["of_expected_pct"] is None


def test_a_giveaway_is_placed_and_earns_nothing():
    summary = summarize(
        [item("g", disposition="giveaway", asking=100)],
        sales={"g": {"price": 0, "at": "2026-11-09"}},
    )
    group = summary["groups"]["household"]
    assert (group["sold"], group["given"], group["unplaced"]) == (0, 1, 0)
    assert group["realized"] == 0
    assert summary["counts"] == {"total": 1, "sold": 0, "given": 1, "unplaced": 0}


def test_an_unplaced_item_is_counted_apart_and_earns_nothing():
    summary = summarize([item("u", status="Available", asking=100)])
    group = summary["groups"]["household"]
    assert (group["sold"], group["given"], group["unplaced"]) == (0, 0, 1)
    assert group["realized"] == 0


def test_the_median_days_ignores_a_giveaway():
    """A giveaway sat until the last day and sold nothing: counting its days as a sale's would
    say the sale was slower than it was."""
    items = [item("a"), item("b"), item("g", disposition="giveaway")]
    group = summarize(items, sales=SALES)["groups"]["household"]
    assert group["median_days"] == round((11 + 21) / 2)  # not the giveaway's 45


def test_an_item_with_no_record_has_no_days():
    assert summarize([item("a")])["groups"]["household"]["median_days"] is None


def test_the_vehicle_is_its_own_group_and_the_total_is_the_sum():
    items = [item("a"), item("car", category="Vehicle", asking=11950)]
    sales = {**SALES, "car": {"price": 10500, "at": "2026-11-09"}}
    summary = summarize(items, targets={"a": 200}, floors={"car": 10500}, sales=sales)
    assert summary["groups"]["vehicle"]["items"] == 1
    assert summary["groups"]["vehicle"]["of_floors_pct"] == 100
    assert summary["groups"]["total"]["items"] == 2
    assert summary["groups"]["total"]["realized"] == 10650
    assert summary["counts"]["total"] == 2


def test_the_span_runs_from_the_catalog_opening_to_the_last_sale():
    summary = summarize([item("a"), item("b")], sales={"a": SALES["a"], "b": SALES["b"]})
    assert summary["last_sale"] == "2026-10-16"
    assert summary["span_days"] == 21


def test_a_disagreement_is_named_for_each_way_the_two_sources_can_differ():
    items = [
        item("no_record"),
        item("priced_giveaway", disposition="giveaway"),
        item("unpriced_sale"),
    ]
    sales = {
        "priced_giveaway": {"price": 40, "at": "2026-10-06"},
        "unpriced_sale": {"price": 0, "at": "2026-10-06"},
    }
    found = retro.disagreements(items, sales)
    assert any(line.startswith("no_record:") for line in found)
    assert any(line.startswith("priced_giveaway:") for line in found)
    assert any(line.startswith("unpriced_sale:") for line in found)


def test_an_unplaced_item_is_never_a_disagreement():
    sales = {"u": {"price": 0, "at": "2026-10-06"}}
    assert retro.disagreements([item("u", status="Available")], sales) == []


def test_the_text_report_names_the_counts_the_days_and_the_totals():
    summary = summarize(
        [item("a"), item("gift", disposition="giveaway")], targets={"a": 200}, sales=SALES
    )
    text = retro.render_text(summary)
    assert "Placed: 2 of 2" in text
    assert "10 sold" not in text  # the real inventory is never assumed
    assert "1 sold, 1 given away, 0 unplaced" in text
    assert "catalog opened 2026-09-25" in text
    assert "$150" in text


class FakePrivate:
    """A decrypted document with a phone and a token in it, as the real one has."""

    PHONE = "+13035550100"
    TOKEN = "sentinel-pages-token-9f2"

    @classmethod
    def document(cls):
        return {
            "seller": {"phone": cls.PHONE},
            "cloudflare_pages_token": cls.TOKEN,
            "targets": {"sofa-sleeper": 200},
            "floors": {"sofa-sleeper": 150},
            "sales": {"sofa-sleeper": {"price": 180, "at": "2026-10-16"}},
        }


def test_the_command_prints_the_summary(capsys, monkeypatch):
    monkeypatch.setattr(private_data, "decrypt_private", FakePrivate.document)
    cli.cmd_retro(argparse.Namespace(json=False))
    out = capsys.readouterr().out
    assert "SALE CLOSE-OUT" in out
    assert "household" in out


def test_the_json_mode_is_json(capsys, monkeypatch):
    monkeypatch.setattr(private_data, "decrypt_private", FakePrivate.document)
    cli.cmd_retro(argparse.Namespace(json=True))
    summary = json.loads(capsys.readouterr().out)
    assert summary["counts"]["total"] >= 1
    assert "groups" in summary


@pytest.mark.parametrize("as_json", [False, True])
def test_the_command_prints_no_phone_and_no_token(capsys, monkeypatch, as_json):
    monkeypatch.setattr(private_data, "decrypt_private", FakePrivate.document)
    cli.cmd_retro(argparse.Namespace(json=as_json))
    out = capsys.readouterr().out
    assert FakePrivate.PHONE not in out
    assert "3035550100" not in out
    assert FakePrivate.TOKEN not in out


def test_an_unreadable_private_file_prints_no_total_at_all(capsys, monkeypatch):
    """A partial report built on an empty document would read as a real result (lesson-019)."""

    def refuse():
        raise RuntimeError("data/private.sops.yaml is not decryptable")

    monkeypatch.setattr(private_data, "decrypt_private", refuse)
    with pytest.raises(SystemExit) as exit_info:
        cli.cmd_retro(argparse.Namespace(json=False))
    assert exit_info.value.code == 1
    out = capsys.readouterr().out
    assert "not decryptable" in out
    assert "$" not in out


def test_a_private_file_with_no_sales_prints_no_total_either(capsys, monkeypatch):
    monkeypatch.setattr(private_data, "decrypt_private", lambda: {"targets": {"a": 10}})
    with pytest.raises(SystemExit) as exit_info:
        cli.cmd_retro(argparse.Namespace(json=False))
    assert exit_info.value.code == 1
    assert "$" not in capsys.readouterr().out
