from leaving_denver import cli, private_data


def test_drops_prints_windows_from_departure_date(monkeypatch, capsys):
    monkeypatch.setattr(
        cli,
        "load_inventory_yaml",
        lambda: {"seller": {"departure_date": "2026-11-09"}, "items": []},
    )
    monkeypatch.setattr(private_data, "floors", lambda: {"unused": 1})

    cli.cmd_drops(None)

    output = capsys.readouterr().out
    assert "First drop: Oct 3-6" in output
    assert "Second drop: Oct 15-17" in output
    assert "Clear floors: Oct 20-25" in output
    assert "Giveaway: Nov 3-5" in output
