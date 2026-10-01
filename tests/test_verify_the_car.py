"""
The car's "verify it yourself" section (FEAT-008): the public VIN, links to official sources
only, and the seller's own evidence, which is a photo the car already carries. The links and
the evidence are data under the car (`verify:`), so a check or an evidence item added later is
one list entry; the builder refuses a check that is not https on an official host and evidence
that is not one of the car's photos.

No Carfax and no dealer service-history printout yet: they are pending owner tasks (#28, #34),
so the section renders only what exists. Those tests flip on purpose when the entries land.
"""

import copy
import re
from urllib.parse import urlsplit

import pytest
import yaml
from test_build_contract import CAR, PHONE, inventory

from leaving_denver import site_builder
from leaving_denver.config import DATA_DIR
from leaving_denver.image_processor import synced_name

ROOT = DATA_DIR.parent
PUBLIC = ROOT / "build" / "public"
PAGES = {"en": "index.html", "es": "es/index.html"}
CAR_ID = "2019-ford-escape-sel-awd"
SOURCE = yaml.safe_load((DATA_DIR / "inventory.yaml").read_text(encoding="utf-8"))
SOURCE_CAR = next(item for item in SOURCE["items"] if item["id"] == CAR_ID)
# Written out here, not imported from the builder: the test must fail if the builder's list widens.
OFFICIAL_HOSTS = {"nhtsa.gov", "ford.com", "nicb.org"}
SECTION = re.compile(r'<section[^>]*data-role="verify-car".*?</section>', re.DOTALL)
LINK = re.compile(r"<a\s([^>]*)>", re.DOTALL)
# What the seller cannot back or must not publish. Owner decisions, 2026-09-30.
FORBIDDEN = re.compile(
    r"100k|carfax|service[- ]history|historial de servicio|service receipt|"
    r"\b(title|registration|plate|owner|address)\b|\b(título|registro|placa|propietario|dirección)\b",
    re.IGNORECASE,
)


@pytest.fixture
def public_dir(tmp_path, monkeypatch):
    """A scratch build root: the builder writes here, never into build/public."""
    dist = tmp_path / "public"
    monkeypatch.setenv("SELLER_PHONE", PHONE)
    monkeypatch.setattr(site_builder, "DIST_DIR", dist)
    monkeypatch.setattr(site_builder, "PUBLIC_INDEX_HTML", dist / "index.html")
    monkeypatch.setattr(site_builder, "PUBLIC_ROBOTS_TXT", dist / "robots.txt")
    monkeypatch.setattr(site_builder, "PUBLIC_HEADERS", dist / "_headers")
    return dist


def section(page):
    found = SECTION.search((PUBLIC / page).read_text(encoding="utf-8"))
    assert found, f"{page} has no verify section for the car"
    return found.group(0)


