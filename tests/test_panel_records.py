"""
Recording what happens to a listing (FEAT-004): posts, reprices and sales go to the encrypted
file through `sops set`, never into the public inventory.

The unit tests stub the one `sops` call; the integration test runs the real binary against a
throwaway file encrypted to a throwaway age key. Nothing here touches data/private.sops.yaml.
"""

import json
import shutil
import subprocess
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from leaving_denver import cli, private_data

TODAY = date(2026, 10, 7)
ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "private.example.yaml"


class FakeSops:
    """Stands in for the sops binary: records each `set`, answers `--decrypt` from a dict."""

    def __init__(self, monkeypatch, tmp_path, private=None, fail_set=False):
        self.sets = []
        self.private = private or {}
        self.fail_set = fail_set
        monkeypatch.setattr(private_data.shutil, "which", lambda _: "/usr/bin/sops")
        (tmp_path / "private.sops.yaml").touch()
        monkeypatch.setattr(private_data, "PRIVATE_SOPS_YAML", tmp_path / "private.sops.yaml")
        monkeypatch.setattr(private_data.subprocess, "run", self.run)

    def run(self, args, **kw):
        if "--decrypt" in args:
            return SimpleNamespace(returncode=0, stdout=json.dumps(self.private), stderr="")
        self.sets.append((args[-1], json.loads(kw["input"]), args))
        return SimpleNamespace(returncode=1 if self.fail_set else 0, stderr="set failed")


@pytest.fixture
def fixture_private():
    return yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))


def test_record_sale_writes_the_price_and_the_day_as_one_object(tmp_path, monkeypatch):
    sops = FakeSops(monkeypatch, tmp_path)
    private_data.record_sale("lamp", 120, TODAY)
    path, value, argv = sops.sets[0]
    assert path == '["sales"]["lamp"]'
    assert value == {"price": 120, "at": "2026-10-07"}
    # The values travel on stdin: nothing in argv reveals them.
    assert "120" not in " ".join(argv)


def test_record_sale_without_a_price_records_only_the_day(tmp_path, monkeypatch):
    sops = FakeSops(monkeypatch, tmp_path)
    private_data.record_sale("lamp", None, TODAY)
    assert sops.sets[0][0] == '["sales"]["lamp"]["at"]'
    assert sops.sets[0][1] == "2026-10-07"


def test_selling_again_without_a_price_keeps_the_price_already_recorded(tmp_path, monkeypatch):
    """Only the day is set, so a second `make sold` with no PRICE cannot wipe the first price."""
    sops = FakeSops(monkeypatch, tmp_path, {"sales": {"lamp": {"price": 120, "at": "2026-10-01"}}})
    private_data.record_sale("lamp", None, TODAY)
    assert [path for path, _, _ in sops.sets] == ['["sales"]["lamp"]["at"]']


def test_selling_again_without_a_price_leaves_a_bare_price_alone(tmp_path, monkeypatch):
    sops = FakeSops(monkeypatch, tmp_path, {"sales": {"lamp": 120}})
    private_data.record_sale("lamp", None, TODAY)
    assert sops.sets == []


def test_a_null_tracking_section_reads_as_empty(tmp_path, monkeypatch):
    sops = FakeSops(monkeypatch, tmp_path, {"tracking": None, "sales": None})
    private_data.record_post("lamp", "facebook", TODAY)
    private_data.record_sale("lamp", None, TODAY)
    assert sops.sets[0][0] == '["tracking"]["lamp"]["channels"]["facebook"][0]'
    assert sops.sets[1][0] == '["sales"]["lamp"]["at"]'


def test_a_post_is_appended_to_the_channels_history(tmp_path, monkeypatch, fixture_private):
    sops = FakeSops(monkeypatch, tmp_path, fixture_private)
    private_data.record_post("sofa-sleeper", "facebook", TODAY)
    path, value, _ = sops.sets[0]
    # The two earlier postings stay; this one goes at the next index.
    assert path == '["tracking"]["sofa-sleeper"]["channels"]["facebook"][2]'
    assert value == "2026-10-07"


def test_the_first_post_on_a_channel_starts_its_history(tmp_path, monkeypatch, fixture_private):
    sops = FakeSops(monkeypatch, tmp_path, fixture_private)
    private_data.record_post("convertible-desk", "offerup", TODAY)
    assert sops.sets[0][0] == '["tracking"]["convertible-desk"]["channels"]["offerup"][0]'
    assert sops.sets[0][1] == "2026-10-07"


