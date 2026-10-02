"""
/seller/ in headless Chrome over the built page (FEAT-009 PR 1): the controls drive the copy
the user pastes, and each copy button puts exactly what is on screen on the clipboard
(harness: browser_harness.py).
"""

import pytest
from browser_harness import needs_chrome, run_page

pytestmark = needs_chrome

STUBS = """
window.CLIPBOARD = [];
Object.defineProperty(navigator, 'clipboard', { configurable: true,
  value: { writeText: text => { window.CLIPBOARD.push(text); return Promise.resolve(); } } });
"""

SHOW = """
const $ = id => document.getElementById(id);
const ITEMS = JSON.parse($('seller-items').textContent);
const choose = async (id, value) => {
  $(id).value = value;
  $(id).dispatchEvent(new Event('change'));
  await wait(20);
};
const ITEM = [...$('item').options].find(o => o.textContent.includes('Sleeper')).value;
const CAR = [...$('item').options].find(o => o.textContent.includes('Escape')).value;
"""


def run(tmp_path, steps):
    return run_page(tmp_path, "seller/index.html", SHOW + steps, setup=STUBS)


def test_choosing_a_spanish_channel_rewrites_the_listing_in_spanish(tmp_path):
    result = run(
        tmp_path,
        """
await choose('item', ITEM);
await choose('platform', 'fb-es');
return { description: $('description').value, link: $('link').value,
  options: [...$('platform').options].map(o => o.value) };
""",
    )
    assert result["options"] == ["fb", "fb-es", "cl", "cl-es", "offerup", "nextdoor"]
    assert "Me mudo en noviembre" in result["description"]
    assert "Precio: $220." in result["description"]
    assert "/es/i/sofa-sleeper/" in result["link"]


def test_the_counters_the_creator_link_and_the_tags_follow_the_choice(tmp_path):
    result = run(
        tmp_path,
        """
await choose('item', CAR);
await choose('platform', 'cl');
const cl = { count: $('title-count').textContent, href: $('create').href };
await choose('platform', 'fb');
return { cl, fb: { count: $('title-count').textContent, href: $('create').href,
  descriptionCount: $('description-count').textContent },
  title: $('title').value, tags: $('tags').value };
""",
    )
    assert result["cl"]["href"] == "https://post.craigslist.org/c/den/cto"
    assert result["cl"]["count"].endswith("/70")
    assert result["fb"]["href"] == "https://www.facebook.com/marketplace/create/vehicle"
    assert result["fb"]["count"].endswith("/100")
    assert result["fb"]["descriptionCount"].endswith("/5000")
    assert "103,500" in result["title"]


def test_every_copy_button_copies_what_is_on_screen(tmp_path):
    result = run(
        tmp_path,
        """
await choose('item', ITEM);
await choose('platform', 'cl');
const copied = [];
for (const id of ['title', 'description', 'link', 'tags']) {
  document.querySelector(`[data-copy="${id}"]`).click();
  await wait(20);
  copied.push([window.CLIPBOARD.at(-1), $(id).value]);
}
$('copy-price').click();
await wait(20);
copied.push([window.CLIPBOARD.at(-1), String(ITEMS[Number($('item').value)].price)]);
$('copy-full').click();
await wait(20);
copied.push([window.CLIPBOARD.at(-1), `TITLE: ${$('title').value}\\nPRICE: $${
  ITEMS[Number($('item').value)].price.toLocaleString('en-US')}\\n\\n${$('description').value}`]);
for (const button of document.querySelectorAll('[data-reply] [data-copy]')) {
  button.click();
  await wait(5);
  copied.push([window.CLIPBOARD.at(-1), $(button.dataset.copy).value]);
}
return { copied, status: $('status').textContent };
""",
    )
    assert len(result["copied"]) == 6 + 12
    for clipboard, shown in result["copied"]:
        assert clipboard and clipboard == shown
    assert result["status"] == "Copied to clipboard."


@pytest.mark.parametrize("platform", ["fb", "fb-es", "cl", "cl-es", "offerup", "nextdoor"])
def test_every_channel_renders_for_every_item_without_an_error(tmp_path, platform):
    result = run(
        tmp_path,
        f"""
const seen = [];
for (const option of $('item').options) {{
  await choose('item', option.value);
  await choose('platform', '{platform}');
  seen.push([$('title').value, $('description').value.length]);
}}
return seen;
""",
    )
    assert len(result) >= 12
    assert all(title and length > 100 for title, length in result)


def test_a_count_turns_red_when_an_edit_passes_the_platform_limit(tmp_path):
    result = run(
        tmp_path,
        """
await choose('item', ITEM);
await choose('platform', 'fb');
const color = () => getComputedStyle($('description-count')).color;
const before = { text: $('description-count').textContent, color: color() };
$('description').value = 'x'.repeat(5001);
$('description').dispatchEvent(new Event('input'));
return { before, after: { text: $('description-count').textContent, color: color() } };
""",
    )
    assert result["before"]["text"].endswith("/5000")
    assert result["after"]["text"] == "5001/5000"
    assert result["after"]["color"] != result["before"]["color"]
