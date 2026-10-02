"""
`leaving-denver seal` (ADR-007 decisions 3, 4 and 6; FEAT-009 PR 2, AC4, AC5 and AC10).

The terminal, `gh` and `sops` are stubbed: the TTY by monkeypatching the prompt functions, `gh`
and `sops` by fakes ahead of the real ones on PATH. The Node child is the real one except where
a test says otherwise. Nothing here reads the real data/private.sops.yaml.
"""

import json
import os
import re
import subprocess
import sys

import pytest
from sealed_helpers import (
    PASSPHRASE,
    ROOT,
    SENTINEL_FLOOR,
    SENTINEL_NOTE,
    fixture_private,
    install_fakes,
    open_in_node,
)

from leaving_denver import cli, seal

WORDS = seal.load_wordlist()


class Terminal:
    """A stand-in for the owner's terminal: scripted answers, and everything shown to it."""

    def __init__(self, monkeypatch, secrets=(PASSPHRASE, PASSPHRASE), lines=("n",), tty=True):
        self.secrets, self.lines, self.shown, self.asked = list(secrets), list(lines), [], []
        monkeypatch.setattr(seal, "has_tty", lambda: tty)
        monkeypatch.setattr(seal, "prompt_secret", self.secret)
        monkeypatch.setattr(seal, "prompt_line", self.line)
        monkeypatch.setattr(seal, "tell", self.shown.append)

    def secret(self, prompt):
        self.asked.append(prompt)
        return self.secrets.pop(0)

    def line(self, prompt):
        self.asked.append(prompt)
        return self.lines.pop(0)


@pytest.fixture
def fixture_data(monkeypatch):
    monkeypatch.setattr(seal, "decrypt_private", fixture_private)


@pytest.fixture
def machine(tmp_path, monkeypatch, fixture_data):
    """An empty working directory, the fakes on PATH and a function for the calls gh saw."""
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(work)
    return install_fakes(tmp_path, monkeypatch), work


@pytest.fixture
def machine_with_dotf(tmp_path, monkeypatch, fixture_data):
    """As `machine`, with a fake `dotf` on PATH that records its argv, stdin and environment."""
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(work)
    return install_fakes(tmp_path, monkeypatch, dotf=True), work


def sets(calls):
    return [c for c in calls if c["argv"][:3] == ["secret", "set", "SELLER_SEALED"]]


# AC4: what the target accepts


def test_the_wordlist_is_the_eff_large_list_with_its_licence_in_the_header():
    text = (ROOT / "data" / "eff_large_wordlist.txt").read_text(encoding="utf-8")
    header = [line for line in text.splitlines() if line.startswith("#")]
    joined = " ".join(header)
    assert "https://www.eff.org/files/2016/07/18/eff_large_wordlist.txt" in joined
    assert "CC BY 3.0" in joined or "Creative Commons Attribution 3.0" in joined
    assert len(WORDS) == 7772
    assert len(set(WORDS)) == 7772
    assert all(word.isalpha() and word.islower() for word in WORDS)
    for dropped in ("drop-down", "felt-tip", "t-shirt", "yo-yo"):
        assert dropped in joined, "the header says which entries were removed"
        assert dropped not in WORDS


def test_every_listed_word_survives_being_typed_back():
    """The EFF list holds four hyphenated words, and a hyphen separates the words of a
    passphrase: such a word would be shown as one and read back as two. None may remain."""
    for word in WORDS:
        assert seal.passphrase_words(word) == [word], word


@pytest.mark.parametrize(
    ("phrase", "reason"),
    [
        ("abacus abide abiding ability", "at least 5"),
        ("abacus abide abiding ability abacus", "repeat"),
        ("abacus abide abiding ability zzzzzz", "not on the EFF"),
        ("", "at least 5"),
        ("   ", "at least 5"),
    ],
)
def test_a_weak_passphrase_is_refused_with_its_reason(phrase, reason):
    with pytest.raises(ValueError, match=reason):
        seal.validate_passphrase(phrase)


def test_a_repeat_is_caught_across_case_and_hyphens():
    with pytest.raises(ValueError, match="repeat"):
        seal.validate_passphrase("Abacus abide-abiding ability ABACUS")


def test_hyphens_and_spaces_give_the_same_passphrase():
    assert seal.validate_passphrase(PASSPHRASE.replace(" ", "-")) == PASSPHRASE
    assert seal.validate_passphrase("  " + PASSPHRASE.upper() + " ") == PASSPHRASE


def test_a_generated_passphrase_is_five_distinct_listed_words():
    for _ in range(50):
        phrase = seal.generate_passphrase()
        assert seal.validate_passphrase(phrase) == phrase.replace("-", " ")
        assert len(phrase.split("-")) == 5, "hyphens between the words"
        assert " " not in phrase


WEAK_ENTRIES = {
    "fewer than 5 words": ("abacus abide abiding ability",) * 2,
    "a repeated word": ("abacus abide abiding ability abacus",) * 2,
    "a word not on the list": ("abacus abide abiding ability zzzzzz",) * 2,
    "two entries that do not match": (PASSPHRASE, "abacus abide abiding ability abdomen zoom"),
}


