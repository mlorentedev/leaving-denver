"""
Shared fixtures for the sealed-data tests (ADR-007, FEAT-009 PR 2): a throwaway passphrase,
the fixture private data with sentinels planted in every allow-listed key, and Node-side
helpers that open an envelope with the same code the page uses.

Nothing here reads data/private.sops.yaml: every value is the fixture's or a sentinel.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "private.example.yaml"

# Five words from the EFF list, used by no real data: a test passphrase only.
PASSPHRASE = "abacus abide abiding ability abdomen"

# Values that cannot occur in public content, one per allow-listed key. The fixture's small
# integers (13, 33, ...) also appear in dates, sizes and prices, so a search for them would fail
# on public content (the approach of test_template_sees_only_sanitized_data).
SENTINEL_FLOOR = 7310987
SENTINEL_TARGET = 7320987
SENTINEL_SALE = 7330987
SENTINEL_PRICE_LOG = 7340987
SENTINEL_POSTED = "2031-04-17"
SENTINEL_NOTE = "sentinel-note-kestrel-4471"
SENTINEL_SEALED_AT = "2031-05-06T07:08:09Z"
SENTINELS = (
    str(SENTINEL_FLOOR),
    str(SENTINEL_TARGET),
    str(SENTINEL_SALE),
    str(SENTINEL_PRICE_LOG),
    SENTINEL_POSTED,
    SENTINEL_NOTE,
)
SENTINEL_ITEM = "sofa-sleeper"


def fixture_private():
    """The fixture's private data, with a sentinel planted in every allow-listed key."""
    private = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
    private["floors"][SENTINEL_ITEM] = SENTINEL_FLOOR
    private["targets"][SENTINEL_ITEM] = SENTINEL_TARGET
    private["sales"][SENTINEL_ITEM] = {"price": SENTINEL_SALE, "at": "2026-10-13"}
    tracking = private["tracking"][SENTINEL_ITEM]
    tracking["price_log"].append({"at": "2026-10-04", "price": SENTINEL_PRICE_LOG})
    tracking["channels"]["facebook"].append(SENTINEL_POSTED)
    private["notes"] = {SENTINEL_ITEM: SENTINEL_NOTE}
    return private


def node(script, stdin=""):
    """Run an ES-module script in Node from the repo root; returns the completed process."""
    return subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=ROOT,
        input=stdin,
        text=True,
        capture_output=True,
        check=False,
    )


OPEN_SCRIPT = """
import { openEnvelope } from './src/leaving_denver/assets/seller.mjs';
let raw = '';
for await (const chunk of process.stdin) raw += chunk;
const { envelope, passphrase } = JSON.parse(raw);
try {
  process.stdout.write(JSON.stringify({ ok: true, plaintext: await openEnvelope(envelope, passphrase) }));
} catch (error) {
  process.stdout.write(JSON.stringify({ ok: false }));
}
"""


def open_in_node(envelope, passphrase):
    """The plaintext the page's own code gets from the envelope, or None when it will not open."""
    if isinstance(envelope, str):
        envelope = json.loads(envelope)
    result = node(OPEN_SCRIPT, json.dumps({"envelope": envelope, "passphrase": passphrase}))
    assert result.returncode == 0, result.stderr
    answer = json.loads(result.stdout)
    return answer["plaintext"] if answer["ok"] else None