def test_a_reprice_is_appended_to_the_price_log(tmp_path, monkeypatch, fixture_private):
    sops = FakeSops(monkeypatch, tmp_path, fixture_private)
    private_data.record_price("sofa-sleeper", 190, TODAY)
    path, value, _ = sops.sets[0]
    assert path == '["tracking"]["sofa-sleeper"]["price_log"][1]'
    assert value == {"at": "2026-10-07", "price": 190}


def test_nothing_is_written_when_the_history_cannot_be_read_first(tmp_path, monkeypatch):
    """An unreadable file is not an empty one: appending to {} would erase the history."""
    (tmp_path / "private.sops.yaml").touch()
    monkeypatch.setattr(private_data, "PRIVATE_SOPS_YAML", tmp_path / "private.sops.yaml")
    monkeypatch.setattr(private_data.shutil, "which", lambda _: "/usr/bin/sops")
    calls = []

    def run(args, **kw):
        calls.append(args)
        return SimpleNamespace(returncode=1, stdout="", stderr="no key")

    monkeypatch.setattr(private_data.subprocess, "run", run)
    with pytest.raises(RuntimeError):
        private_data.record_post("sofa-sleeper", "facebook", TODAY)
    assert all("--decrypt" in c for c in calls), "a set ran after a failed read"


def test_a_failed_set_is_reported(tmp_path, monkeypatch, fixture_private):
    FakeSops(monkeypatch, tmp_path, fixture_private, fail_set=True)
    with pytest.raises(RuntimeError, match="set failed"):
        private_data.record_price("sofa-sleeper", 190, TODAY)


# The commands


@pytest.fixture
def commands(monkeypatch, fixture_private):
    """The CLI with inventory, recorders and rebuild stubbed; `calls` collects what ran."""
    inventory = {
        "seller": {"departure_date": "2026-11-09"},
        "items": [
            {"id": "sofa-sleeper", "title": "Sofa", "status": "Available"},
            {"id": "lamp", "title": "Lamp", "status": "Available"},
        ],
    }
    calls = []
    saved = []
    monkeypatch.setattr(cli, "load_inventory_yaml", lambda: inventory)
    monkeypatch.setattr(cli, "save_inventory_yaml", saved.append)
    monkeypatch.setattr(cli, "build_all", lambda: None)
    monkeypatch.setattr(cli, "load_private", lambda: fixture_private)
    for name in ("record_post", "record_price", "record_sale"):
        monkeypatch.setattr(cli, name, lambda *a, _n=name: calls.append((_n, *a)))
    return SimpleNamespace(calls=calls, saved=saved, inventory=inventory)


def post_args(**kw):
    return SimpleNamespace(**{"id": "sofa-sleeper", "channel": "facebook", "on": None, **kw})


def test_post_records_today_by_default(commands):
    cli.cmd_post(post_args())
    assert commands.calls == [("record_post", "sofa-sleeper", "facebook", date.today())]


def test_post_takes_a_date_for_a_listing_made_earlier(commands):
    cli.cmd_post(post_args(on="2026-09-29"))
    assert commands.calls == [("record_post", "sofa-sleeper", "facebook", date(2026, 9, 29))]


@pytest.mark.parametrize(
    "bad", [{"id": "typo"}, {"channel": "ebay"}, {"on": "yesterday"}, {"on": "2026-13-40"}]
)
def test_post_refuses_an_unknown_item_channel_or_date_and_records_nothing(commands, bad):
    with pytest.raises(SystemExit):
        cli.cmd_post(post_args(**bad))
    assert commands.calls == []


def test_reprice_records_the_new_price(commands):
    cli.cmd_reprice(SimpleNamespace(id="sofa-sleeper", price=190, on=None))
    assert commands.calls == [("record_price", "sofa-sleeper", 190, date.today())]


@pytest.mark.parametrize("bad", [{"id": "typo"}, {"price": 0}, {"price": -5}])
def test_reprice_refuses_an_unknown_item_or_a_non_positive_price(commands, bad):
    with pytest.raises(SystemExit):
        cli.cmd_reprice(SimpleNamespace(**{"id": "sofa-sleeper", "price": 190, "on": None, **bad}))
    assert commands.calls == []


@pytest.mark.parametrize(
    "failure", [RuntimeError("x"), json.JSONDecodeError("bad", "", 0), AttributeError("y")]
)
def test_a_failed_write_is_an_error_not_a_traceback(commands, monkeypatch, capsys, failure):
    def refuse(*args):
        raise failure

    monkeypatch.setattr(cli, "record_post", refuse)
    with pytest.raises(SystemExit):
        cli.cmd_post(post_args())
    assert capsys.readouterr().out.startswith("Error:")


