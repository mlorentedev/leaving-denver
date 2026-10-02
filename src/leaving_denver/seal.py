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
import os
import re
import secrets
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from leaving_denver.config import ASSETS_DIR, WORDLIST_FILE
from leaving_denver.private_data import PASSPHRASE_ENV, child_env, decrypt_private

SEAL_SCRIPT = ASSETS_DIR / "seal.mjs"

# What goes into the envelope; everything else in the sops file (the phone, the Cloudflare
# token) stays out. `sealed_at` is the moment of the seal, hidden inside the ciphertext too.
ALLOW_LIST = ("floors", "targets", "sales", "tracking", "notes")
NOTE_LIMIT = 500

# The envelope the builder accepts (ADR-007 decision 4).
ENVELOPE_VERSION = 1
ENVELOPE_KDF = "PBKDF2-SHA256"
MIN_ITERATIONS = 600_000
# A cap too: an envelope with a huge count would make every unlock hang the phone.
MAX_ITERATIONS = 10_000_000
SALT_BYTES = 16
IV_BYTES = 12
TAG_BYTES = 16
ENVELOPE_KEYS = {"v", "kdf", "iter", "salt", "iv", "ct"}

# GitHub caps a secret at 48 KB (49,152 bytes); the seal refuses well before that.
SIZE_BUDGET = 40_000
ENVIRONMENTS = ("production", "preview")
SECRET_NAME = "SELLER_SEALED"
PASSPHRASE_WORDS = 5
# The bitwarden id is the dotfiles secret's name; PASSPHRASE_ENV (private_data) is the variable
# `dotf secrets run --only SELLER_PASSPHRASE -- make ...` injects into one child alone.
BITWARDEN_ID = "SELLER_PASSPHRASE"
DEPLOY_DISPATCH = ["workflow", "run", "ci.yml", "--ref", "main", "-f", "branch=main"]


class SealError(RuntimeError):
    """The seal cannot go on. The message never holds a passphrase or a payload value."""


def seal_with_node(payload: dict[str, Any] | str, passphrase: str) -> str:
    """The envelope (JSON text) for a payload, sealed by Node's WebCrypto.

    The child opens its own envelope and compares it with the payload before answering."""
    plaintext = payload if isinstance(payload, dict) else json.loads(payload)
    try:
        # No NaN or Infinity: JSON.parse would refuse them, and Node's SyntaxError echoes the line.
        feed = json.dumps({"payload": plaintext, "passphrase": passphrase}, allow_nan=False)
    except ValueError as err:
        raise SealError("the payload cannot be written as JSON") from err
    try:
        child = subprocess.run(
            ["node", str(SEAL_SCRIPT)],
            input=feed,
            capture_output=True,
            text=True,
            env=child_env(),
        )
    except OSError as err:
        raise SealError(f"node could not run ({err.strerror})") from err
    if child.returncode != 0:
        # Never its stderr: on a parse failure Node echoes the stdin line, payload and passphrase.
        raise SealError(f"the Node sealer failed (exit {child.returncode})")
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
            type(iterations) is int and MIN_ITERATIONS <= iterations <= MAX_ITERATIONS,
            f"iter is not an integer from {MIN_ITERATIONS} to {MAX_ITERATIONS}",
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
    """`count` distinct words drawn uniformly from the list with the OS's random source, joined
    by hyphens (one token to write down; the page reads hyphens and spaces alike)."""
    words = load_wordlist()
    chosen: list[str] = []
    while len(chosen) < count:
        word = secrets.choice(words)
        if word not in chosen:
            chosen.append(word)
    return "-".join(chosen)


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


FIRST_PROMPT = "Passphrase (Enter to generate one): "
RESEAL_PROMPT = "Passphrase: "
CURRENT_PASSPHRASE_HINT = "Type your current passphrase (or run make ci-secrets to make a new one)"
SAVED = f"Saved to Bitwarden as {BITWARDEN_ID}"
# dotf's own words are never relayed: this is all that is said when a save fails.
SAVE_FAILED = f"`dotf secrets set {BITWARDEN_ID}` failed; run it by hand to see why"
RESEAL_REMINDER = "Sealing with this passphrase replaces the one your phone uses."


def passphrase_from_environment() -> str | None:
    """The passphrase `dotf secrets run` put in SELLER_PASSPHRASE, validated like a typed one.

    There is no telling a variable injected by dotf from one set by hand, so the check is the
    same either way: five or more distinct EFF words. A blank value is none. The message never
    holds the value."""
    raw = os.environ.get(PASSPHRASE_ENV, "")
    if not raw.strip():
        return None
    try:
        return validate_passphrase(raw)
    except ValueError as err:
        raise SealError(f"{PASSPHRASE_ENV} is refused: {err}") from err


def hyphenated(passphrase: str) -> str:
    return "-".join(passphrase_words(passphrase))