# An implementation of the envelope that shares no code with seller.mjs: node:crypto's PBKDF2 and
# AES-GCM, written from the ADR (key = PBKDF2-SHA256(normalised words, salt, iter) -> 32 bytes;
# AAD = {"v","kdf","iter","salt"} as JSON; 128-bit tag at the end of ct). A fault in the page's
# own derivation (a fixed iteration count, a wrong AAD) cannot hide behind a round trip with itself.
ORACLE_SCRIPT = """
import { createCipheriv, createDecipheriv, pbkdf2Sync, randomBytes } from 'node:crypto';
let raw = '';
for await (const chunk of process.stdin) raw += chunk;
const input = JSON.parse(raw);
const aad = e => Buffer.from(JSON.stringify({ v: e.v, kdf: e.kdf, iter: e.iter, salt: e.salt }));
const key = (words, e) => pbkdf2Sync(Buffer.from(words, 'utf8'), Buffer.from(e.salt, 'base64'), e.iter, 32, 'sha256');
if (input.cmd === 'seal') {
  const e = { v: 1, kdf: 'PBKDF2-SHA256', iter: input.iter, salt: randomBytes(16).toString('base64') };
  const iv = randomBytes(12);
  const cipher = createCipheriv('aes-256-gcm', key(input.words, e), iv, { authTagLength: 16 });
  cipher.setAAD(aad(e));
  const ct = Buffer.concat([cipher.update(input.plaintext, 'utf8'), cipher.final(), cipher.getAuthTag()]);
  process.stdout.write(JSON.stringify({ ...e, iv: iv.toString('base64'), ct: ct.toString('base64') }));
} else {
  try {
    const e = input.envelope;
    const body = Buffer.from(e.ct, 'base64');
    const decipher = createDecipheriv('aes-256-gcm', key(input.words, e), Buffer.from(e.iv, 'base64'), { authTagLength: 16 });
    decipher.setAAD(aad(e));
    decipher.setAuthTag(body.subarray(body.length - 16));
    const plain = Buffer.concat([decipher.update(body.subarray(0, body.length - 16)), decipher.final()]);
    process.stdout.write(JSON.stringify({ ok: true, plaintext: plain.toString('utf8') }));
  } catch (error) {
    process.stdout.write(JSON.stringify({ ok: false }));
  }
}
"""


def oracle_words(passphrase):
    from leaving_denver import seal

    return " ".join(seal.passphrase_words(passphrase))


def oracle_seal(plaintext, passphrase=PASSPHRASE, iterations=1_000_000):
    """An envelope (JSON text) sealed by the independent implementation."""
    request = {"cmd": "seal", "plaintext": plaintext, "words": oracle_words(passphrase)}
    result = node(ORACLE_SCRIPT, json.dumps({**request, "iter": iterations}))
    assert result.returncode == 0, result.stderr
    return result.stdout


def oracle_open(envelope, passphrase=PASSPHRASE):
    """The plaintext the independent implementation gets, or None when it will not open."""
    if isinstance(envelope, str):
        envelope = json.loads(envelope)
    request = {"cmd": "open", "envelope": envelope, "words": oracle_words(passphrase)}
    result = node(ORACLE_SCRIPT, json.dumps(request))
    assert result.returncode == 0, result.stderr
    answer = json.loads(result.stdout)
    return answer["plaintext"] if answer["ok"] else None


def json_block(html, block_id):
    """The parsed content of a <script type="application/json" id=...> block, or None."""
    import re

    found = re.search(
        rf'<script type="application/json" id="{re.escape(block_id)}">(.*?)</script>',
        html,
        flags=re.DOTALL,
    )
    return json.loads(found.group(1)) if found else None


def build_site(dist, monkeypatch, sealed=None):
    """Build the public site into dist, with SELLER_SEALED set to `sealed` (None: unset).

    Public files only: the page is built without the Tailwind step (see build_with_styles)."""
    from leaving_denver import site_builder

    monkeypatch.setenv("SELLER_PHONE", "+15555550100")
    if sealed is None:
        monkeypatch.delenv("SELLER_SEALED", raising=False)
    else:
        monkeypatch.setenv("SELLER_SEALED", sealed)
    monkeypatch.setattr(site_builder, "DIST_DIR", dist)
    monkeypatch.setattr(site_builder, "PUBLIC_INDEX_HTML", dist / "index.html")
    monkeypatch.setattr(site_builder, "PUBLIC_ROBOTS_TXT", dist / "robots.txt")
    monkeypatch.setattr(site_builder, "PUBLIC_HEADERS", dist / "_headers")
    site_builder.build_public_site(site_builder.load_inventory_yaml())


def dom_forms(*numbers_and_text):
    """Every way the page may show a value: as written, and a number with thousands commas."""
    forms = []
    for value in numbers_and_text:
        forms.append(str(value))
        if isinstance(value, int):
            forms.append(f"{value:,}")
    return forms


