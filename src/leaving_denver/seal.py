"""
Sealing the private seller data for /seller/ (ADR-007).

Plaintext never leaves the owner's machine: the allow-listed payload and the passphrase reach
a Node child on stdin only (WebCrypto, the same code the page opens it with), and only the
envelope goes on to `gh secret set`. Nothing here writes a file or prints a private value.
"""

import base64
import binascii
import functools
import getpass
import json
import re
import secrets
import subprocess
import sys
from datetime import UTC, datetime
from typing import Any

from leaving_denver.config import ASSETS_DIR, WORDLIST_FILE
from leaving_denver.private_data import decrypt_private

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

# GitHub caps a secret at 48 KB (49,152 bytes); the seal refuses well before that.
SIZE_BUDGET = 40_000
ENVIRONMENTS = ("production", "preview")
SECRET_NAME = "SELLER_SEALED"
PASSPHRASE_WORDS = 5
DEPLOY_DISPATCH = ["workflow", "run", "ci.yml", "--ref", "main", "-f", "branch=main"]


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


# The passphrase (ADR-007 decision 4)


@functools.cache
def load_wordlist() -> tuple[str, ...]:
    """The EFF large wordlist: one word per line, "#" lines are the file's header."""
    lines = WORDLIST_FILE.read_text(encoding="utf-8").splitlines()
    return tuple(line for line in lines if line and not line.startswith("#"))


def passphrase_words(text: str) -> list[str]:
    """The words of a phrase typed with spaces or hyphens, in any case (as the page reads it)."""
    return [word for word in re.split(r"[\s-]+", text.lower()) if word]


def validate_passphrase(text: str) -> str:
    """The phrase as one space-separated string, or a ValueError naming what is wrong.

    The word count, the list and the repeats are all that can be measured: whether the words
    were chosen at random cannot be, which is why the target offers to generate them."""
    words = passphrase_words(text)
    if len(words) < PASSPHRASE_WORDS:
        raise ValueError(f"it needs at least {PASSPHRASE_WORDS} words")
    if len(set(words)) != len(words):
        raise ValueError("a word repeats")
    listed = set(load_wordlist())
    if any(word not in listed for word in words):
        raise ValueError("a word is not on the EFF large wordlist")
    return " ".join(words)


def generate_passphrase(count: int = PASSPHRASE_WORDS) -> str:
    """`count` distinct words drawn uniformly from the list with the OS's random source."""
    words = load_wordlist()
    chosen: list[str] = []
    while len(chosen) < count:
        word = secrets.choice(words)
        if word not in chosen:
            chosen.append(word)
    return " ".join(chosen)


# The terminal. Each is a module attribute so a test can stand in for the owner.


def has_tty() -> bool:
    """True when stdin is a terminal. An agent shell, CI and a pipe are not."""
    return sys.stdin.isatty()


def prompt_secret(prompt: str) -> str:
    """One line with echo off (getpass reads /dev/tty, never argv or the environment)."""
    return getpass.getpass(prompt)


def prompt_line(prompt: str) -> str:
    return input(prompt)


def tell(text: str) -> None:
    """Show text on the terminal itself, so a redirect of stdout or stderr cannot capture it."""
    try:
        with open("/dev/tty", "w", encoding="utf-8") as terminal:
            terminal.write(text)
    except OSError as err:
        raise SealError("cannot write to the terminal") from err


def ask_passphrase(offer_generation: bool = True) -> str:
    """The passphrase, typed twice. It can first be generated and shown on the terminal only:
    it is still typed back, which is how the owner proves it was written down."""
    if offer_generation and prompt_line("Generate a new passphrase? [y/N] ").strip().lower() in (
        "y",
        "yes",
    ):
        tell(
            "\nNew passphrase (keep it in your password manager; it is not stored anywhere):\n\n"
            f"    {generate_passphrase()}\n\nType it twice below.\n"
        )
    first = prompt_secret("Passphrase: ")
    second = prompt_secret("Again: ")
    if passphrase_words(first) != passphrase_words(second):
        raise SealError("the two entries do not match")
    try:
        return validate_passphrase(first)
    except ValueError as err:
        raise SealError(f"that passphrase is refused: {err}") from err