@pytest.mark.parametrize("entries", WEAK_ENTRIES.values(), ids=WEAK_ENTRIES.keys())
def test_a_weak_or_mismatched_passphrase_sets_nothing(entries, machine, monkeypatch):
    calls, work = machine
    Terminal(monkeypatch, secrets=entries)
    with pytest.raises(seal.SealError):
        seal.run_seal()
    assert calls() == []
    assert not list(work.iterdir())


def test_without_a_terminal_it_refuses_before_reading_anything(machine, monkeypatch):
    calls, work = machine
    terminal = Terminal(monkeypatch, tty=False)
    monkeypatch.setattr(
        seal, "decrypt_private", lambda: pytest.fail("decrypted without a terminal")
    )
    with pytest.raises(seal.SealError, match="terminal"):
        seal.run_seal()
    assert terminal.asked == []
    assert calls() == []


def test_the_command_without_a_terminal_exits_non_zero_and_touches_nothing(tmp_path, monkeypatch):
    """The real CLI, with a pipe for stdin, as an agent shell or CI would run it."""
    calls = install_fakes(tmp_path, monkeypatch)
    env = {**os.environ, "PASSPHRASE": PASSPHRASE, "PYTHONPATH": str(ROOT / "src")}
    done = subprocess.run(
        [sys.executable, "-m", "leaving_denver.cli", "seal"],
        cwd=ROOT,
        env=env,
        input=f"{PASSPHRASE}\n{PASSPHRASE}\n",
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode != 0
    assert "terminal" in (done.stdout + done.stderr)
    assert PASSPHRASE not in done.stdout + done.stderr
    assert calls() == []


def test_a_passphrase_in_any_other_variable_or_in_argv_is_ignored(machine, monkeypatch):
    calls, _ = machine
    other = " ".join(WORDS[-5:])
    for name in ("PASSPHRASE", "SELLER_SEALED_PASSPHRASE", "SELLER_PASSWORD"):
        monkeypatch.setenv(name, other)
    terminal = Terminal(monkeypatch)
    seal.run_seal()
    assert len(terminal.asked) == 2  # the entry twice
    envelope = json.loads(sets(calls())[0]["stdin"])
    assert open_in_node(envelope, PASSPHRASE) is not None
    assert open_in_node(envelope, other) is None
    monkeypatch.setattr(sys, "argv", ["leaving-denver", "seal", "--passphrase", other])
    with pytest.raises(SystemExit) as refused:
        cli.main()
    assert refused.value.code == 2


def test_a_valid_passphrase_sets_the_secret_in_both_environments_on_stdin_only(
    machine, monkeypatch
):
    calls, work = machine
    Terminal(monkeypatch)
    seal.run_seal()
    seen = calls()
    uploads = sets(seen)
    assert [c["argv"] for c in uploads] == [
        ["secret", "set", "SELLER_SEALED", "--env", "production"],
        ["secret", "set", "SELLER_SEALED", "--env", "preview"],
    ]
    for upload in uploads:
        envelope = seal.validate_envelope(upload["stdin"])
        assert upload["stdin"] == uploads[0]["stdin"]
        assert envelope["ct"] not in " ".join(upload["argv"])
    for call in seen:
        argv = " ".join(call["argv"])
        assert PASSPHRASE not in argv
        assert str(SENTINEL_FLOOR) not in argv
    assert not [p for p in work.iterdir()], "the seal wrote a file"


def test_the_envelope_it_sets_opens_to_the_allow_list_with_the_passphrase(machine, monkeypatch):
    calls, _ = machine
    Terminal(monkeypatch)
    seal.run_seal()
    payload = json.loads(open_in_node(sets(calls())[0]["stdin"], PASSPHRASE))
    assert set(payload) == {"floors", "targets", "sales", "tracking", "notes", "sealed_at"}
    assert payload["notes"]["sofa-sleeper"] == SENTINEL_NOTE


def test_a_repository_level_copy_is_removed_after_the_upload(tmp_path, monkeypatch, fixture_data):
    calls = install_fakes(
        tmp_path, monkeypatch, list_output="CLOUDFLARE_API_TOKEN\tx\nSELLER_SEALED\t2026\n"
    )
    Terminal(monkeypatch)
    seal.run_seal()
    last = calls()[-1]["argv"]
    assert last == ["secret", "delete", "SELLER_SEALED"]


def test_no_repository_level_copy_means_no_delete(machine, monkeypatch):
    calls, _ = machine
    Terminal(monkeypatch)
    seal.run_seal()
    assert not [c for c in calls() if c["argv"][:2] == ["secret", "delete"]]


def test_a_failed_upload_is_an_error_not_a_success(tmp_path, monkeypatch, fixture_data):
    calls = install_fakes(tmp_path, monkeypatch, fail_on="--env preview")
    Terminal(monkeypatch)
    with pytest.raises(seal.SealError, match="preview"):
        seal.run_seal()
    assert len(sets(calls())) == 2


FIRST_PROMPT = "Passphrase (Enter to generate one): "


def test_the_first_prompt_offers_to_generate_one(machine, monkeypatch):
    terminal = Terminal(monkeypatch)
    seal.run_seal()
    assert terminal.asked[0] == FIRST_PROMPT


def test_enter_generates_five_hyphenated_words_shown_on_the_terminal_only(
    machine, monkeypatch, capsys
):
    calls, work = machine
    phrase = "-".join(WORDS[-5:])
    monkeypatch.setattr(seal, "generate_passphrase", lambda: phrase)
    terminal = Terminal(monkeypatch, secrets=("", phrase))
    seal.run_seal()
    shown = "".join(terminal.shown)
    assert phrase in shown
    assert "Write this down now. It is not stored anywhere." in shown
    out = capsys.readouterr()
    assert phrase not in out.out + out.err
    assert phrase not in json.dumps(calls())
    assert not list(work.iterdir())
    assert len(terminal.asked) == 2, "the empty entry, then the one typed-back confirmation"
    assert open_in_node(sets(calls())[0]["stdin"], phrase) is not None


def test_the_generated_phrase_is_drawn_from_the_list_and_printed_once(machine, monkeypatch):
    calls, _ = machine
    terminal = Terminal(monkeypatch, secrets=("", ""))
    with pytest.raises(seal.SealError):
        seal.run_seal()  # the confirmation is blank, so this only reads what was shown
    shown = "".join(terminal.shown)
    phrase = next(
        word_run
        for word_run in re.findall(r"[a-z]+(?:-[a-z]+){4}", shown)
        if seal.validate_passphrase(word_run)
    )
    assert shown.count(phrase) == 1
    assert calls() == []


def test_a_confirmation_that_does_not_match_the_generated_phrase_aborts(machine, monkeypatch):
    calls, work = machine
    terminal = Terminal(monkeypatch, secrets=("", PASSPHRASE))
    with pytest.raises(seal.SealError, match="nothing was set"):
        seal.run_seal()
    assert calls() == [], "nothing set, no gh call at all"
    assert not list(work.iterdir())
    assert PASSPHRASE not in "".join(terminal.shown)


def test_a_typed_passphrase_still_needs_both_entries_to_match(machine, monkeypatch):
    calls, _ = machine
    terminal = Terminal(monkeypatch, secrets=(PASSPHRASE, PASSPHRASE))
    seal.run_seal()
    assert terminal.shown == [], "nothing is generated or shown for a typed passphrase"
    assert len(sets(calls())) == 2


def test_a_resealing_never_generates_and_an_empty_entry_aborts(machine, monkeypatch):
    calls, work = machine
    terminal = Terminal(monkeypatch, secrets=("",))
    monkeypatch.setattr(
        seal, "generate_passphrase", lambda: pytest.fail("a routine sale rotated the passphrase")
    )
    with pytest.raises(seal.SealError) as refused:
        seal.run_seal(offer_generation=False)
    assert str(refused.value) == (
        "Type your current passphrase (or run make ci-secrets to make a new one)"
    )
    assert "generate" not in terminal.asked[0].lower()
    assert terminal.shown == []
    assert calls() == []
    assert not list(work.iterdir())


def test_a_resealing_with_the_passphrase_typed_twice_seals(machine, monkeypatch):
    calls, _ = machine
    terminal = Terminal(monkeypatch)
    seal.run_seal(offer_generation=False)
    assert len(terminal.asked) == 2
    assert len(sets(calls())) == 2


def test_the_summary_names_the_size_and_the_time_never_the_envelope(machine, monkeypatch, capsys):
    calls, _ = machine
    Terminal(monkeypatch)
    seal.run_seal()
    out = capsys.readouterr().out
    envelope = sets(calls())[0]["stdin"]
    assert "bytes" in out
    assert json.loads(envelope)["ct"] not in out
    assert PASSPHRASE not in out
    assert SENTINEL_NOTE not in out


# The sops file cannot be read


def test_an_unreadable_sops_file_sets_nothing(tmp_path, monkeypatch):
    calls = install_fakes(tmp_path, monkeypatch)
    Terminal(monkeypatch)

    def unreadable():
        raise RuntimeError("data/private.sops.yaml is not decryptable (sops + age key required)")

    monkeypatch.setattr(seal, "decrypt_private", unreadable)
    with pytest.raises(seal.SealError, match="not decryptable"):
        seal.run_seal()
    assert calls() == []


# Notes are free text of at most 500 characters


def test_a_note_over_500_characters_is_refused(machine, monkeypatch):
    calls, _ = machine
    private = fixture_private()
    private["notes"] = {"sofa-sleeper": "x" * 501}
    monkeypatch.setattr(seal, "decrypt_private", lambda: private)
    Terminal(monkeypatch)
    with pytest.raises(seal.SealError, match="500"):
        seal.run_seal()
    assert calls() == []


@pytest.mark.parametrize(
    "notes", [{"sofa-sleeper": 5}, ["not", "a", "map"], {"sofa-sleeper": None}]
)
def test_a_note_that_is_not_text_is_refused(notes, machine, monkeypatch):
    calls, _ = machine
    private = fixture_private()
    private["notes"] = notes
    monkeypatch.setattr(seal, "decrypt_private", lambda: private)
    Terminal(monkeypatch)
    with pytest.raises(seal.SealError, match="notes"):
        seal.run_seal()
    assert calls() == []


def test_a_note_of_exactly_500_characters_seals(machine, monkeypatch):
    calls, _ = machine
    private = fixture_private()
    private["notes"] = {"sofa-sleeper": "x" * 500}
    monkeypatch.setattr(seal, "decrypt_private", lambda: private)
    Terminal(monkeypatch)
    seal.run_seal()
    assert len(sets(calls())) == 2


# AC5: the size


def worst_case():
    """ADR-007 decision 6: 18 items, each with a floor, a target and a sale; 5 channels with 6
    dates each; 6 price-log entries; a 500-character note."""
    channels = ["facebook", "craigslist", "offerup", "nextdoor", "activebuilding"]
    ids = [f"worst-case-item-name-{n:02d}" for n in range(18)]
    return {
        "floors": {i: 1234 for i in ids},
        "targets": {i: 2345 for i in ids},
        "sales": {i: {"price": 3456, "at": "2026-10-30"} for i in ids},
        "tracking": {
            i: {
                "channels": {c: [f"2026-10-{d:02d}" for d in range(1, 7)] for c in channels},
                "price_log": [{"at": f"2026-10-{d:02d}", "price": 4567} for d in range(1, 7)],
            }
            for i in ids
        },
        "notes": {i: "n" * 500 for i in ids},
    }


def test_the_worst_case_envelope_is_under_the_secret_budget(machine, monkeypatch, capsys):
    calls, _ = machine
    monkeypatch.setattr(seal, "decrypt_private", worst_case)
    Terminal(monkeypatch)
    seal.run_seal()
    size = len(sets(calls())[0]["stdin"].encode())
    with capsys.disabled():
        print(f"\nworst-case envelope: {size} bytes (budget {seal.SIZE_BUDGET})")
    assert size < seal.SIZE_BUDGET == 40_000
    assert size < 49_152, "GitHub's secret limit"


def test_an_envelope_over_the_budget_is_refused_and_nothing_is_set(machine, monkeypatch):
    calls, _ = machine
    big = fixture_private()
    big["tracking"]["sofa-sleeper"]["price_log"] = [
        {"at": "2026-10-01", "price": 100_000 + n} for n in range(2500)
    ]
    monkeypatch.setattr(seal, "decrypt_private", lambda: big)
    Terminal(monkeypatch)
    with pytest.raises(seal.SealError, match="40000|40,000"):
        seal.run_seal()
    assert calls() == []


# AC10: plaintext never leaves the machine


def test_the_python_side_hands_the_node_child_stdin_and_nothing_else(
    machine, monkeypatch, tmp_path
):
    calls, work = machine
    seen = {}
    real_run = subprocess.run

    def spy(cmd, *args, **kwargs):
        if cmd[0] == "node":
            seen["argv"] = cmd
            seen["input"] = kwargs.get("input")
            seen["env"] = kwargs.get("env")
        return real_run(cmd, *args, **kwargs)

    monkeypatch.setattr(seal.subprocess, "run", spy)
    Terminal(monkeypatch)
    seal.run_seal()
    assert PASSPHRASE not in " ".join(seen["argv"])
    assert str(SENTINEL_FLOOR) not in " ".join(seen["argv"])
    assert PASSPHRASE in seen["input"] and str(SENTINEL_FLOOR) in seen["input"]
    assert seen["env"] is not None and seal.PASSPHRASE_ENV not in seen["env"]
    assert not list(work.iterdir())
    assert not list(tmp_path.glob("*.json"))


def test_sops_children_never_get_the_passphrase_variable(machine, monkeypatch, tmp_path):
    """decrypt_private and set_private launch sops: it needs the age key, not the passphrase."""
    from leaving_denver import private_data

    kept = tmp_path / "stand-in.sops.yaml"
    kept.write_text("x: 1\n", encoding="utf-8")
    monkeypatch.setattr(private_data, "PRIVATE_SOPS_YAML", kept)
    monkeypatch.setenv(seal.PASSPHRASE_ENV, "abacus abide abiding ability abdomen")
    seen = []
    real_run = subprocess.run

    def spy(cmd, *args, **kwargs):
        if cmd[0] == "sops":
            seen.append(kwargs.get("env"))
        return real_run(cmd, *args, **kwargs)

    monkeypatch.setattr(private_data.subprocess, "run", spy)
    for action in (
        private_data.decrypt_private,
        lambda: private_data.set_private(["notes", "x"], "y"),
    ):
        try:
            action()
        except (RuntimeError, ValueError):
            pass  # the fake sops need not succeed: only what it was launched with matters
    assert len(seen) == 2, "both sops launches were seen"
    for env in seen:
        assert env is not None and seal.PASSPHRASE_ENV not in env


def test_the_workflows_hold_no_age_key_and_never_mention_sops():
    for workflow in (ROOT / ".github" / "workflows").glob("*.yml"):
        text = workflow.read_text(encoding="utf-8").lower()
        assert "sops_age_key" not in text, workflow.name
        assert "sops" not in text, workflow.name
        assert "age_key" not in text, workflow.name


# The Makefile


def make_dry_run(target):
    return subprocess.run(
        ["make", "-n", "--no-print-directory", target],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_ci_secrets_seals_after_it_sets_the_phone_and_the_token():
    done = make_dry_run("ci-secrets")
    assert done.returncode == 0, done.stderr
    recipe = done.stdout
    assert recipe.index("SELLER_PHONE") < recipe.index("leaving-denver seal")
    assert recipe.rstrip().splitlines()[-1].endswith("leaving-denver seal")


def test_the_panel_target_is_gone():
    done = make_dry_run("panel")
    assert done.returncode != 0
    assert "No rule to make target" in done.stderr


@pytest.mark.parametrize(("stdin", "key"), [(None, "stdin"), ("an-envelope-body", "input")])
def test_gh_never_inherits_the_terminal_and_gets_a_secret_on_stdin_only(stdin, key, monkeypatch):
    """A bare `gh` call must not read the owner's terminal (it would hang a recording), and a
    secret is passed as stdin, never in argv."""
    seen = {}

    def fake_run(argv, **kwargs):
        seen.update(argv=argv, **kwargs)
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.undo()  # the autouse guard replaces seal.gh; this test wants the real one
    monkeypatch.setattr(seal.subprocess, "run", fake_run)
    seal.gh("secret", "list", stdin=stdin)
    assert seen[key] == (subprocess.DEVNULL if stdin is None else stdin)
    assert stdin is None or stdin not in seen["argv"]


def test_tell_writes_to_the_controlling_terminal_never_stdout_or_stderr(monkeypatch, capsys):
    """The real `tell`: its only sink is /dev/tty, so a redirect or a log cannot hold a phrase."""
    import io

    opened = []

    class Sink(io.StringIO):
        def close(self):  # keep the text readable after the `with` block
            pass

    sink = Sink()

    def fake_open(path, mode="r", **kwargs):
        opened.append((path, mode))
        return sink

    monkeypatch.setattr("builtins.open", fake_open)
    seal.tell("-".join(WORDS[:5]))
    assert opened == [("/dev/tty", "w")]
    assert sink.getvalue() == "-".join(WORDS[:5])
    out = capsys.readouterr()
    assert out.out == "" and out.err == ""


def test_tell_refuses_when_there_is_no_terminal_to_write_to(monkeypatch):
    def no_tty(*args, **kwargs):
        raise OSError(6, "No such device or address")

    monkeypatch.setattr("builtins.open", no_tty)
    with pytest.raises(seal.SealError, match="terminal"):
        seal.tell("secret words")


# The owner keeps the passphrase in Bitwarden through `dotf` (ADR-007 decision 3, amended)


def written(path):
    return open(path, encoding="utf-8").read()


def test_enter_with_dotf_saves_the_phrase_to_bitwarden_and_prints_no_value(
    machine_with_dotf, monkeypatch, capfd
):
    calls, work = machine_with_dotf
    phrase = "-".join(WORDS[-5:])
    monkeypatch.setattr(seal, "generate_passphrase", lambda: phrase)
    monkeypatch.setenv("FAKE_DOTF_ECHO", "1")  # even a tool that echoes it must not reach us
    terminal = Terminal(monkeypatch, secrets=("",))
    seal.run_seal()
    saved = calls.dotf()
    assert [c["argv"] for c in saved] == [["secrets", "set", "SELLER_PASSPHRASE", "--yes"]]
    assert saved[0]["stdin"] == phrase, "the value goes on stdin, exactly, never in argv"
    assert phrase not in " ".join(saved[0]["argv"])
    assert terminal.shown == [], "nothing is shown on the terminal when it was saved"
    assert len(terminal.asked) == 1, "no type-back: Bitwarden holds it"
    seen = capfd.readouterr()
    assert phrase not in seen.out + seen.err
    assert not any(word in seen.out + seen.err for word in phrase.split("-"))
    assert "Saved to Bitwarden as SELLER_PASSPHRASE" in seen.out
    assert phrase not in json.dumps(calls())
    assert open_in_node(sets(calls())[0]["stdin"], phrase) is not None
    assert not list(work.iterdir())


def test_the_save_is_announced_without_the_value(machine_with_dotf, monkeypatch, capsys):
    calls, _ = machine_with_dotf
    phrase = "-".join(WORDS[-5:])
    monkeypatch.setattr(seal, "generate_passphrase", lambda: phrase)
    Terminal(monkeypatch, secrets=("",))
    seal.run_seal()
    out = capsys.readouterr().out
    assert "Saved to Bitwarden as SELLER_PASSPHRASE" in out
    assert phrase not in out


def test_a_failed_save_falls_back_to_the_terminal_and_the_typed_back_confirmation(
    machine_with_dotf, monkeypatch, capsys
):
    calls, _ = machine_with_dotf
    phrase = "-".join(WORDS[-5:])
    monkeypatch.setattr(seal, "generate_passphrase", lambda: phrase)
    monkeypatch.setenv("FAKE_DOTF_FAIL", "1")
    terminal = Terminal(monkeypatch, secrets=("", phrase))
    seal.run_seal()
    assert phrase in "".join(terminal.shown)
    assert "Write this down now. It is not stored anywhere." in "".join(terminal.shown)
    out = capsys.readouterr()
    assert "Saved to Bitwarden" not in out.out
    assert phrase not in out.out + out.err
    assert len(sets(calls())) == 2


def test_a_failed_save_and_a_wrong_confirmation_seal_nothing(machine_with_dotf, monkeypatch):
    calls, _ = machine_with_dotf
    monkeypatch.setenv("FAKE_DOTF_FAIL", "1")
    Terminal(monkeypatch, secrets=("", PASSPHRASE))
    with pytest.raises(seal.SealError, match="nothing was set"):
        seal.run_seal()
    assert calls() == []


def test_enter_without_dotf_falls_back_to_the_terminal(machine, monkeypatch, capsys):
    """No dotf on PATH (the plain `machine` has none): the TTY print and the type-back."""
    calls, _ = machine
    phrase = "-".join(WORDS[-5:])
    monkeypatch.setattr(seal, "generate_passphrase", lambda: phrase)
    terminal = Terminal(monkeypatch, secrets=("", phrase))
    seal.run_seal()
    assert phrase in "".join(terminal.shown)
    assert phrase not in capsys.readouterr().out
    assert len(sets(calls())) == 2


def test_a_typed_passphrase_with_dotf_is_offered_a_save(machine_with_dotf, monkeypatch):
    calls, _ = machine_with_dotf
    terminal = Terminal(monkeypatch, lines=("y",))
    seal.run_seal()
    assert any("Save it to Bitwarden? [y/N]" in prompt for prompt in terminal.asked)
    saved = calls.dotf()
    assert [c["argv"] for c in saved] == [["secrets", "set", "SELLER_PASSPHRASE", "--yes"]]
    assert saved[0]["stdin"] == PASSPHRASE.replace(" ", "-")
    assert len(sets(calls())) == 2


def test_a_typed_passphrase_is_not_saved_unless_the_owner_says_yes(machine_with_dotf, monkeypatch):
    calls, _ = machine_with_dotf
    Terminal(monkeypatch, lines=("",))
    seal.run_seal()
    assert calls.dotf() == []
    assert len(sets(calls())) == 2


def test_a_typed_passphrase_without_dotf_is_not_offered_a_save(machine, monkeypatch):
    terminal = Terminal(monkeypatch)
    seal.run_seal()
    assert not any("Bitwarden" in prompt for prompt in terminal.asked)


def test_a_save_the_owner_asked_for_that_fails_seals_nothing(machine_with_dotf, monkeypatch):
    calls, _ = machine_with_dotf
    monkeypatch.setenv("FAKE_DOTF_FAIL", "1")
    Terminal(monkeypatch, lines=("y",))
    with pytest.raises(seal.SealError, match="nothing was set"):
        seal.run_seal()
    assert calls() == []


@pytest.mark.parametrize("offer_generation", [True, False])
def test_the_passphrase_in_the_environment_is_used_without_a_prompt(
    offer_generation, machine, monkeypatch, capsys
):
    """What `dotf secrets run --only SELLER_PASSPHRASE -- make ...` gives the target."""
    calls, _ = machine
    monkeypatch.setenv("SELLER_PASSPHRASE", "-".join(PASSPHRASE.split()))
    terminal = Terminal(monkeypatch, secrets=())
    monkeypatch.setattr(
        seal, "generate_passphrase", lambda: pytest.fail("generated with one in the environment")
    )
    seal.run_seal(offer_generation=offer_generation)
    assert terminal.asked == []
    assert open_in_node(sets(calls())[0]["stdin"], PASSPHRASE) is not None
    out = capsys.readouterr()
    assert not any(word in out.out + out.err for word in PASSPHRASE.split())


@pytest.mark.parametrize(
    ("value", "reason"),
    [
        ("abacus abide abiding ability", "at least 5"),
        ("abacus abide abiding ability abacus", "repeat"),
        ("abacus abide abiding ability zzzzzz", "not on the EFF"),
    ],
)
def test_a_weak_passphrase_in_the_environment_is_refused_without_echoing_it(
    value, reason, machine, monkeypatch, capsys
):
    calls, _ = machine
    monkeypatch.setenv("SELLER_PASSPHRASE", value)
    terminal = Terminal(monkeypatch, secrets=())
    with pytest.raises(seal.SealError, match=reason) as refused:
        seal.run_seal(offer_generation=False)
    assert "SELLER_PASSPHRASE" in str(refused.value)
    assert value not in str(refused.value)
    assert terminal.asked == [] and calls() == []


@pytest.mark.parametrize("blank", ["", "   "])
def test_a_blank_environment_value_means_none_and_the_prompt_runs(blank, machine, monkeypatch):
    calls, _ = machine
    monkeypatch.setenv("SELLER_PASSPHRASE", blank)
    terminal = Terminal(monkeypatch)
    seal.run_seal()
    assert len(terminal.asked) == 2
    assert len(sets(calls())) == 2


def test_the_environment_passphrase_does_not_lift_the_terminal_rule(machine, monkeypatch):
    calls, _ = machine
    monkeypatch.setenv("SELLER_PASSPHRASE", PASSPHRASE)
    Terminal(monkeypatch, tty=False)
    with pytest.raises(seal.SealError, match="terminal"):
        seal.run_seal()
    assert calls() == []


def test_the_children_do_not_inherit_the_passphrase_from_the_environment(
    machine_with_dotf, monkeypatch
):
    """Node and gh run with SELLER_PASSPHRASE removed from their environment."""
    calls, _ = machine_with_dotf
    seen = {}
    real_run = subprocess.run

    def spy(cmd, *args, **kwargs):
        seen[cmd[0]] = kwargs.get("env")
        return real_run(cmd, *args, **kwargs)

    monkeypatch.setattr(seal.subprocess, "run", spy)
    monkeypatch.setenv("SELLER_PASSPHRASE", PASSPHRASE)
    Terminal(monkeypatch, secrets=())
    seal.run_seal()
    assert {"node", "gh"} <= set(seen)
    for name, env in seen.items():
        assert env is not None and "SELLER_PASSPHRASE" not in env, name
    assert len(sets(calls())) == 2


def test_dotf_runs_without_the_passphrase_in_its_environment(machine_with_dotf, monkeypatch):
    """The third child. With SELLER_PASSPHRASE set the seal never needs dotf, so the call is
    made directly: the fake dotf logs the names in the environment it was started with."""
    calls, _ = machine_with_dotf
    monkeypatch.setenv("SELLER_PASSPHRASE", PASSPHRASE)
    assert seal.save_to_bitwarden("-".join(WORDS[:5])) is True
    started = calls.dotf()
    assert len(started) == 1
    assert "SELLER_PASSPHRASE" not in started[0]["env"]
    assert "PATH" in started[0]["env"], "the rest of the environment is still passed on"


# Round two of the review (F1, F3, F5, F6, F7, F9)

FIXED_REASON = "`dotf secrets set SELLER_PASSPHRASE` failed; run it by hand to see why"
CANARY = "FAKE-DOTF-STDERR-CANARY"


def test_the_save_passes_yes_so_dotf_may_create_the_absent_item(machine_with_dotf, monkeypatch):
    """dotf cannot ask on a pipe: without --yes it refuses to create the item, and the first run
    would always fall back to the terminal. The fake dotf refuses the same way."""
    calls, _ = machine_with_dotf
    phrase = "-".join(WORDS[-5:])
    monkeypatch.setattr(seal, "generate_passphrase", lambda: phrase)
    terminal = Terminal(monkeypatch, secrets=("",))
    seal.run_seal()
    saved = calls.dotf()
    assert saved[0]["argv"] == ["secrets", "set", "SELLER_PASSPHRASE", "--yes"]
    assert terminal.shown == [], "saved, so no terminal fallback"


def test_the_fake_dotf_refuses_to_create_without_yes(machine_with_dotf):
    """The stand-in is only worth anything if it behaves like dotf on this point."""
    refused = subprocess.run(
        ["dotf", "secrets", "set", "SELLER_PASSPHRASE"], input="x", capture_output=True, text=True
    )
    assert refused.returncode != 0
    assert "--yes" in refused.stderr


def test_a_failed_save_names_a_fixed_reason_and_never_forwards_dotfs_stderr(
    machine_with_dotf, monkeypatch, capfd
):
    calls, _ = machine_with_dotf
    phrase = "-".join(WORDS[-5:])
    monkeypatch.setattr(seal, "generate_passphrase", lambda: phrase)
    monkeypatch.setenv("FAKE_DOTF_FAIL", "1")
    monkeypatch.setenv("FAKE_DOTF_ECHO", "1")
    Terminal(monkeypatch, secrets=("", phrase))
    seal.run_seal()
    seen = capfd.readouterr()
    assert FIXED_REASON in seen.err
    assert CANARY not in seen.out + seen.err
    assert phrase not in seen.out + seen.err


def test_a_requested_save_that_fails_says_the_fixed_reason_and_sets_nothing(
    machine_with_dotf, monkeypatch
):
    calls, _ = machine_with_dotf
    monkeypatch.setenv("FAKE_DOTF_FAIL", "1")
    Terminal(monkeypatch, lines=("y",))
    with pytest.raises(seal.SealError) as refused:
        seal.run_seal()
    assert FIXED_REASON in str(refused.value)
    assert CANARY not in str(refused.value)
    assert calls() == []


def times(entries):
    return [entry["t"] for entry in entries]


def test_the_order_is_seal_then_bitwarden_then_the_secret(machine_with_dotf, monkeypatch):
    calls, _ = machine_with_dotf
    order = []
    real_seal = seal.seal_with_node

    def sealed(*args, **kwargs):
        order.append("seal")
        return real_seal(*args, **kwargs)

    monkeypatch.setattr(seal, "seal_with_node", sealed)
    phrase = "-".join(WORDS[-5:])
    monkeypatch.setattr(seal, "generate_passphrase", lambda: phrase)
    Terminal(monkeypatch, secrets=("",))
    seal.run_seal()
    assert order == ["seal"]
    saved, uploaded = times(calls.dotf()), times(sets(calls()))
    assert len(saved) == 1 and len(uploaded) == 2
    assert saved[0] < min(uploaded), "Bitwarden is written before the secret is set"


def test_a_save_that_fails_leaves_the_secret_untouched_even_though_it_was_sealed(
    machine_with_dotf, monkeypatch
):
    calls, _ = machine_with_dotf
    sealed = []
    real_seal = seal.seal_with_node
    monkeypatch.setattr(
        seal, "seal_with_node", lambda *a, **k: sealed.append(1) or real_seal(*a, **k)
    )
    monkeypatch.setenv("FAKE_DOTF_FAIL", "1")
    Terminal(monkeypatch, secrets=("", PASSPHRASE))
    with pytest.raises(seal.SealError):
        seal.run_seal()
    assert sealed == [1]
    assert calls() == []


def test_an_upload_that_fails_after_a_saved_passphrase_says_bitwarden_holds_the_new_one(
    tmp_path, monkeypatch, fixture_data
):
    calls = install_fakes(tmp_path, monkeypatch, dotf=True, fail_on="--env production")
    monkeypatch.chdir(tmp_path)
    Terminal(monkeypatch, secrets=("",))
    with pytest.raises(seal.SealError) as failed:
        seal.run_seal()
    message = str(failed.value)
    assert "Bitwarden now holds the new passphrase" in message
    assert "run make ci-secrets again" in message
    assert len(calls.dotf()) == 1


def test_an_upload_that_fails_after_no_save_does_not_mention_bitwarden(
    tmp_path, monkeypatch, fixture_data
):
    install_fakes(tmp_path, monkeypatch, fail_on="--env production")
    monkeypatch.chdir(tmp_path)
    Terminal(monkeypatch)
    with pytest.raises(seal.SealError) as failed:
        seal.run_seal()
    assert "Bitwarden" not in str(failed.value)


def test_a_repository_copy_that_cannot_be_deleted_is_an_error(tmp_path, monkeypatch, fixture_data):
    install_fakes(
        tmp_path, monkeypatch, list_output="SELLER_SEALED\tUpdated\n", fail_on="secret delete"
    )
    monkeypatch.chdir(tmp_path)
    Terminal(monkeypatch)
    with pytest.raises(seal.SealError, match="repository-level"):
        seal.run_seal()


def test_node_failing_never_puts_the_payload_or_the_passphrase_in_the_error(
    tmp_path, monkeypatch, capfd
):
    """Node echoes the offending stdin line when JSON.parse fails; nothing of that may travel."""
    sentinel = "sentinel-passphrase-quokka-8812"
    echo = tmp_path / "echo.mjs"
    echo.write_text(
        "let raw = ''; for await (const c of process.stdin) raw += c;"
        " console.error('SyntaxError near ' + raw); process.exit(1);",
        encoding="utf-8",
    )
    monkeypatch.setattr(seal, "SEAL_SCRIPT", echo)
    with pytest.raises(seal.SealError) as failed:
        seal.seal_with_node({"floors": {"x": 7310987}}, sentinel)
    seen = capfd.readouterr()
    for text in (str(failed.value), seen.out, seen.err):
        assert sentinel not in text
        assert "7310987" not in text
        assert "SyntaxError" not in text
    assert "exit" in str(failed.value)


def test_a_payload_json_cannot_carry_is_refused_before_node_runs(monkeypatch):
    monkeypatch.setattr(
        subprocess, "run", lambda *a, **k: pytest.fail("node ran with a payload NaN would break")
    )
    with pytest.raises(seal.SealError, match="JSON"):
        seal.seal_with_node({"floors": {"x": float("nan")}}, PASSPHRASE)


def test_the_builder_caps_the_iteration_count():
    assert seal.MAX_ITERATIONS == 10_000_000
    envelope = {
        "v": 1,
        "kdf": "PBKDF2-SHA256",
        "iter": seal.MAX_ITERATIONS,
        "salt": "AAAAAAAAAAAAAAAAAAAAAA==",
        "iv": "AAAAAAAAAAAAAAAA",
        "ct": "A" * 22 + "==",
    }
    assert seal.envelope_problem(envelope) is None
    assert "iter" in seal.envelope_problem({**envelope, "iter": seal.MAX_ITERATIONS + 1})


def test_a_resealing_reminds_that_the_phone_passphrase_is_replaced(machine, monkeypatch, capsys):
    calls, _ = machine
    Terminal(monkeypatch)
    seal.run_seal(offer_generation=False)
    assert (
        "Sealing with this passphrase replaces the one your phone uses" in capsys.readouterr().out
    )


def test_a_new_passphrase_from_ci_secrets_needs_no_such_reminder(machine, monkeypatch, capsys):
    Terminal(monkeypatch)
    seal.run_seal()
    assert "replaces the one your phone uses" not in capsys.readouterr().out