@dataclass(frozen=True)
class Choice:
    """The passphrase for this seal and what is still owed to Bitwarden once it is sealed.

    `save` is set when it is to be stored; `generated` when the owner has not seen it yet, so
    a failed save falls back to showing it, rather than losing the only copy."""

    passphrase: str
    save: bool = False
    generated: bool = False


def ask_passphrase(offer_generation: bool = True) -> Choice:
    """The passphrase for this seal: from SELLER_PASSPHRASE, typed, or generated.

    - SELLER_PASSPHRASE, when set, is used without a prompt.
    - Otherwise the owner types it twice. Where `offer_generation` (`make ci-secrets` only) Enter
      instead generates a new one, and a typed one can be saved to Bitwarden.
    - A routine re-seal after a sale never generates: an empty entry aborts, so a sale cannot
      rotate the passphrase silently.

    Nothing is saved here: Bitwarden is written only after the seal has worked."""
    from_environment = passphrase_from_environment()
    if from_environment:
        print(f"Using the passphrase in {PASSPHRASE_ENV}.")
        return Choice(from_environment)
    first = prompt_secret(FIRST_PROMPT if offer_generation else RESEAL_PROMPT)
    if not first.strip():
        if not offer_generation:
            raise SealError(CURRENT_PASSPHRASE_HINT)
        return generate_new_passphrase()
    if passphrase_words(first) != passphrase_words(prompt_secret("Again: ")):
        raise SealError("the two entries do not match")
    try:
        passphrase = validate_passphrase(first)
    except ValueError as err:
        raise SealError(f"that passphrase is refused: {err}") from err
    return Choice(passphrase, save=offer_generation and offer_save())


def offer_save() -> bool:
    return have_dotf() and prompt_line("Save it to Bitwarden? [y/N] ").strip().lower() in (
        "y",
        "yes",
    )


def generate_new_passphrase() -> Choice:
    """Five new words. With dotf they are saved to Bitwarden after the seal and never shown;
    without it they are shown on the terminal only and typed back once, which is how the owner
    proves they were written down."""
    phrase = generate_passphrase()
    if have_dotf():
        return Choice(phrase, save=True, generated=True)
    show_and_confirm(phrase)
    return Choice(phrase)


def show_and_confirm(phrase: str) -> None:
    tell(
        f"\nNew passphrase:\n\n    {phrase}\n\nWrite this down now. It is not stored anywhere.\n\n"
    )
    if passphrase_words(prompt_secret("Type it back to confirm: ")) != passphrase_words(phrase):
        raise SealError("the confirmation does not match: nothing was set")


def store_in_bitwarden(choice: Choice) -> bool:
    """Save the passphrase. True when Bitwarden now holds it.

    A typed one that cannot be saved aborts: the owner asked for the save. A generated one is
    shown and typed back instead, since this run holds the only copy."""
    if save_to_bitwarden(hyphenated(choice.passphrase)):
        print(SAVED)
        return True
    if not choice.generated:
        raise SealError(f"{SAVE_FAILED}: nothing was set")
    print(SAVE_FAILED, file=sys.stderr)
    show_and_confirm(choice.passphrase)
    return False


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
        return subprocess.run(
            ["gh", *args], capture_output=True, text=True, env=child_env(), **feed
        )
    except OSError as err:
        raise SealError(f"gh could not run ({err.strerror})") from err


def have_dotf() -> bool:
    return shutil.which("dotf") is not None


def run_dotf(*args: str, stdin: str) -> subprocess.CompletedProcess[str]:
    """Run dotf with `stdin` as the value. Its output is captured and never shown: it is not
    ours to relay, and the value must reach no screen or log."""
    try:
        return subprocess.run(
            ["dotf", *args], input=stdin, capture_output=True, text=True, env=child_env()
        )
    except OSError as err:
        raise SealError(f"dotf could not run ({err.strerror})") from err


def save_to_bitwarden(passphrase: str) -> bool:
    """Store the passphrase as the SELLER_PASSPHRASE secret (stdin only). True when it took."""
    try:
        # --yes: on a pipe dotf cannot ask, and refuses to create the item without it.
        done = run_dotf("secrets", "set", BITWARDEN_ID, "--yes", stdin=passphrase)
        return done.returncode == 0
    except SealError:
        return False


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
        removed = gh("secret", "delete", SECRET_NAME)
        if removed.returncode != 0:
            raise SealError(
                f"gh could not remove the repository-level {SECRET_NAME}: "
                f"{removed.stderr.strip()[:200]}"
            )


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
    choice = ask_passphrase(offer_generation)
    if not offer_generation:
        print(RESEAL_REMINDER)
    envelope = seal_with_node(payload, choice.passphrase)
    size = check_envelope(envelope)
    # Bitwarden before the secret: a lost upload is rerun, a lost passphrase is not recoverable.
    saved = store_in_bitwarden(choice) if choice.save else False
    try:
        upload_secret(envelope)
    except SealError as err:
        if saved:
            raise SealError(
                f"{err}. Bitwarden now holds the new passphrase: run make ci-secrets again"
            ) from err
        raise
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
