"""
Private data never reaches the public build in the clear (FEAT-004, amended by ADR-007).

It holds floors, targets, sale prices and listing history. These tests fail if a private file
lands under build/public/, if the build tolerates one there or any plaintext of the data, if
the sealed envelope turns up anywhere but /seller/index.html, or if any value of the fake
private fixture shows up in a public build made while that data is loaded.
"""

import re
from pathlib import Path

import pytest
import yaml
from sealed_helpers import build_site, json_block, seal_fixture

from leaving_denver import site_builder

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "private.example.yaml"
PUBLIC = ROOT / "build" / "public"
TEXT_SUFFIXES = {".html", ".txt", ".json", ".mjs", ".js", ""}


def private_fixture():
    return yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))


def fixture_values(private):
    """Every number and date the fixture holds for the owner's eyes only."""
    found: set[str] = set()

    def walk(node, under_seller=False):
        if isinstance(node, dict):
            for key, value in node.items():
                if key != "seller":
                    walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
        elif isinstance(node, (int, str)):
            found.add(str(node))

    walk(private)
    return {v for v in found if re.fullmatch(r"\d+|\d{4}-\d{2}-\d{2}", v)}


def text_of(root: Path) -> dict[str, str]:
    # as_posix: the seller page's key must match on every OS, and a backslash key on
    # Windows would silently dodge the "outside /seller/" comparisons (BUG-018 session).
    return {
        str(p.relative_to(root).as_posix()): p.read_text(encoding="utf-8", errors="ignore")
        for p in sorted(root.rglob("*"))
        if p.is_file() and p.suffix in TEXT_SUFFIXES
    }


def leaked(values, files):
    pattern = {v: re.compile(rf"(?<![\w.-]){re.escape(v)}(?![\w])") for v in values}
    return sorted(
        (v, name) for name, text in files.items() for v, p in pattern.items() if p.search(text)
    )


def test_the_built_public_site_has_no_private_file():
    assert PUBLIC.exists(), "build the site first (make test does)"
    assert not [p for p in PUBLIC.rglob("*") if re.search(r"panel|poster", p.name.lower())]
    assert not (PUBLIC / "inventory.json").exists()


@pytest.mark.parametrize("name", ["panel.html", "poster_assistant.html", "inventory.json"])
def test_the_build_fails_when_a_private_file_is_in_the_public_dist(name, tmp_path, monkeypatch):
    monkeypatch.setattr(site_builder, "DIST_DIR", tmp_path)
    (tmp_path / name).write_text("x", encoding="utf-8")
    with pytest.raises(RuntimeError, match="SECURITY LEAK"):
        site_builder.verify_security_guarantees()


@pytest.mark.parametrize(
    "plaintext",
    [
        '{"firm_floor_price": 173}',
        '{"sealed_at": "2031-05-06T07:08:09Z"}',
        '{"floors": {"sofa-sleeper": 173}}',
        '{"price_log": [{"at": "2026-10-03", "price": 205}]}',
    ],
)
@pytest.mark.parametrize("page", ["index.html", "seller/index.html", "notes.txt"])
def test_the_build_fails_when_a_public_file_carries_plaintext_private_data(
    plaintext, page, tmp_path, monkeypatch
):
    monkeypatch.delenv("SELLER_SEALED", raising=False)
    monkeypatch.setattr(site_builder, "DIST_DIR", tmp_path)
    (tmp_path / page).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / page).write_text(plaintext, encoding="utf-8")
    with pytest.raises(RuntimeError, match="SECURITY LEAK"):
        site_builder.verify_security_guarantees()


def test_the_build_accepts_the_sealed_block_in_the_seller_page(tmp_path, monkeypatch):
    dist = tmp_path / "public"
    build_site(dist, monkeypatch, sealed=seal_fixture())
    assert json_block((dist / "seller" / "index.html").read_text(encoding="utf-8"), "sealed")
    site_builder.verify_security_guarantees()


@pytest.mark.parametrize(
    "stray", ["index.html", "es/index.html", "robots.txt", "seller/seller.mjs"]
)
def test_the_build_fails_when_the_envelope_is_anywhere_but_the_seller_page(
    stray, tmp_path, monkeypatch
):
    dist = tmp_path / "public"
    build_site(dist, monkeypatch, sealed=seal_fixture())
    page = (dist / "seller" / "index.html").read_text(encoding="utf-8")
    block = re.search(r'<script type="application/json" id="sealed">.*?</script>', page).group(0)
    ciphertext = json_block(page, "sealed")["ct"]
    # The block, and the ciphertext alone: either is the envelope in the wrong place.
    for text in (block, ciphertext):
        (dist / stray).write_text(text, encoding="utf-8")
        with pytest.raises(RuntimeError, match="SECURITY LEAK"):
            site_builder.verify_security_guarantees()
        (dist / stray).unlink()


