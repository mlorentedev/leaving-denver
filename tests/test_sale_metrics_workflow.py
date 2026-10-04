"""The daily metrics digest (integrations/n8n, FEAT-015): an n8n workflow that reads the first-party
events from Workers Analytics Engine and Cloudflare Web Analytics and emails a summary.

The file is public: it must hold no secret, no address and nothing that goes stale (a price, an item
title). Its Code node is run here in Node on rows shaped like the ones the endpoint writes, so the
digest, the SQL's column mapping and functions/api/hit.js are checked against each other and not
each against its own assumptions."""

import json
import re
import tomllib
from pathlib import Path

import pytest
import yaml
from sealed_helpers import node

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / "integrations/n8n/workflows/sale_metrics_daily_digest.json"
TEXT = WORKFLOW.read_text(encoding="utf-8")
FLOW = json.loads(TEXT)
NODES = {n["name"]: n for n in FLOW["nodes"]}


def by_type(kind):
    return [n for n in FLOW["nodes"] if n["type"] == kind]


def strings(value):
    """Every string in a JSON value, keys included."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)


def test_it_is_importable_n8n_json_that_starts_switched_off():
    assert FLOW["name"]
    assert FLOW["active"] is False, "the owner switches it on after setting the credentials"
    for node_ in FLOW["nodes"]:
        assert {"parameters", "name", "type", "typeVersion", "position"} <= set(node_)
    assert len(NODES) == len(FLOW["nodes"]), "node names are unique"


def test_the_nodes_form_one_chain_from_the_schedule_to_the_email():
    (trigger,) = by_type("n8n-nodes-base.scheduleTrigger")
    (email,) = by_type("n8n-nodes-base.emailSend")
    seen, current = [trigger["name"]], trigger["name"]
    while current in FLOW["connections"]:
        (links,) = FLOW["connections"][current]["main"]
        (link,) = links
        assert link["node"] in NODES, link
        current = link["node"]
        seen.append(current)
    assert seen[-1] == email["name"]
    assert sorted(seen) == sorted(NODES), "every node is on the chain"


def test_it_runs_daily_at_eight_in_denver():
    (trigger,) = by_type("n8n-nodes-base.scheduleTrigger")
    (interval,) = trigger["parameters"]["rule"]["interval"]
    assert interval == {"field": "cronExpression", "expression": "0 8 * * *"}
    assert FLOW["settings"]["timezone"] == "America/Denver"


def test_it_sends_an_email_through_smtp_and_nothing_else():
    (email,) = by_type("n8n-nodes-base.emailSend")
    assert email["credentials"] == {"smtp": {"name": "sale-digest-smtp"}}
    assert email["parameters"]["emailFormat"] == "text"
    assert email["parameters"]["subject"] == "={{ $json.subject }}"
    lowered = TEXT.lower()
    for other_channel in ("telegram", "slack", "discord", "webhook"):
        assert other_channel not in lowered, other_channel


def test_the_addresses_come_from_n8n_variables_and_are_not_in_the_file():
    (email,) = by_type("n8n-nodes-base.emailSend")
    assert email["parameters"]["toEmail"] == "={{ $env.SALE_DIGEST_TO }}"
    assert email["parameters"]["fromEmail"] == "={{ $env.SALE_DIGEST_FROM }}"
    assert not re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", TEXT), "an email address in a public file"


def test_credentials_are_named_and_never_inlined():
    seen = {}
    for node_ in FLOW["nodes"]:
        for kind, ref in node_.get("credentials", {}).items():
            assert set(ref) == {"name"}, f"{node_['name']}: only a name, never an id or a value"
            seen[kind] = ref["name"]
    assert seen == {"httpHeaderAuth": "cloudflare-analytics-read", "smtp": "sale-digest-smtp"}
    for node_ in by_type("n8n-nodes-base.httpRequest"):
        assert node_["parameters"]["authentication"] == "genericCredentialType"
        assert node_["parameters"]["genericAuthType"] == "httpHeaderAuth"
        assert node_["credentials"] == {"httpHeaderAuth": {"name": "cloudflare-analytics-read"}}
        assert "headers" not in json.dumps(node_["parameters"]).lower(), "no header typed in"


def test_the_file_holds_no_secret():
    assert "bearer" not in TEXT.lower()
    assert not re.search(r"[A-Za-z0-9_-]{40,}", TEXT), "a token-shaped string"
    assert not re.search(r"(?i)\b(password|passphrase|api[_-]?key|secret)\b", TEXT)
    assert not re.search(r"\+?\d[\d\s().-]{9,}\d", TEXT), "a phone-shaped number"
    # The account id is public (the Makefile and ci.yml carry it); the site tag is a variable.
    assert "$env.CF_WEB_ANALYTICS_SITE_TAG" in TEXT


def test_it_names_no_price_and_no_item():
    """Prices and titles live in data/inventory.yaml; a copy typed here goes stale."""
    assert not re.search(r"\$\s?\d", TEXT.replace("${", "")), "a price typed into the workflow"
    data = yaml.safe_load((ROOT / "data/inventory.yaml").read_text(encoding="utf-8"))
    assert data["items"], "stale: no items"
    lowered = TEXT.lower()
    for item in data["items"]:
        assert item["title"].lower() not in lowered, item["title"]
        assert item["id"] not in lowered, item["id"]
        assert item["short_title"].lower() not in lowered, item["short_title"]
    for bundle in data["bundles"]:
        assert bundle["id"] not in lowered, bundle["id"]


def test_it_reads_the_account_and_dataset_the_repository_names():
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    account = re.search(r"^CF_ACCOUNT_ID := (\w+)", makefile, re.M).group(1)
    dataset = tomllib.loads((ROOT / "wrangler.toml").read_text(encoding="utf-8"))[
        "analytics_engine_datasets"
    ][0]["dataset"]
    sql_nodes = [NODES["Events, last 24 h"], NODES["Events, whole sale"]]
    for node_ in sql_nodes:
        parameters = node_["parameters"]
        assert (
            parameters["url"]
            == f"https://api.cloudflare.com/client/v4/accounts/{account}/analytics_engine/sql"
        )
        assert parameters["method"] == "POST"
        assert re.search(rf"\bFROM {dataset}\b", parameters["body"])
        assert "SUM(_sample_interval)" in parameters["body"], "counts must weigh sampled rows"
        assert "FORMAT JSON" in parameters["body"]
    assert "INTERVAL '1' DAY" in sql_nodes[0]["parameters"]["body"]
    assert "WHERE" not in sql_nodes[1]["parameters"]["body"], "the whole sale has no time filter"
    graphql = NODES["Web Analytics, last 24 h"]["parameters"]
    assert graphql["url"] == "https://api.cloudflare.com/client/v4/graphql"
    assert account in NODES["Web Analytics query"]["parameters"]["jsCode"]


def test_a_failed_request_does_not_stop_the_email():
    for name in ("Events, last 24 h", "Events, whole sale", "Web Analytics, last 24 h"):
        node_ = NODES[name]
        assert node_["onError"] == "continueRegularOutput", name
        assert node_["parameters"]["options"]["response"]["response"]["neverError"] is True, name


# The digest, run on rows shaped like the ones the endpoint writes

RUN_DIGEST = """
const { code, answers } = JSON.parse(await new Response(process.stdin).text());
const $ = name => ({ first: () => ({ json: answers[name] }) });
const $now = { setZone: () => ({ toFormat: () => '2026-10-04' }) };
const run = new Function('$', '$now', code);
process.stdout.write(JSON.stringify(run($, $now)));
"""
WRITE_POINTS = """
import { onRequestPost } from './functions/api/hit.js';
const points = [];
const env = { SALE_METRICS: { writeDataPoint: p => points.push(p) } };
for (const body of JSON.parse(await new Response(process.stdin).text())) {
  await onRequestPost({ request: new Request('https://x.test/api/hit', { method: 'POST', body: JSON.stringify(body) }), env });
}
process.stdout.write(JSON.stringify(points));
"""
NO_WEB = {"data": None, "errors": [{"message": "denied"}]}


def written(events):
    """The data points hit.js writes for these events."""
    result = node(WRITE_POINTS, json.dumps(events))
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def as_rows(points):
    """What the SQL in the workflow returns for those points: its own `blobN AS name` mapping."""
    select = NODES["Events, whole sale"]["parameters"]["body"]
    mapping = {int(n): name for n, name in re.findall(r"blob(\d) AS (\w+)", select)}
    counts = {}
    for point in points:
        key = tuple(sorted((name, point["blobs"][n - 1]) for n, name in mapping.items()))
        counts[key] = counts.get(key, 0) + point["doubles"][0]
    return [{**dict(key), "n": str(n)} for key, n in counts.items()]  # UInt64 comes back a string


def digest(recent, sale, web=NO_WEB):
    answers = {
        "Events, last 24 h": {"data": recent} if recent is not None else {"error": "x"},
        "Events, whole sale": {"data": sale} if sale is not None else {"error": "x"},
        "Web Analytics, last 24 h": web,
    }
    code = NODES["Write the digest"]["parameters"]["jsCode"]
    result = node(RUN_DIGEST, json.dumps({"code": code, "answers": answers}))
    assert result.returncode == 0, result.stderr
    (item,) = json.loads(result.stdout)
    return item["json"]


EVENTS = (
    [{"event": "visit", "source": "flyer"}] * 3
    + [{"event": "visit", "source": "facebook"}] * 2
    + [{"event": "view_item", "item": "sofa-sleeper"}] * 6
    + [{"event": "view_item", "item": "bar-stools"}] * 7
    + [{"event": "view_item", "item": "lamp"}] * 2
    + [{"event": "text_tap", "item": "sofa-sleeper", "source": "flyer"}] * 2
    + [{"event": "text_tap", "bundle": "bundle-wfh", "source": "nextdoor"}]
)


def test_the_digest_reports_what_the_endpoint_wrote():
    rows = as_rows(written(EVENTS))
    out = digest(rows, rows)
    text = out["text"]
    assert out["subject"] == "Moving sale — daily metrics 2026-10-04"
    assert "Visits from a tracked link, by source: flyer 3, facebook 2" in text
    assert "Text taps: 3 (by item: sofa-sleeper 2; by bundle: bundle-wfh 1)" in text
    assert "by item: bar-stools 7, sofa-sleeper 6, lamp 2" in text
    assert text.count("LAST 24 HOURS") == 1 and text.count("WHOLE SALE, SO FAR") == 1


def test_an_item_with_many_views_and_no_text_taps_is_named_a_repricing_candidate():
    rows = as_rows(written(EVENTS))
    text = digest(rows, rows)["text"]
    # bar-stools: 7 views, no taps. sofa-sleeper was texted about; lamp has too few views.
    assert "Repricing candidates (at least 5 views, no text taps): bar-stools 7" in text
    assert "sofa-sleeper 6" not in text.split("Repricing candidates")[1].splitlines()[0]
    assert "make reprice" in text


def test_the_digest_says_so_when_a_step_failed_and_still_goes_out():
    rows = as_rows(written(EVENTS))
    out = digest(None, rows)
    assert "unavailable: the Analytics Engine query failed" in out["text"]
    assert "WHOLE SALE, SO FAR" in out["text"] and "bar-stools" in out["text"]
    both = digest(None, None)
    assert both["text"].count("unavailable") >= 3
    assert "make reprice" in both["text"]


def test_an_empty_dataset_reads_as_none_not_as_an_error():
    text = digest([], [])["text"]
    assert "by source: none" in text
    assert "Text taps: 0" in text


def test_web_analytics_totals_and_referrers_are_reported():
    web = {
        "data": {
            "viewer": {
                "accounts": [
                    {
                        "totals": [{"count": 41, "sum": {"visits": 17}}],
                        "referrers": [
                            {"count": 12, "dimensions": {"refererHost": "m.facebook.com"}},
                            {"count": 5, "dimensions": {"refererHost": ""}},
                        ],
                    }
                ]
            }
        }
    }
    text = digest([], [], web)["text"]
    assert "Page views: 41, visits: 17" in text
    assert "Top referrers: m.facebook.com 12, direct 5" in text


def test_a_graphql_error_is_reported_even_when_partial_data_comes_with_it():
    # GraphQL answers 200 with an `errors` array and may still carry data: the figures beside
    # such an error are not to be trusted, so the email says unavailable instead of printing them.
    web = {
        "errors": [{"message": "unknown field"}],
        "data": {"viewer": {"accounts": [{"totals": [{"count": 41, "sum": {"visits": 17}}]}]}},
    }
    text = digest([], [], web)["text"]
    assert "unavailable: the GraphQL query returned errors" in text
    assert "Page views: 41" not in text


def test_the_web_analytics_query_filters_by_site_and_time_and_asks_for_the_documented_fields():
    code = NODES["Web Analytics query"]["parameters"]["jsCode"]
    for needle in (
        "rumPageloadEventsAdaptiveGroups",
        "accountTag: $account",
        "siteTag: $site",
        "datetime_geq: $since",
        "datetime_leq: $until",
        "sum { visits }",
        "refererHost",
    ):
        assert needle in code, needle
    body = NODES["Web Analytics, last 24 h"]["parameters"]["jsonBody"]
    assert body == "={{ JSON.stringify($('Web Analytics query').first().json.graphql) }}"


@pytest.mark.parametrize("name", ["Web Analytics query", "Write the digest"])
def test_each_code_node_is_valid_javascript(name):
    code = NODES[name]["parameters"]["jsCode"]
    result = node(
        "const code = JSON.parse(await new Response(process.stdin).text());"
        "new Function('$', '$now', '$env', code);",
        json.dumps(code),
    )
    assert result.returncode == 0, result.stderr


# The runbooks name what the owner must set, so a workflow that grows a variable or a credential
# cannot ship without the instruction to create it.

OPS = (ROOT / "docs/runbooks/ops.md").read_text(encoding="utf-8")
KUBELAB = (ROOT / "docs/runbooks/kubelab-integration.md").read_text(encoding="utf-8")
DECOMMISSION = (ROOT / "docs/runbooks/decommission.md").read_text(encoding="utf-8")


def test_every_variable_and_credential_the_workflow_uses_is_in_the_runbooks():
    variables = set(re.findall(r"\$env\.(\w+)", TEXT))
    assert variables == {"SALE_DIGEST_TO", "SALE_DIGEST_FROM", "CF_WEB_ANALYTICS_SITE_TAG"}
    credentials = {ref["name"] for n in FLOW["nodes"] for ref in n.get("credentials", {}).values()}
    for name in variables | credentials:
        assert name in OPS, f"ops.md does not say how to set {name}"
        assert name in KUBELAB or name == "CF_WEB_ANALYTICS_SITE_TAG", name


def test_the_runbook_names_the_token_permission_and_how_to_import():
    assert "Account Analytics" in OPS and "Read" in OPS
    assert "sale_metrics_daily_digest.json" in OPS
    assert "sale_metrics_daily_digest.json" in KUBELAB


def test_the_decommission_runbook_switches_the_digest_off_and_revokes_the_token_by_nov_15():
    by_nov_9 = DECOMMISSION.split("## By Nov 9")[1].split("## By Nov 15")[0]
    by_nov_15 = DECOMMISSION.split("## By Nov 15")[1]
    assert "sale_metrics_daily_digest.json" in by_nov_9 and "Active off" in by_nov_9
    assert "leaving-denver-analytics-read" in by_nov_15
    assert "2026-11-15" in OPS, "the token is created with a TTL that ends on the teardown date"
