"""The event endpoint (FEAT-015): functions/api/hit.js takes the page's beacon and writes one
data point to Workers Analytics Engine. It runs in Node here with a fake binding, the way
test_seller_csp.py runs the middleware: the real binding cannot be used locally (Cloudflare docs).

The contract these tests hold: strict validation, a 400 and no write for bad input, a 204 for
good input even when the dataset is missing or throws (a beacon must never become an error page),
nothing read from the request but its body, and the same data point shape the digest queries."""

import json
import re
from pathlib import Path

import pytest
from sealed_helpers import node

ROOT = Path(__file__).resolve().parents[1]
HIT = ROOT / "functions" / "api" / "hit.js"
SELLER_MJS = ROOT / "src" / "leaving_denver" / "assets" / "seller.mjs"

RUN = """
import { onRequestPost, onRequest } from './functions/api/hit.js';
let raw = '';
for await (const chunk of process.stdin) raw += chunk;
const out = [];
for (const c of JSON.parse(raw)) {
  const points = [];
  const env = c.binding === 'none' ? {}
    : { SALE_METRICS: { writeDataPoint: p => { if (c.binding === 'throws') throw new Error('x'); points.push(p); } } };
  const reads = [];
  const request = new Request('https://leaving-denver.pages.dev/api/hit', {
    method: c.method || 'POST', headers: { 'content-type': 'text/plain', 'x-forwarded-for': '203.0.113.9' },
    body: c.method === 'GET' ? undefined : c.body,
  });
  // Anything the handler reads of the request besides its method and body is recorded.
  for (const key of ['headers', 'cf']) {
    Object.defineProperty(request, key, { get() { reads.push(key); return {}; } });
  }
  const handler = (c.method || 'POST') === 'POST' ? onRequestPost : onRequest;
  const response = await handler({ request, env });
  out.push({ status: response.status, body: await response.text(), points, reads, allow: response.headers.get('allow') });
}
process.stdout.write(JSON.stringify(out));
"""


def run(*cases):
    result = node(RUN, json.dumps(list(cases)))
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def post(payload, **case):
    body = payload if isinstance(payload, str) else json.dumps(payload)
    return {"body": body, **case}


def only(case):
    return run(case)[0]


def test_a_visit_writes_one_data_point_and_answers_204():
    answer = only(post({"event": "visit", "source": "flyer", "locale": "en"}))
    assert answer["status"] == 204
    assert answer["body"] == ""
    assert answer["points"] == [
        {"blobs": ["visit", "flyer", "", "", "en"], "doubles": [1], "indexes": ["visit"]}
    ]


def test_a_text_tap_carries_its_item_and_a_bundle_tap_its_bundle():
    item = only(
        post({"event": "text_tap", "item": "sofa-sleeper", "source": "nextdoor", "locale": "es"})
    )
    assert item["points"][0]["blobs"] == ["text_tap", "nextdoor", "sofa-sleeper", "", "es"]
    bundle = only(
        post({"event": "text_tap", "bundle": "kitchen-2", "source": "direct", "locale": "en"})
    )
    assert bundle["points"][0]["blobs"] == ["text_tap", "direct", "", "kitchen-2", "en"]
    view = only(post({"event": "view_item", "item": "2019-ford-escape-sel-awd", "locale": "en"}))
    assert view["points"][0]["blobs"] == [
        "view_item",
        "direct",
        "2019-ford-escape-sel-awd",
        "",
        "en",
    ]


@pytest.mark.parametrize(
    "payload",
    [
        {"event": "purchase", "source": "flyer"},
        {"event": 7},
        {"source": "flyer"},
        {"event": "__proto__"},
        {"event": "constructor"},
        [],
        [{"event": "visit"}],
        "null",
        "7",
        '"visit"',
        "not json",
        "",
        "{",
    ],
)
def test_bad_input_is_a_400_and_writes_nothing(payload):
    answer = only(post(payload))
    assert answer["status"] == 400
    assert answer["points"] == []


def test_a_body_over_the_cap_is_a_400():
    padding = "x" * 4096
    answer = only(post({"event": "visit", "source": "flyer", "note": padding}))
    assert answer["status"] == 400
    assert answer["points"] == []


@pytest.mark.parametrize(
    "item",
    [
        "Sofa",
        "sofa sleeper",
        "sofa_sleeper",
        "sofa/../x",
        "<script>",
        "",
        "a" * 65,
        7,
        None,
        ["a"],
        {"a": 1},
    ],
)
def test_an_item_id_that_is_not_a_slug_is_dropped_and_the_event_still_counts(item):
    answer = only(post({"event": "view_item", "item": item, "source": "flyer", "locale": "en"}))
    assert answer["status"] == 204
    assert answer["points"][0]["blobs"] == ["view_item", "flyer", "", "", "en"]


def test_an_id_of_exactly_the_cap_is_kept():
    slug = "a" * 64
    answer = only(post({"event": "view_item", "item": slug, "locale": "en"}))
    assert answer["points"][0]["blobs"][2] == slug