def test_sold_records_the_price_and_the_day(commands):
    cli.cmd_sold(SimpleNamespace(id="sofa-sleeper", price=180))
    assert commands.calls == [("record_sale", "sofa-sleeper", 180, date.today())]
    assert commands.saved[-1]["items"][0]["status"] == "Sold"


def test_sold_lists_takedown_only_for_the_channels_the_item_was_posted_on(commands, capsys):
    cli.cmd_sold(SimpleNamespace(id="sofa-sleeper", price=180))
    out = capsys.readouterr().out
    assert "Facebook Marketplace" in out
    assert "Craigslist" in out
    assert "OfferUp" not in out
    assert "Nextdoor" not in out


def test_sold_lists_every_channel_when_nothing_was_recorded(commands, capsys):
    cli.cmd_sold(SimpleNamespace(id="lamp", price=20))
    out = capsys.readouterr().out
    for channel in ("Facebook", "Craigslist", "OfferUp", "Nextdoor", "ActiveBuilding"):
        assert channel in out
    assert "no posting recorded" in out.lower()


def test_sold_without_a_price_still_works_when_the_day_cannot_be_recorded(commands, monkeypatch):
    def refuse(*args):
        raise RuntimeError("sops unavailable")

    monkeypatch.setattr(cli, "record_sale", refuse)
    cli.cmd_sold(SimpleNamespace(id="lamp", price=None))
    assert commands.saved[-1]["items"][1]["status"] == "Sold"


def test_the_public_inventory_never_gains_a_price_a_date_or_a_channel(commands):
    cli.cmd_sold(SimpleNamespace(id="sofa-sleeper", price=180))
    cli.cmd_post(post_args())
    cli.cmd_reprice(SimpleNamespace(id="sofa-sleeper", price=190, on=None))
    item = commands.saved[-1]["items"][0]
    assert set(item) == {"id", "title", "status"}


# The real sops, against a throwaway key


@pytest.mark.skipif(
    not (shutil.which("sops") and shutil.which("age-keygen")), reason="needs sops and age"
)
def test_the_real_sops_accepts_the_values_and_keeps_the_history(tmp_path, monkeypatch):
    key = tmp_path / "key.txt"
    subprocess.run(["age-keygen", "-o", str(key)], check=True, capture_output=True)
    public = next(
        line.split()[-1] for line in key.read_text().splitlines() if line.startswith("# public")
    )
    plain = tmp_path / "plain.yaml"
    plain.write_text("floors:\n  lamp: 40\n", encoding="utf-8")
    encrypted = tmp_path / "private.sops.yaml"
    # From tmp_path, so no creation rules from a .sops.yaml further up the tree apply.
    with encrypted.open("w") as out:
        subprocess.run(
            ["sops", "encrypt", "--age", public, str(plain)], check=True, stdout=out, cwd=tmp_path
        )
    plain.unlink()
    monkeypatch.setenv("SOPS_AGE_KEY_FILE", str(key))
    monkeypatch.setattr(private_data, "PRIVATE_SOPS_YAML", encrypted)

    private_data.record_post("lamp", "facebook", date(2026, 10, 1))
    private_data.record_post("lamp", "facebook", date(2026, 10, 8))
    private_data.record_price("lamp", 35, date(2026, 10, 3))
    private_data.record_sale("lamp", 30, date(2026, 10, 9))

    data = private_data.decrypt_private()
    assert data["floors"] == {"lamp": 40}
    assert data["tracking"]["lamp"]["channels"]["facebook"] == ["2026-10-01", "2026-10-08"]
    assert data["tracking"]["lamp"]["price_log"] == [{"at": "2026-10-03", "price": 35}]
    assert data["sales"]["lamp"] == {"price": 30, "at": "2026-10-09"}
    # Selling again with no price moves the day and keeps the price.
    private_data.record_sale("lamp", None, date(2026, 10, 10))
    assert private_data.decrypt_private()["sales"]["lamp"] == {"price": 30, "at": "2026-10-10"}
    # Nothing readable on disk: the values are encrypted.
    assert "2026-10-08" not in encrypted.read_text()


def test_a_test_that_forgets_to_stub_the_recorder_cannot_write_the_real_file():
    """The suite-wide guard (tests/conftest.py) fails the test instead of editing the owner's file."""
    with pytest.raises(pytest.fail.Exception, match="real data/private.sops.yaml"):
        private_data.set_private(["sales", "x"], {"at": "2026-10-07"})
