"""
Recording offers to update /seller/ (ADR-007 decision 8; FEAT-009 PR 2, AC14).

After a successful `make post`, `make sold` or `make reprice` the command asks once whether to
update /seller/ now. No is the default and so is any run without a terminal; yes seals, sets
the secret in both environments and dispatches the deploy, and the exit status reflects them.
"""

import json
from types import SimpleNamespace

import pytest
from sealed_helpers import PASSPHRASE, fixture_private, install_fakes

from leaving_denver import cli, seal

INVENTORY_OF_ONE = {
    "seller": {"departure_date": "2026-11-09"},
    "items": [{"id": "sofa-sleeper", "title": "Sofa", "status": "Available"}],
}


@pytest.fixture
def commands(monkeypatch):
    """The CLI with inventory, recorders and rebuild stubbed; `calls` records the order."""
    inventory = {
        "seller": {"departure_date": "2026-11-09"},
        "items": [{"id": "sofa-sleeper", "title": "Sofa", "status": "Available"}],
    }
    calls = []
    monkeypatch.setattr(cli, "load_inventory_yaml", lambda: inventory)
    monkeypatch.setattr(cli, "save_inventory_yaml", lambda data: None)
    monkeypatch.setattr(cli, "build_all", lambda: None)
    monkeypatch.setattr(cli, "load_private", fixture_private)
    for name in ("record_post", "record_price", "record_sale"):
        monkeypatch.setattr(cli, name, lambda *a, _n=name: calls.append(_n))
    monkeypatch.setattr(seal, "run_seal", lambda offer_generation=True: calls.append("seal"))
    monkeypatch.setattr(seal, "dispatch_deploy", lambda: calls.append("dispatch"))
    return calls


def terminal(monkeypatch, answers, tty=True):
    asked = []

    def line(prompt):
        asked.append(prompt)
        return answers.pop(0)

    monkeypatch.setattr(seal, "has_tty", lambda: tty)
    monkeypatch.setattr(seal, "prompt_line", line)
    return asked


RECORDS = {
    "post": lambda: cli.cmd_post(SimpleNamespace(id="sofa-sleeper", channel="facebook", on=None)),
    "reprice": lambda: cli.cmd_reprice(SimpleNamespace(id="sofa-sleeper", price=190, on=None)),
    "sold": lambda: cli.cmd_sold(SimpleNamespace(id="sofa-sleeper", price=180)),
}
RECORDED = {"post": "record_post", "reprice": "record_price", "sold": "record_sale"}


@pytest.mark.parametrize("command", RECORDS)
@pytest.mark.parametrize("answer", ["", "n", "N", "no", "maybe", "  "])
def test_anything_but_yes_changes_nothing_more(command, answer, commands, monkeypatch):
    asked = terminal(monkeypatch, [answer])
    RECORDS[command]()
    assert commands == [RECORDED[command]]
    assert len(asked) == 1
    assert "/seller/" in asked[0]
    assert "[y/N]" in asked[0], "the default is no, and the prompt says so"


@pytest.mark.parametrize("command", RECORDS)
def test_without_a_terminal_it_does_not_ask_and_changes_nothing_more(
    command, commands, monkeypatch
):
    asked = terminal(monkeypatch, [], tty=False)
    RECORDS[command]()
    assert commands == [RECORDED[command]]
    assert asked == []


@pytest.mark.parametrize("command", RECORDS)
@pytest.mark.parametrize("answer", ["y", "Y", "yes", " YES "])
def test_yes_seals_then_dispatches_after_the_record(command, answer, commands, monkeypatch):
    asked = terminal(monkeypatch, [answer])
    RECORDS[command]()
    assert commands == [RECORDED[command], "seal", "dispatch"]
    assert len(asked) == 1, "asked once, and the seal is not offered a new passphrase"


def test_yes_does_not_offer_to_generate_a_new_passphrase(commands, monkeypatch):
    seen = []
    monkeypatch.setattr(
        seal, "run_seal", lambda offer_generation=True: seen.append(offer_generation)
    )
    terminal(monkeypatch, ["y"])
    RECORDS["post"]()
    assert seen == [False]


@pytest.mark.parametrize("command", RECORDS)
def test_a_failed_seal_is_the_commands_exit_status_and_nothing_deploys(
    command, commands, monkeypatch, capsys
):
    def refuse(offer_generation=True):
        raise seal.SealError("the two entries do not match")

    monkeypatch.setattr(seal, "run_seal", refuse)
    terminal(monkeypatch, ["y"])
    with pytest.raises(SystemExit) as failed:
        RECORDS[command]()
    assert failed.value.code == 1
    assert "dispatch" not in commands
    assert "not updated" in capsys.readouterr().out


