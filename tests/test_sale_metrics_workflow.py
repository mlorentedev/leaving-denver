"""The daily metrics digest (FEAT-015, ADR-011) is owned by the kubelab repository, which imports it
as code (kubelab#2088, kubelab#2090). This repository keeps what is still true here:

- no second copy of the workflow (it would drift from the one that runs),
- the runbooks, which are the owner's only instructions for setting it up and for removing it,
- the contract between `functions/api/hit.js` and the digest's SQL. The columns the pointer README
  states are checked against hit.js everywhere. The digest's own SQL and Code node can only be
  checked against kubelab's file: set KUBELAB_SALE_DIGEST_JSON to a copy of
  `infra/n8n/workflows/sale-metrics-daily-digest.json` to run those; without it they are skipped
  (CI does not set it).

The shape of the data point itself, `[event, source, item, bundle, locale]`, is pinned in
tests/test_hit_function.py."""

import json
import os
import re
import tomllib
from pathlib import Path

import pytest
from sealed_helpers import node

ROOT = Path(__file__).resolve().parents[1]
OLD_COPY = ROOT / "integrations/n8n/workflows/sale_metrics_daily_digest.json"
POINTER = (ROOT / "integrations/n8n/README.md").read_text(encoding="utf-8")
OPS = (ROOT / "docs/runbooks/ops.md").read_text(encoding="utf-8")
KUBELAB = (ROOT / "docs/runbooks/kubelab-integration.md").read_text(encoding="utf-8")
DECOMMISSION = (ROOT / "docs/runbooks/decommission.md").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
ARCHITECTURE = (ROOT / "docs/ARCHITECTURE.md").read_text(encoding="utf-8")

KUBELAB_WORKFLOW = "infra/n8n/workflows/sale-metrics-daily-digest.json"
SOPS_PATHS = (
    "apps.services.automation.n8n.sale_digest.analytics_token",
    "apps.services.automation.n8n.sale_digest.recipient",
    "apps.services.automation.n8n.sale_digest.site_tag",
)
# What the workflow used to need and no longer does: n8n variables, hand-made credentials, and the
# n8n 2 switch that let a node read `$env`. A runbook that still names one sends the owner to set
# something nothing reads.
STALE = (
    "SALE_DIGEST_TO",
    "SALE_DIGEST_FROM",
    "CF_WEB_ANALYTICS_SITE_TAG",
    "sale-digest-smtp",
    "N8N_BLOCK_ENV_ACCESS_IN_NODE",
    "sale_metrics_daily_digest.json",
)


def section(text, heading):
    found = re.search(rf"^## {re.escape(heading)}.*?(?=^## |\Z)", text, re.M | re.S)
    assert found, f"no section {heading!r}"
    return found.group(0)


# What this repository owns: one pointer, no copy, and runbooks that match kubelab


def test_there_is_no_second_copy_of_the_workflow_and_the_pointer_names_the_one_that_runs():
    assert not OLD_COPY.exists(), "kubelab owns the digest; a copy here drifts"
    assert not list((ROOT / "integrations").rglob("*digest*")), "a digest workflow is back"
    assert KUBELAB_WORKFLOW in POINTER and "mlorentedev/kubelab" in POINTER
    assert "leaving_denver_sale_events" in POINTER


def test_the_pointer_names_the_dataset_the_repository_declares():
    wrangler = tomllib.loads((ROOT / "wrangler.toml").read_text(encoding="utf-8"))
    (dataset,) = wrangler["analytics_engine_datasets"]
    assert dataset["dataset"] in POINTER


def test_no_runbook_or_readme_sends_the_owner_to_set_what_nothing_reads_any_more():
    for name, text in (
        ("ops.md", OPS),
        ("kubelab-integration.md", KUBELAB),
        ("decommission.md", DECOMMISSION),
        ("README.md", README),
        ("ARCHITECTURE.md", ARCHITECTURE),
    ):
        for needle in STALE:
            assert needle not in text, f"{name} still names {needle}"


def test_the_integration_runbook_says_how_the_digest_gets_imported_and_what_it_needs():
    digest = section(KUBELAB, "3. Sale Metrics Daily Digest")
    assert KUBELAB_WORKFLOW in digest
    assert "make import-n8n ENV=prod" in digest
    assert "kubelab-smtp" in digest
    for path in SOPS_PATHS:
        assert path in digest, path
    assert "live" in digest, "it is live at import, with no switching on afterwards"
    assert "user token" in digest.lower() and "/user/tokens/verify" in digest
    assert "Switch Active" not in digest and "arrives switched off" not in digest


def test_the_ops_runbook_stores_the_three_values_in_kubelab_sops_without_echoing_them():
    sale = section(OPS, "Sale metrics")
    setup = sale.split("### Owner setup")[1].split("### Reading the digest")[0]
    for path in SOPS_PATHS:
        assert path in setup, path
    assert 'printf %s "$' in setup and "toolkit secrets set" in setup
    assert "--env prod --stdin" in setup
    assert "toolkit infra n8n import --env prod --dry-run" in setup
    assert "make import-n8n ENV=prod" in setup
    assert "Account Analytics" in setup and "Read" in setup
    assert "2026-11-15" in setup, "the token is created with a TTL that ends on the teardown date"
    assert "user token" in setup.lower(), "an account token fails kubelab's expiry check"
    for line in setup.splitlines():
        assert not (re.search(r"\becho\b", line) and "$" in line), f"a value is echoed: {line}"


