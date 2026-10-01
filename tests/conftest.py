"""Shared guards for the whole suite."""

import shutil

import pytest

from leaving_denver import config, private_data, seal


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
    dispatch a deploy on the real repository.

    The terminal is off unless a test turns it on, and `gh` runs only when PATH resolves it to
    a fake (tests/sealed_helpers.install_fakes puts one in a `fake-bin` directory)."""
    real = seal.gh

    def guarded(*args, **kwargs):
        found = shutil.which("gh") or ""
        if "fake-bin" not in found:
            pytest.fail(f"a test reached the real gh: gh {' '.join(args[:2])}")
        return real(*args, **kwargs)

    monkeypatch.setattr(seal, "has_tty", lambda: False)
    monkeypatch.setattr(seal, "gh", guarded)