def test_a_failed_dispatch_is_the_commands_exit_status(commands, monkeypatch, capsys):
    def refuse():
        raise seal.SealError("gh could not dispatch the deploy")

    monkeypatch.setattr(seal, "dispatch_deploy", refuse)
    terminal(monkeypatch, ["y"])
    with pytest.raises(SystemExit) as failed:
        RECORDS["post"]()
    assert failed.value.code == 1


@pytest.mark.parametrize("command", RECORDS)
def test_a_record_that_fails_never_asks(command, commands, monkeypatch):
    def refuse(*args):
        raise RuntimeError("sops unavailable")

    for name in ("record_post", "record_price", "record_sale"):
        monkeypatch.setattr(cli, name, refuse)
    asked = terminal(monkeypatch, ["y"])
    with pytest.raises(SystemExit):
        RECORDS[command]()
    assert asked == []
    assert commands == []


def test_an_unknown_item_never_asks(commands, monkeypatch):
    asked = terminal(monkeypatch, ["y"])
    with pytest.raises(SystemExit):
        cli.cmd_post(SimpleNamespace(id="typo", channel="facebook", on=None))
    assert asked == []


def test_yes_end_to_end_sets_both_environments_then_dispatches_the_deploy(tmp_path, monkeypatch):
    """The real seal and the real `gh` call sequence, with the terminal and `gh` stubbed."""
    inventory = {
        "seller": {"departure_date": "2026-11-09"},
        "items": [{"id": "sofa-sleeper", "title": "Sofa", "status": "Available"}],
    }
    monkeypatch.setattr(cli, "load_inventory_yaml", lambda: inventory)
    monkeypatch.setattr(cli, "record_price", lambda *a: None)
    monkeypatch.setattr(seal, "decrypt_private", fixture_private)
    monkeypatch.chdir(tmp_path)
    gh_calls = install_fakes(tmp_path, monkeypatch)
    secrets = [PASSPHRASE, PASSPHRASE]
    monkeypatch.setattr(seal, "has_tty", lambda: True)
    monkeypatch.setattr(seal, "prompt_line", lambda prompt: "y")
    monkeypatch.setattr(seal, "prompt_secret", lambda prompt: secrets.pop(0))
    cli.cmd_reprice(SimpleNamespace(id="sofa-sleeper", price=190, on=None))
    argv = [call["argv"] for call in gh_calls()]
    assert argv[0] == ["secret", "set", "SELLER_SEALED", "--env", "production"]
    assert argv[1] == ["secret", "set", "SELLER_SEALED", "--env", "preview"]
    assert argv[-1] == ["workflow", "run", "ci.yml", "--ref", "main", "-f", "branch=main"]
    assert secrets == [], "the passphrase was asked for exactly twice"
    assert json.loads(gh_calls()[0]["stdin"])["v"] == 1


@pytest.mark.parametrize("command", RECORDS)
def test_an_empty_passphrase_on_a_resealing_aborts_with_the_hint_and_rotates_nothing(
    command, tmp_path, monkeypatch, capsys
):
    """Yes, then Enter at the passphrase: a routine sale must not make a new passphrase.
    The real seal runs here, over the fakes."""
    monkeypatch.setattr(cli, "load_inventory_yaml", lambda: INVENTORY_OF_ONE)
    monkeypatch.setattr(cli, "save_inventory_yaml", lambda data: None)
    monkeypatch.setattr(cli, "build_all", lambda: None)
    monkeypatch.setattr(cli, "load_private", fixture_private)
    for name in ("record_post", "record_price", "record_sale"):
        monkeypatch.setattr(cli, name, lambda *a: None)
    monkeypatch.setattr(seal, "decrypt_private", fixture_private)
    monkeypatch.chdir(tmp_path)
    gh_calls = install_fakes(tmp_path, monkeypatch)
    monkeypatch.setattr(seal, "has_tty", lambda: True)
    monkeypatch.setattr(seal, "prompt_line", lambda prompt: "y")
    monkeypatch.setattr(seal, "prompt_secret", lambda prompt: "")
    monkeypatch.setattr(seal, "tell", lambda text: pytest.fail("a re-seal showed a passphrase"))
    with pytest.raises(SystemExit) as failed:
        RECORDS[command]()
    assert failed.value.code == 1
    assert "make ci-secrets to make a new one" in capsys.readouterr().out
    assert gh_calls() == []
