"""
Private seller data (reserve floors, phone) kept out of the public tree.

Source of truth is data/private.sops.yaml, encrypted with sops/age. The public
build only needs the phone, which can also come from the SELLER_PHONE env var
(how CI gets it, as a repository secret). Floors are only ever needed locally,
by the private seller workspace and `leaving-denver drops`.
"""

import json
import os
import re
import shutil
import subprocess
from typing import Any

from leaving_denver.config import PRIVATE_SOPS_YAML


def load_private() -> dict[str, Any]:
    """Decrypt the private file. Returns {} when it is absent or not decryptable."""
    if not PRIVATE_SOPS_YAML.exists() or not shutil.which("sops"):
        return {}
    res = subprocess.run(
        ["sops", "--decrypt", "--output-type", "json", str(PRIVATE_SOPS_YAML)],
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        return {}
    return json.loads(res.stdout)


def seller_phone(private: dict[str, Any] | None = None) -> str | None:
    env = os.environ.get("SELLER_PHONE")
    if env:
        return env
    if private is None:
        private = load_private()
    return private.get("seller", {}).get("phone")


def phone_parts(phone: str) -> dict[str, str]:
    """Split a NANP number into the fragments the public page assembles at runtime."""
    digits = re.sub(r"\D", "", phone)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10:
        raise ValueError("SELLER_PHONE must be a 10-digit US number (optionally +1)")
    return {"cc": "+1", "area": digits[:3], "prefix": digits[3:6], "line": digits[6:]}


def floors(private: dict[str, Any] | None = None) -> dict[str, int]:
    if private is None:
        private = load_private()
    return private.get("floors", {})


def record_sale(item_id: str, price: int) -> None:
    """Keep what an item actually sold for in the encrypted file, never in the public repo."""
    if not shutil.which("sops"):
        raise RuntimeError("sops is not installed")
    # The price goes on stdin, not argv, so it never shows in the process table.
    res = subprocess.run(
        ["sops", "set", "--value-stdin", str(PRIVATE_SOPS_YAML), f'["sales"]["{item_id}"]'],
        input=str(int(price)),
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        raise RuntimeError(f"sops set failed: {res.stderr.strip()}")
