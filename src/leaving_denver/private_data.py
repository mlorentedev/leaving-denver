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
from datetime import date
from typing import Any

from leaving_denver.config import PRIVATE_SOPS_YAML


def decrypt_private() -> dict[str, Any]:
    """Decrypt the private file in process. Raises when it cannot be read.

    For anything that must not mistake "unreadable" for "empty": a write built on {} would
    replace what the file holds."""
    if not PRIVATE_SOPS_YAML.exists():
        raise RuntimeError(f"{PRIVATE_SOPS_YAML} does not exist")
    if not shutil.which("sops"):
        raise RuntimeError("sops is not installed")
    res = subprocess.run(
        ["sops", "--decrypt", "--output-type", "json", str(PRIVATE_SOPS_YAML)],
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        raise RuntimeError("data/private.sops.yaml is not decryptable (sops + age key required)")
    return json.loads(res.stdout)


def load_private() -> dict[str, Any]:
    """Decrypt the private file. Returns {} when it is absent or not decryptable."""
    try:
        return decrypt_private()
    except RuntimeError:
        return {}


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


def set_private(keys: list[str | int], value: Any) -> None:
    """Set one key of the encrypted file with `sops set`, creating the path when it is new.

    The value goes on stdin as JSON, not argv, so it never shows in the process table. `sops set`
    rejects a bare JSON list as the value, so a list grows by setting its next index."""
    if not shutil.which("sops"):
        raise RuntimeError("sops is not installed")
    index = "".join(f"[{json.dumps(key)}]" for key in keys)
    res = subprocess.run(
        ["sops", "set", "--value-stdin", str(PRIVATE_SOPS_YAML), index],
        input=json.dumps(value),
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        raise RuntimeError(f"sops set failed: {res.stderr.strip()}")


def record_sale(item_id: str, price: int | None, on: date) -> None:
    """Keep what an item sold for, and when, in the encrypted file, never in the public repo."""
    sale: dict[str, Any] = {"at": on.isoformat()}
    if price is not None:
        sale = {"price": int(price), **sale}
    set_private(["sales", item_id], sale)


def append_tracking(item_id: str, path: list[str], entry: Any) -> None:
    """Append to a list kept under tracking.<item>: set the entry at the list's next index.

    Reads the file first and refuses to write if it cannot be read: an index counted on an
    unreadable file would overwrite an entry already there."""
    node: Any = decrypt_private().get("tracking", {}).get(item_id, {})
    for key in path:
        node = (node or {}).get(key)
    set_private(["tracking", item_id, *path, len(node or [])], entry)


def record_post(item_id: str, channel: str, on: date) -> None:
    """A posting, or a renewal, of the item on a channel."""
    append_tracking(item_id, ["channels", channel], on.isoformat())


def record_price(item_id: str, price: int, on: date) -> None:
    """A change of the asking price, for judging afterwards whether the drops worked."""
    append_tracking(item_id, ["price_log"], {"at": on.isoformat(), "price": int(price)})
