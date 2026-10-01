"""Shared guards for the whole suite."""

import pytest

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