def text_of(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


def links(html):
    """Each link's attributes, by name."""
    return [dict(re.findall(r'([\w-]+)="([^"]*)"', attrs)) for attrs in LINK.findall(html)]


def is_official(host):
    return any(host == domain or host.endswith("." + domain) for domain in OFFICIAL_HOSTS)


@pytest.mark.parametrize("locale", PAGES)
def test_the_section_shows_the_vin_and_the_three_official_hosts(locale):
    html = section(PAGES[locale])
    assert SOURCE_CAR["vin"] in text_of(html)
    hosts = {urlsplit(a["href"]).hostname for a in links(html) if a["href"].startswith("https:")}
    for domain in OFFICIAL_HOSTS:
        assert any(h == domain or h.endswith("." + domain) for h in hosts), f"{locale}: {domain}"
    heading = {"en": "Verify it yourself", "es": "Compruébalo tú mismo"}[locale]
    assert heading in text_of(html)


def test_the_section_sits_under_the_car_and_not_in_the_footer():
    html = (PUBLIC / "index.html").read_text(encoding="utf-8")
    assert html.index('data-role="vehicle-payment"') < html.index('data-role="verify-car"')
    assert html.index('data-role="verify-car"') < html.index("<footer")


@pytest.mark.parametrize("locale", PAGES)
def test_every_link_is_https_on_an_official_host_or_one_of_the_cars_photos(locale):
    html = section(PAGES[locale])
    found = links(html)
    assert len(found) >= 5, "three checks and two evidence photos"
    for attrs in found:
        href = attrs["href"]
        parts = urlsplit(href)
        if parts.scheme:
            assert parts.scheme == "https", href
            assert is_official(parts.hostname), href
        else:
            assert "/catalog/" + CAR_ID + "/" in "/" + href.lstrip("./"), href
        assert attrs.get("target") == "_blank", href
        assert set(attrs.get("rel", "").split()) >= {"noopener", "noreferrer"}, href


def test_the_allow_list_rejects_look_alike_hosts():
    for host in ("nhtsa.gov.evil.example", "evilford.com", "carfax.com", "nicb.org.cn"):
        assert not is_official(host), host
    for host in ("www.nhtsa.gov", "ford.com", "www.nicb.org"):
        assert is_official(host), host


@pytest.mark.parametrize("locale", PAGES)
def test_evidence_links_to_photos_the_car_has_and_the_build_ships(locale):
    html = section(PAGES[locale])
    prefix = "" if locale == "en" else "../"
    photos = {synced_name(p) for p in SOURCE_CAR["photos"]}
    evidence = [a["href"] for a in links(html) if not a["href"].startswith("https:")]
    assert {href.rsplit("/", 1)[-1] for href in evidence} == {
        "doc_1_recall_invoice.jpg",
        "doc_2_emissions_report.jpg",
    }
    for href in evidence:
        assert href.startswith(prefix + "catalog/" + CAR_ID + "/"), href
        name = href.rsplit("/", 1)[-1]
        assert name in photos, f"{href} is not one of the car's photos"
        assert (PUBLIC / "catalog" / CAR_ID / name).is_file(), f"{href} is not in the build"


@pytest.mark.parametrize(
    ("locale", "certificate", "scam"),
    [
        ("en", "fresh, unused", "official sites"),
        ("es", "sin usar", "sitios oficiales"),
    ],
)
def test_the_section_hands_over_a_fresh_certificate_and_warns_about_paid_report_links(
    locale, certificate, scam
):
    text = text_of(section(PAGES[locale])).lower()
    assert certificate in text
    assert scam in text
    assert ("never pay" if locale == "en" else "nunca pagues") in text
    assert "PASS" in text_of(section(PAGES[locale]))


@pytest.mark.parametrize("locale", PAGES)
def test_the_section_claims_no_service_history_and_shows_no_personal_data(locale):
    # Link targets are checked too: a Carfax or dealer URL would show up in an href.
    html = section(PAGES[locale])
    hits = FORBIDDEN.findall(html)
    assert not hits, f"{locale}: {hits}"


def test_the_data_carries_both_languages_for_every_entry():
    verify = SOURCE_CAR["verify"]
    spanish = SOURCE_CAR["es"]["verify"]
    for kind in ("checks", "evidence"):
        ids = [entry["id"] for entry in verify[kind]]
        assert len(ids) == len(set(ids)), f"{kind}: duplicate ids"
        for entry_id in ids:
            copy_es = spanish[entry_id]
            assert copy_es["label"] and copy_es["note"], f"es: {entry_id}"
        for entry in verify[kind]:
            assert entry["label"] and entry["note"], entry["id"]


def test_the_template_hardcodes_no_check_and_no_evidence():
    template = (ROOT / "src" / "leaving_denver" / "templates" / "index.html").read_text(
        encoding="utf-8"
    )
    block = template[template.index('data-role="verify-car"') :]
    block = block[: block.index("</section>")]
    for hardcoded in ("nhtsa", "ford.com", "nicb", "doc_1", "doc_2", "https://"):
        assert hardcoded not in block, hardcoded


# The builder's own guards, on a car built from a fixture.


def car_with(verify):
    car = copy.deepcopy(CAR)
    car.update(
        vin="1FMCU9HD9KUB80146",
        photos=["doc_1_recall_invoice.jpg"],
        images=[f"catalog/{CAR_ID}/doc_1_recall_invoice.jpg"],
        verify=verify,
    )
    return car


def checks(url):
    return {
        "checks": [{"id": "check", "url": url, "label": "Check", "note": "Note"}],
        "evidence": [],
    }


def built_page(public_dir, car):
    data = inventory()
    data["items"].append(car)
    site_builder.build_public_site(data)
    return (public_dir / "index.html").read_text(encoding="utf-8")


def test_a_car_without_verify_data_renders_no_section(public_dir):
    car = copy.deepcopy(CAR)
    car.pop("verify", None)
    assert 'data-role="verify-car"' not in built_page(public_dir, car)


def test_a_car_with_verify_data_renders_it_from_the_data(public_dir):
    verify = {
        "checks": [
            {
                "id": "nhtsa",
                "url": "https://www.nhtsa.gov/recalls",
                "label": "Label from data",
                "note": "Note from data",
            }
        ],
        "evidence": [
            {
                "id": "invoice",
                "photo": "doc_1_recall_invoice.jpg",
                "label": "Invoice from data",
                "note": "Invoice note",
            }
        ],
    }
    html = built_page(public_dir, car_with(verify))
    found = SECTION.search(html).group(0)
    assert "Label from data" in found
    assert "Note from data" in found
    assert "Invoice from data" in found
    assert 'href="https://www.nhtsa.gov/recalls"' in found
    assert f'href="catalog/{CAR_ID}/doc_1_recall_invoice.jpg"' in found


@pytest.mark.parametrize(
    "url",
    [
        "http://www.nhtsa.gov/recalls",
        "https://www.carfax.com/vehicle/1FMCU9HD9KUB80146",
        "https://nhtsa.gov.evil.example/recalls",
        "https://evilford.com/support/recalls/",
        "https://user@www.nhtsa.gov@evil.example/",
        "//www.nhtsa.gov/recalls",
        "javascript:alert(1)",
    ],
)
def test_the_build_refuses_a_check_that_is_not_https_on_an_official_host(public_dir, url):
    data = inventory()
    data["items"].append(car_with(checks(url)))
    with pytest.raises(RuntimeError, match="official"):
        site_builder.build_public_site(data)


def test_the_build_refuses_evidence_that_is_not_one_of_the_cars_photos(public_dir):
    verify = {
        "checks": [],
        "evidence": [{"id": "title", "photo": "title_scan.jpg", "label": "x", "note": "y"}],
    }
    data = inventory()
    data["items"].append(car_with(verify))
    with pytest.raises(RuntimeError, match="title_scan.jpg"):
        site_builder.build_public_site(data)


def test_the_build_refuses_evidence_that_is_synced_but_not_listed(public_dir):
    car = car_with(
        {
            "checks": [],
            "evidence": [
                {"id": "unlisted", "photo": "doc_9_unlisted.jpg", "label": "x", "note": "y"}
            ],
        }
    )
    car["images"].append(f"catalog/{CAR_ID}/doc_9_unlisted.jpg")
    data = inventory()
    data["items"].append(car)
    with pytest.raises(RuntimeError, match="doc_9_unlisted.jpg"):
        site_builder.build_public_site(data)


def test_the_build_refuses_verify_data_on_a_car_with_no_vin(public_dir):
    car = car_with(checks("https://www.nhtsa.gov/recalls"))
    car.pop("vin")
    data = inventory()
    data["items"].append(car)
    with pytest.raises(RuntimeError, match="vin"):
        site_builder.build_public_site(data)