@pytest.mark.parametrize(
    "source", ["Flyer", "FLYER", "evil.example", "flyer ", "", 7, None, "a" * 500, "__proto__"]
)
def test_an_unknown_source_is_other_never_stored_as_sent(source):
    answer = only(post({"event": "visit", "source": source, "locale": "en"}))
    assert answer["status"] == 204
    assert answer["points"][0]["blobs"][1] == ("direct" if source in ("", None, 7) else "other")
    assert "evil" not in json.dumps(answer["points"])
    assert "a" * 100 not in json.dumps(answer["points"])


def test_a_missing_source_is_direct():
    answer = only(post({"event": "text_tap", "item": "lamp", "locale": "en"}))
    assert answer["points"][0]["blobs"][1] == "direct"


@pytest.mark.parametrize("locale", ["fr", "EN", "en-US", "", 7, None, "x" * 99])
def test_an_unknown_locale_is_en(locale):
    answer = only(post({"event": "visit", "source": "flyer", "locale": locale}))
    assert answer["points"][0]["blobs"][4] == "en"


def test_the_spanish_locale_is_kept():
    answer = only(post({"event": "visit", "source": "flyer", "locale": "es"}))
    assert answer["points"][0]["blobs"][4] == "es"


def test_extra_fields_are_never_stored():
    answer = only(
        post(
            {
                "event": "text_tap",
                "item": "lamp",
                "source": "flyer",
                "locale": "en",
                "phone": "+13035550100",
                "ua": "Mozilla",
                "ip": "203.0.113.9",
            }
        )
    )
    point = answer["points"][0]
    assert set(point) == {"blobs", "doubles", "indexes"}
    assert len(point["blobs"]) == 5
    text = json.dumps(point)
    assert "13035550100" not in text and "Mozilla" not in text and "203.0.113" not in text


def test_a_missing_dataset_binding_still_answers_204():
    assert only(post({"event": "visit", "source": "flyer"}, binding="none"))["status"] == 204


def test_a_dataset_that_throws_still_answers_204():
    assert only(post({"event": "visit", "source": "flyer"}, binding="throws"))["status"] == 204


def test_nothing_of_the_request_is_read_but_its_body():
    """No IP, no user agent, no country: the request's headers and `cf` are never touched."""
    for case in (
        post({"event": "visit", "source": "flyer"}),
        post({"event": "text_tap", "item": "lamp"}),
        post("not json"),
    ):
        assert only(case)["reads"] == []


def test_only_post_is_handled_anything_else_is_a_405():
    answer = only({"method": "GET"})
    assert answer["status"] == 405
    assert answer["allow"] == "POST"
    assert answer["points"] == []


def test_every_channel_the_site_can_link_from_is_a_known_source():
    """A channel that is missing from the function reads as `other` in the digest: this fails
    the day a channel is added to the seller tool or to `make post` and not here."""
    from leaving_denver.channels import CHANNELS

    sources = set(re.findall(r"source: '([a-z]+)'", SELLER_MJS.read_text(encoding="utf-8")))
    sources |= set(CHANNELS) | {"flyer"}
    assert {"facebook", "craigslist", "offerup", "nextdoor", "flyer"} <= sources, "stale pattern"
    probe = run(*[post({"event": "visit", "source": s}) for s in sorted(sources)])
    for source, answer in zip(sorted(sources), probe, strict=True):
        assert answer["points"][0]["blobs"][1] == source, f"{source} reads as other"


def test_the_function_is_not_under_seller_and_the_middleware_lets_it_through():
    """/seller/* is guarded by Access in the middleware; /api/hit must pass through untouched."""
    assert HIT.relative_to(ROOT).parts[:2] == ("functions", "api")
    result = node(
        """
        import { onRequest } from './functions/_middleware.js';
        let passed = false;
        const response = await onRequest({
          request: new Request('https://leaving-denver.pages.dev/api/hit', { method: 'POST' }),
          env: {}, data: {},
          next: async () => { passed = true; return new Response(null, { status: 204 }); },
        });
        process.stdout.write(JSON.stringify({ passed, status: response.status,
          csp: response.headers.get('content-security-policy') }));
        """
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"passed": True, "status": 204, "csp": None}


def test_every_id_the_page_can_send_passes_the_endpoints_slug_rule():
    """An item or bundle whose id the endpoint would drop is invisible in the digest."""
    import yaml

    data = yaml.safe_load((ROOT / "data" / "inventory.yaml").read_text(encoding="utf-8"))
    ids = [i["id"] for i in data["items"]] + [b["id"] for b in data["bundles"]]
    assert len(ids) > 10, "stale: no ids found"
    for ident in ids:
        assert re.fullmatch(r"[a-z0-9-]{1,64}", ident), ident


def test_the_binding_the_function_writes_to_is_declared_for_pages():
    """Cloudflare gives the function `env.SALE_METRICS` only if wrangler.toml declares it."""
    import tomllib

    config = tomllib.loads((ROOT / "wrangler.toml").read_text(encoding="utf-8"))
    assert config["pages_build_output_dir"] == "build/public"
    (dataset,) = config["analytics_engine_datasets"]
    assert dataset["binding"] == "SALE_METRICS"
    assert "SALE_METRICS" in HIT.read_text(encoding="utf-8")
    assert re.fullmatch(r"[a-z0-9_]+", dataset["dataset"])