# The payload and the envelope


def check_notes(notes: Any) -> None:
    """Notes are free text of at most NOTE_LIMIT characters, one per item id."""
    if not isinstance(notes, dict) or not all(isinstance(text, str) for text in notes.values()):
        raise SealError("notes must map each item id to text")
    for item_id, text in notes.items():
        if len(text) > NOTE_LIMIT:
            raise SealError(f"the note for {item_id} is over {NOTE_LIMIT} characters")


def check_envelope(envelope: str) -> int:
    """The envelope's size in bytes once it is well formed and inside the budget."""
    try:
        validate_envelope(envelope)
    except ValueError as err:
        raise SealError(f"the sealer produced a malformed envelope: {err}") from err
    size = len(envelope.encode("utf-8"))
    if size > SIZE_BUDGET:
        raise SealError(
            f"the envelope is {size} bytes, over the {SIZE_BUDGET} byte budget: nothing was set"
        )
    return size


# GitHub


def gh(*args: str, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    """Run gh. With no `stdin` it gets none (never the terminal: a prompt would hang a recording)."""
    feed = {"input": stdin} if stdin is not None else {"stdin": subprocess.DEVNULL}
    try:
        return subprocess.run(["gh", *args], capture_output=True, text=True, **feed)
    except OSError as err:
        raise SealError(f"gh could not run ({err.strerror})") from err


def upload_secret(envelope: str) -> None:
    """Set SELLER_SEALED in both environments (the envelope on stdin, never argv), then remove
    any repository-level copy: a repository secret would reach every workflow."""
    for environment in ENVIRONMENTS:
        done = gh("secret", "set", SECRET_NAME, "--env", environment, stdin=envelope)
        if done.returncode != 0:
            raise SealError(
                f"gh could not set {SECRET_NAME} in the {environment} environment: "
                f"{done.stderr.strip()[:200]}"
            )
    listed = gh("secret", "list")
    if listed.returncode != 0:
        raise SealError(f"gh could not list the repository secrets: {listed.stderr.strip()[:200]}")
    if any(line.split()[:1] == [SECRET_NAME] for line in listed.stdout.splitlines()):
        gh("secret", "delete", SECRET_NAME)


def dispatch_deploy() -> None:
    """Deploy main so the page carries the new envelope (a deploy reads the secret as it is
    when the run starts)."""
    done = gh(*DEPLOY_DISPATCH)
    if done.returncode != 0:
        raise SealError(f"gh could not dispatch the deploy: {done.stderr.strip()[:200]}")


# The command


def run_seal(offer_generation: bool = True) -> None:
    """Seal the private data and set the secret in both environments.

    The terminal is checked first, before anything is decrypted: an agent shell has none."""
    if not has_tty():
        raise SealError(
            "sealing needs a terminal: it asks for the passphrase there, and only there"
        )
    try:
        payload = allowlisted_payload(decrypt_private())
    except RuntimeError as err:
        raise SealError(str(err)) from err
    check_notes(payload["notes"])
    passphrase = ask_passphrase(offer_generation)
    envelope = seal_with_node(payload, passphrase)
    size = check_envelope(envelope)
    upload_secret(envelope)
    print(
        f"Sealed private data as of {payload['sealed_at']} ({size} bytes) into {SECRET_NAME} "
        f"for {' and '.join(ENVIRONMENTS)}. Deploy for the page to carry it."
    )


def offer_update() -> None:
    """After a record: ask once whether to update /seller/ now. The default is no, and so is
    any run without a terminal."""
    if not has_tty():
        return
    answer = prompt_line("Update /seller/ now (seal, set the secret, deploy)? [y/N] ")
    if answer.strip().lower() not in ("y", "yes"):
        return
    run_seal(offer_generation=False)
    dispatch_deploy()
    print("Deploy dispatched.")