def seal_fixture(passphrase=PASSPHRASE):
    """The fixture private data (sentinels planted), sealed: the envelope as JSON text."""
    from datetime import UTC, datetime

    from leaving_denver import seal

    payload = seal.allowlisted_payload(fixture_private(), datetime(2031, 5, 6, 7, 8, 9, tzinfo=UTC))
    return seal.seal_with_node(payload, passphrase)


FAKE_GH = """#!{python}
import json
import os
import sys

stdin = "" if sys.stdin.isatty() else sys.stdin.read()
import time

with open(os.environ["FAKE_GH_LOG"], "a", encoding="utf-8") as log:
    log.write(json.dumps({{"argv": sys.argv[1:], "stdin": stdin, "t": time.time_ns()}}) + "\\n")
if sys.argv[1:3] == ["secret", "list"]:
    sys.stdout.write(os.environ.get("FAKE_GH_LIST", ""))
if os.environ.get("FAKE_GH_FAIL") and os.environ["FAKE_GH_FAIL"] in " ".join(sys.argv[1:]):
    sys.stderr.write("fake gh: failing on purpose\\n")
    sys.exit(1)
"""

FAKE_SOPS = """#!{python}
import os
import sys

with open(os.environ["FAKE_GH_LOG"], "a", encoding="utf-8") as log:
    log.write('{{"sops": true}}\\n')
sys.exit(1)
"""


FAKE_DOTF = """#!{python}
import json
import os
import sys

import time

stdin = sys.stdin.read()
with open(os.environ["FAKE_DOTF_LOG"], "a", encoding="utf-8") as log:
    log.write(
        json.dumps(
            {{"argv": sys.argv[1:], "stdin": stdin, "env": sorted(os.environ), "t": time.time_ns()}}
        )
        + "\\n"
    )
# What dotf does with a value on a pipe: it cannot ask, so an absent item needs --yes.
CANARY = "FAKE-DOTF-STDERR-CANARY"
if not os.environ.get("FAKE_DOTF_EXISTS") and not {{"--yes", "-y"}} & set(sys.argv[1:]):
    sys.stderr.write(CANARY + ": item not found; re-run with --yes to create it non-interactively\\n")
    sys.exit(1)
if os.environ.get("FAKE_DOTF_ECHO"):
    # A careless tool: the value on both streams. Nothing of it may reach the owner's screen.
    sys.stdout.write(stdin)
    sys.stderr.write(stdin)
if os.environ.get("FAKE_DOTF_FAIL"):
    sys.stderr.write(CANARY + ": failing on purpose\\n")
    sys.exit(3)
"""


def install_fakes(tmp_path, monkeypatch, *, list_output="", fail_on="", dotf=False):
    """A fake `gh` (and a `sops` that only records it was called) ahead of the real ones on PATH.

    Returns a function giving the calls the fake `gh` has seen, as {argv, stdin} dicts."""
    bin_dir = tmp_path / "fake-bin"
    bin_dir.mkdir()
    log = tmp_path / "gh-calls.jsonl"
    fakes = [("gh", FAKE_GH), ("sops", FAKE_SOPS)] + ([("dotf", FAKE_DOTF)] if dotf else [])
    for name, body in fakes:
        script = bin_dir / name
        script.write_text(body.format(python=sys.executable), encoding="utf-8")
        script.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}:{os.environ['PATH']}")
    monkeypatch.setenv("FAKE_GH_LOG", str(log))
    monkeypatch.setenv("FAKE_GH_LIST", list_output)
    monkeypatch.setenv("FAKE_GH_FAIL", fail_on)
    dotf_log = tmp_path / "dotf-calls.jsonl"
    monkeypatch.setenv("FAKE_DOTF_LOG", str(dotf_log))
    monkeypatch.delenv("FAKE_DOTF_FAIL", raising=False)
    monkeypatch.delenv("FAKE_DOTF_ECHO", raising=False)
    monkeypatch.delenv("FAKE_DOTF_EXISTS", raising=False)

    def calls():
        if not log.exists():
            return []
        return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]

    def dotf_calls():
        if not dotf_log.exists():
            return []
        return [json.loads(line) for line in dotf_log.read_text(encoding="utf-8").splitlines()]

    calls.dotf = dotf_calls
    return calls