def test_the_default_private_file_stays_out_of_git_and_the_deploy():
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "build/" in ignored  # the whole of build/, so nothing built is ever committed
    assert "build/public" in (ROOT / "wrangler.toml").read_text(encoding="utf-8")


def without_sealed_envelope(text: str) -> str:
    """The sealed block is ciphertext by construction — its base64 is random bytes from
    randomBytes on every seal — so a short fixture value landing inside it flanked by base64
    punctuation is a draw of chance, not a plaintext leak (BUG-018, ~1 build in 260). The
    envelope's SHAPE is guaranteed elsewhere; the scan looks at what is around it."""
    return re.sub(r'<script type="application/json" id="sealed">.*?</script>', "", text, flags=re.S)


def test_a_fixture_value_inside_the_sealed_envelope_is_not_a_leak():
    """The carve-out: a value that appears ONLY between the sealed script tags is not
    reported, while the same value in the page's plaintext (outside any envelope) still is."""
    envelope_only = (
        "<!doctype html><html><body>"
        '<script type="application/json" id="sealed">{"salt":"ab59+/==","iv":"x59y","ct":"59"}'
        "</script><p>price 60</p></body></html>"
    )
    plaintext = "<!doctype html><html><body><p>price 59</p></body></html>"
    assert leaked({"59"}, {"seller/index.html": without_sealed_envelope(envelope_only)}) == []
    # The draw that flaked CI: the same text, unstripped, does flag — that is the bug's shape.
    assert leaked({"59"}, {"seller/index.html": envelope_only}) == [("59", "seller/index.html")]
    # The carve-out must not blind the scan to real plaintext on the seller page.
    assert leaked({"59"}, {"seller/index.html": without_sealed_envelope(plaintext)}) == [
        ("59", "seller/index.html")
    ]


def test_no_private_fixture_value_reaches_a_public_build(tmp_path, monkeypatch):
    """Build twice, clean and with the sealed fixture loaded: every file but the seller page is
    identical, and none of the fixture's numbers or dates is in the second, seller page included
    (the envelope is ciphertext, so a value showing there would be a plaintext leak)."""
    private = private_fixture()
    build_site(tmp_path / "clean", monkeypatch)
    build_site(tmp_path / "loaded", monkeypatch, sealed=seal_fixture())
    baseline = text_of(tmp_path / "clean")
    after = text_of(tmp_path / "loaded")

    seller = "seller/index.html"
    # The sealed block is ciphertext; a short value landing inside it is chance, not a
    # leak (BUG-018). The page is still scanned — with the envelope carved out.
    after[seller] = without_sealed_envelope(after[seller])
    assert {k: v for k, v in after.items() if k != seller} == {
        k: v for k, v in baseline.items() if k != seller
    }, "private data changed the public build outside the seller page"

    # Values that already appear in a clean build prove nothing; the rest must be absent.
    discriminating = {v for v in fixture_values(private) if not leaked({v}, baseline)}
    assert len(discriminating) >= 8, "the fixture no longer discriminates; pick distinctive numbers"
    assert leaked(discriminating, after) == []
    # The scan is able to see them: a file that does carry some is caught.
    assert leaked({"173", "191", "10650"}, {"probe.html": "floor 173, target 191, 10650"})


# 8011 as a number of its own: the zip 80111 is public and contains it.
RETIRED = [
    "poster_assistant",
    r"(?<!\d)8011(?!\d)",
    r"panel\.py",
    r"panel\.html",
    "make panel",
    "build/private",
    "PRIVATE_POSTER_HTML",
    "DIST_PRIVATE_DIR",
]


def test_nothing_in_src_or_the_build_refers_to_the_retired_workspace():
    """AC12: the old workspace, its PIN and its folder are absent from src/ and the build."""
    sources = [p for p in (ROOT / "src").rglob("*") if p.is_file() and "__pycache__" not in p.parts]
    built = [p for p in PUBLIC.rglob("*") if p.is_file() and p.suffix in TEXT_SUFFIXES]
    found = [
        (str(p.relative_to(ROOT)), word)
        for p in sources + built
        for word in RETIRED
        if re.search(word, p.read_text(encoding="utf-8", errors="ignore"))
    ]
    assert found == []
    assert not (ROOT / "src" / "leaving_denver" / "panel.py").exists()
    assert not (ROOT / "src" / "leaving_denver" / "templates" / "panel.html").exists()
    assert not (ROOT / "build" / "private").exists()
    assert "panel" not in (ROOT / "Makefile").read_text(encoding="utf-8").split("ci-secrets")[0]