def test_the_decommission_runbook_points_at_kubelabs_removal_and_keeps_the_shared_credential():
    by_nov_9 = section(DECOMMISSION, "By Nov 9")
    by_nov_15 = section(DECOMMISSION, "By Nov 15")
    assert "Removing the sale" in by_nov_9
    assert "infra/n8n/workflows/README.md" in by_nov_9
    assert "kubelab-smtp" in by_nov_9 and "stays" in by_nov_9
    assert "leaving-denver-analytics-read" in by_nov_15
    assert "2026-11-15" in OPS


# The columns the digest reads, as the pointer README states them, against what hit.js writes. This
# one runs everywhere; the tests below it need kubelab's file.


def pointer_columns():
    return {int(n): name for n, name in re.findall(r"`blob(\d)` (\w+)", POINTER)}


def test_hit_js_writes_each_field_in_the_blob_the_pointer_says_the_digest_reads():
    columns = pointer_columns()
    assert columns == {1: "event", 2: "source", 3: "item", 4: "bundle"}, "the pointer is stale"
    body = {
        "event": "text_tap",
        "source": "flyer",
        "item": "sofa-sleeper",
        "bundle": "bundle-wfh",
        "locale": "es",
    }
    (point,) = written([body])
    for index, name in columns.items():
        assert point["blobs"][index - 1] == body[name], f"blob{index} is not {name}"
    assert point["doubles"] == [1], "the digest sums the weight: one event is a count of one"


# What only kubelab's file can say: the digest reads back what hit.js wrote


@pytest.fixture(scope="module")
def nodes():
    path = os.environ.get("KUBELAB_SALE_DIGEST_JSON")
    if not path:
        pytest.skip("KUBELAB_SALE_DIGEST_JSON is not set: kubelab's copy of the digest is not here")
    flow = json.loads(Path(path).read_text(encoding="utf-8"))
    return {n["name"]: n for n in flow["nodes"]}


WRITE_POINTS = """
import { onRequestPost } from './functions/api/hit.js';
const points = [];
const env = { SALE_METRICS: { writeDataPoint: p => points.push(p) } };
for (const body of JSON.parse(await new Response(process.stdin).text())) {
  await onRequestPost({ request: new Request('https://x.test/api/hit', { method: 'POST', body: JSON.stringify(body) }), env });
}
process.stdout.write(JSON.stringify(points));
"""


def written(events):
    """The data points hit.js writes for these events."""
    result = node(WRITE_POINTS, json.dumps(events))
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def as_rows(nodes, points):
    """What the SQL in the workflow returns for those points: its own `blobN AS name` mapping."""
    select = nodes["Events, whole sale"]["parameters"]["body"]
    mapping = {int(n): name for n, name in re.findall(r"blob(\d) AS (\w+)", select)}
    counts = {}
    for point in points:
        key = tuple(sorted((name, point["blobs"][n - 1]) for n, name in mapping.items()))
        counts[key] = counts.get(key, 0) + point["doubles"][0]
    return [{**dict(key), "n": str(n)} for key, n in counts.items()]  # UInt64 comes back a string


EVENTS = (
    [{"event": "visit", "source": "flyer"}] * 3
    + [{"event": "visit", "source": "facebook"}] * 2
    + [{"event": "visit", "source": "share"}]
    + [{"event": "view_item", "item": "sofa-sleeper"}] * 6
    + [{"event": "view_item", "item": "bar-stools"}] * 7
    + [{"event": "view_item", "item": "lamp"}] * 2
    + [{"event": "text_tap", "item": "sofa-sleeper", "source": "flyer"}] * 2
    + [{"event": "text_tap", "bundle": "bundle-wfh", "source": "nextdoor"}]
)


def test_the_digest_sql_reads_back_what_the_endpoint_wrote(nodes):
    """The data contract only: kubelab's own tests own how the email looks (kubelab#2088)."""
    rows = {
        (r.get("event"), r.get("source"), r.get("item"), r.get("bundle")): int(r["n"])
        for r in as_rows(nodes, written(EVENTS))
    }
    assert rows[("visit", "flyer", "", "")] == 3
    assert rows[("visit", "share", "", "")] == 1
    assert rows[("view_item", "direct", "bar-stools", "")] == 7
    assert rows[("text_tap", "flyer", "sofa-sleeper", "")] == 2
    assert rows[("text_tap", "nextdoor", "", "bundle-wfh")] == 1


def test_the_digest_reads_the_account_and_dataset_the_repository_names(nodes):
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    account = re.search(r"^CF_ACCOUNT_ID := (\w+)", makefile, re.M).group(1)
    dataset = tomllib.loads((ROOT / "wrangler.toml").read_text(encoding="utf-8"))[
        "analytics_engine_datasets"
    ][0]["dataset"]
    for name in ("Events, last 24 h", "Events, whole sale"):
        parameters = nodes[name]["parameters"]
        assert account in parameters["url"]
        assert re.search(rf"\bFROM {dataset}\b", parameters["body"])
        assert "SUM(_sample_interval)" in parameters["body"], "counts must weigh sampled rows"
    assert account in nodes["Web Analytics query"]["parameters"]["jsCode"]
