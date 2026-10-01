"""
Sealing the private seller data for /seller/ (ADR-007).

Plaintext never leaves the owner's machine: the allow-listed payload and the passphrase reach
a Node child on stdin only (WebCrypto, the same code the page opens it with), and only the
envelope goes on to `gh secret set`. Nothing here writes a file or prints a private value.
"""

import base64
import binascii
import json
import subprocess
from datetime import UTC, datetime
from typing import Any

from leaving_denver.config import ASSETS_DIR

SEAL_SCRIPT = ASSETS_DIR / "seal.mjs"

# What goes into the envelope; everything else in the sops file (the phone, the Cloudflare
# token) stays out. `sealed_at` is the moment of the seal, hidden inside the ciphertext too.
ALLOW_LIST = ("floors", "targets", "sales", "tracking", "notes")
NOTE_LIMIT = 500

# The envelope the builder accepts (ADR-007 decision 4).
ENVELOPE_VERSION = 1
ENVELOPE_KDF = "PBKDF2-SHA256"
MIN_ITERATIONS = 600_000
SALT_BYTES = 16
IV_BYTES = 12
TAG_BYTES = 16
ENVELOPE_KEYS = {"v", "kdf", "iter", "salt", "iv", "ct"}


class SealError(RuntimeError):
    """The seal cannot go on. The message never holds a passphrase or a payload value."""


def seal_with_node(payload: dict[str, Any] | str, passphrase: str) -> str:
    """The envelope (JSON text) for a payload, sealed by Node's WebCrypto.

    The child opens its own envelope and compares it with the payload before answering."""
    plaintext = payload if isinstance(payload, dict) else json.loads(payload)
    try:
        child = subprocess.run(
            ["node", str(SEAL_SCRIPT)],
            input=json.dumps({"payload": plaintext, "passphrase": passphrase}),
            capture_output=True,
            text=True,
        )
    except OSError as err:
        raise SealError(f"node could not run ({err.strerror})") from err
    if child.returncode != 0:
        # stderr is the script's own fixed message or Node's trace of it: never the payload.
        raise SealError(f"the Node sealer failed: {child.stderr.strip()[:300]}")
    return child.stdout


def allowlisted_payload(private: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    """The decrypted private data cut down to the allow-list, stamped with the seal's time.

    A section that is absent or null seals as empty, so the page can read every key."""
    sealed_at = (now or datetime.now(UTC)).astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload: dict[str, Any] = {key: private.get(key) or {} for key in ALLOW_LIST}
    payload["sealed_at"] = sealed_at
    return payload


def b64_length(value: Any) -> int | None:
    """The byte length of a base64 string, or None when it is not valid base64."""
    if not isinstance(value, str):
        return None
    try:
        return len(base64.b64decode(value, validate=True))
    except (binascii.Error, ValueError):
        return None


def envelope_problem(envelope: Any) -> str | None:
    """Why an envelope is malformed, or None. Names the field, never its value."""
    if not isinstance(envelope, dict) or set(envelope) != ENVELOPE_KEYS:
        return "it is not an object with exactly v, kdf, iter, salt, iv and ct"
    iterations = envelope["iter"]
    checks = (
        (envelope["v"] == ENVELOPE_VERSION and type(envelope["v"]) is int, "v is not 1"),
        (envelope["kdf"] == ENVELOPE_KDF, f"kdf is not {ENVELOPE_KDF}"),
        (
            type(iterations) is int and iterations >= MIN_ITERATIONS,
            f"iter is not an integer of at least {MIN_ITERATIONS}",
        ),
        (b64_length(envelope["salt"]) == SALT_BYTES, f"salt is not {SALT_BYTES} bytes of base64"),
        (b64_length(envelope["iv"]) == IV_BYTES, f"iv is not {IV_BYTES} bytes of base64"),
        (
            (b64_length(envelope["ct"]) or 0) >= TAG_BYTES,
            f"ct is not base64 of at least the {TAG_BYTES}-byte tag",
        ),
    )
    return next((problem for holds, problem in checks if not holds), None)


def validate_envelope(text: str) -> dict[str, Any]:
    """The envelope parsed and checked, or a ValueError that says why (never the envelope)."""
    try:
        envelope = json.loads(text)
    except ValueError as err:
        raise ValueError("it is not JSON") from err
    problem = envelope_problem(envelope)
    if problem:
        raise ValueError(problem)
    return envelope
