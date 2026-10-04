"""The ops runbook names only things that exist, and monitoring stays dashboard-side (OPS-012).

A runbook is read in a bad moment. A command it names that no longer exists costs the owner
time exactly then, so every `make` target, CLI subcommand, workflow and script it names is
checked against the file that defines it.
"""

import json
import os
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

import pytest
import yaml

from leaving_denver.config import SITE_URL

ROOT = Path(__file__).resolve().parents[1]
RUNBOOKS = sorted((ROOT / "docs/runbooks").glob("*.md"))
OPS = ROOT / "docs/runbooks/ops.md"
PUBLIC = ROOT / "build" / "public"
TEMPLATES = ROOT / "src" / "leaving_denver" / "templates"

# Hosts Cloudflare Web Analytics loads from and reports to (ADR-005).
BEACON_SCRIPT_HOST = "static.cloudflareinsights.com"
BEACON_REPORT_HOST = "cloudflareinsights.com"


def make_targets() -> set[str]:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    return set(re.findall(r"^([a-zA-Z][\w-]*):", makefile, flags=re.MULTILINE))


def cli_subcommands() -> set[str]:
    out = subprocess.run(
        [sys.executable, "-m", "leaving_denver.cli", "--help"],
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
    ).stdout
    return set(re.search(r"\{([\w,-]+)\}", out).group(1).split(","))


def referenced(pattern: str, text: str) -> set[str]:
    return set(re.findall(pattern, text))


@pytest.mark.parametrize("runbook", RUNBOOKS, ids=lambda p: p.name)
def test_make_targets_named_in_a_runbook_exist(runbook):
    named = referenced(r"`make ([a-z][\w-]*)", runbook.read_text(encoding="utf-8"))
    assert not named - make_targets(), f"{runbook.name} names a make target that does not exist"


@pytest.mark.parametrize("runbook", RUNBOOKS, ids=lambda p: p.name)
def test_cli_subcommands_named_in_a_runbook_exist(runbook):
    named = referenced(r"uv run leaving-denver ([a-z][\w-]*)", runbook.read_text(encoding="utf-8"))
    assert not named - cli_subcommands(), f"{runbook.name} names a CLI subcommand that is gone"


@pytest.mark.parametrize("runbook", RUNBOOKS, ids=lambda p: p.name)
def test_workflows_and_scripts_named_in_a_runbook_exist(runbook):
    text = runbook.read_text(encoding="utf-8")
    for workflow in referenced(r"(?:--workflow|workflow run) ([\w.-]+\.yml)", text):
        assert (ROOT / ".github/workflows" / workflow).is_file(), workflow
    for script in referenced(r"scripts/[\w.-]+\.sh", text):
        assert (ROOT / script).is_file(), script


def test_ops_runbook_covers_what_the_issue_asks():
    """Each recurring task names the command that does it, so none can be dropped silently."""
    ops = OPS.read_text(encoding="utf-8")
    for needle in (
        "## Deploy and roll back",
        "make sold",
        "uv run leaving-denver pending",
        "recommended_list_price",
        "work phone",
        "SELLER_PHONE",
        "make ci-secrets",
        "make secrets",
        "make audit-deploy",
        "scripts/smoke.sh",
        "SOPS_AGE_KEY_FILE",
        "ADR-005",
    ):
        assert needle in ops, f"ops.md no longer mentions {needle!r}"


def test_the_runbook_covers_the_sealed_private_data():
    """AC13: SELLER_SEALED, its staleness, rotation (with deleting earlier deployments) and the
    decommission after the car deadline are written down, and the owner's two manual checks."""
    ops = OPS.read_text(encoding="utf-8")
    section = ops[ops.index("## The sealed private data") :]
    section = section[: section.index("\n## ", 3)] if "\n## " in section[3:] else section
    flat = " ".join(section.split())
    for needle in (
        "`SELLER_SEALED`",
        "make ci-secrets",
        "uv run leaving-denver seal",
        "as of the last `make ci-secrets` and deploy",
        "**Rotation.**",
        "delete the earlier Pages deployments",
        "**Decommission by 2026-11-09.**",
        "gh secret delete SELLER_SEALED --env production",
        "--env preview",
        "content-security-policy",
        "frame-ancestors 'none'",
        "3 s or less",
        "update `/seller/` now",
        "Write this down now. It is not stored anywhere.",
        "Enter alone does not make a new passphrase",
        "Passphrase (Enter to generate one):",
        "leaving-denver-seller",
        "dotf secrets set SELLER_PASSPHRASE",
        "https://leaving-denver.pages.dev/seller/",
        "dotf secrets run --only SELLER_PASSPHRASE -- make sold",
        "overwrites both the `SELLER_SEALED` secret and the Bitwarden field",
    ):
        assert needle in flat, f"the sealed-data section no longer says {needle!r}"
    seller = yaml.safe_load((ROOT / "data/inventory.yaml").read_text(encoding="utf-8"))["seller"]
    assert seller["vehicle_deadline"] == "2026-11-09"


def test_the_uptime_keyword_is_on_the_page_the_monitor_fetches():
    """The runbook tells the owner what to type into the monitor; that string must be
    on the home page, or the monitor alerts from its first check (or never alerts)."""
    ops = OPS.read_text(encoding="utf-8")
    keyword = re.search(r"Keyword: `([^`]+)`", ops)
    assert keyword, "ops.md names no uptime keyword"
    assert f"`{SITE_URL}/`" in ops, "ops.md does not name the production home page to monitor"
    html = (PUBLIC / "index.html").read_text(encoding="utf-8")
    title = re.search(r"<title>(.*?)</title>", html, flags=re.DOTALL).group(1)
    assert keyword.group(1) in title


def csp_blocks_beacon(policy: str) -> list[str]:
    """What a Content-Security-Policy would stop Web Analytics loading or reporting."""
    directives = {}
    for part in filter(str.strip, policy.split(";")):
        name, *sources = part.split()
        directives[name.lower()] = sources

    def allows(directive: str, host: str) -> bool:
        sources = directives.get(directive, directives.get("default-src"))
        return sources is None or any(
            s == "*" or s == host or s == f"https://{host}" or s == f"https://*.{host}"
            for s in sources
        )

    blocked = []
    if not allows("script-src", BEACON_SCRIPT_HOST):
        blocked.append(f"script-src needs {BEACON_SCRIPT_HOST}")
    if not allows("connect-src", BEACON_REPORT_HOST):
        blocked.append(f"connect-src needs {BEACON_REPORT_HOST}")
    return blocked


@pytest.mark.parametrize(
    ("policy", "blocked"),
    [
        ("default-src 'self'", 2),
        ("script-src 'self'; connect-src 'self'", 2),
        ("script-src 'self' https://static.cloudflareinsights.com; connect-src 'self'", 1),
        (
            "script-src 'self' https://static.cloudflareinsights.com; "
            "connect-src 'self' https://cloudflareinsights.com",
            0,
        ),
        ("img-src 'self'", 0),
    ],
)
def test_csp_check_notices_a_policy_that_would_stop_the_beacon(policy, blocked):
    assert len(csp_blocks_beacon(policy)) == blocked


class _CspMeta(HTMLParser):
    def __init__(self):
        super().__init__()
        self.policies = []

    def handle_starttag(self, tag, attrs):
        attrs = {name: value or "" for name, value in attrs}
        if tag == "meta" and attrs.get("http-equiv", "").lower() == "content-security-policy":
            self.policies.append(attrs.get("content", ""))


def csp_meta_policies(html):
    """The content of every CSP <meta>, read by an HTML parser so attribute order,
    quoting and spacing cannot hide one."""
    parser = _CspMeta()
    parser.feed(html)
    return parser.policies


def test_the_csp_scan_reads_meta_tags_however_they_are_written():
    for tag in (
        '<meta http-equiv="Content-Security-Policy" content="script-src \'self\'">',
        '<meta content="script-src \'self\'" http-equiv="Content-Security-Policy">',
        "<meta http-equiv = 'content-security-policy' content = \"script-src 'self'\">",
        "<META HTTP-EQUIV=Content-Security-Policy CONTENT=\"script-src 'self'\">",
    ):
        assert csp_meta_policies(tag) == ["script-src 'self'"], tag
    assert csp_meta_policies('<meta name="viewport" content="width=device-width">') == []


def test_no_csp_stops_the_cloudflare_beacon():
    """ADR-005: Web Analytics is enabled in the Pages dashboard and Cloudflare injects the
    beacon at the edge. A CSP added later would silently break it, so it must allow it.

    Every path but /seller/* (ADR-007): the static headers and the page templates may carry no
    policy that blocks it, and the middleware sends none outside /seller/."""
    from leaving_denver.site_builder import PAGES_HEADERS

    policies = re.findall(r"Content-Security-Policy:\s*(.+)", PAGES_HEADERS, flags=re.IGNORECASE)
    for template in TEMPLATES.rglob("*.html"):
        policies += csp_meta_policies(template.read_text(encoding="utf-8"))
    for policy in policies:
        assert not csp_blocks_beacon(policy), policy


def middleware_policy(path: str) -> str | None:
    """The Content-Security-Policy functions/_middleware.js puts on a response for this path."""
    script = f"""
import {{ onRequest }} from './functions/_middleware.js';
const response = await onRequest({{
  env: {{}}, request: new Request('https://leaving-denver.pages.dev{path}'),
  next: () => new Response('page')
}});
console.log(JSON.stringify(response.headers.get('Content-Security-Policy')));
"""
    done = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


@pytest.mark.parametrize(
    "path", ["/", "/es/", "/i/sofa-sleeper/", "/es/i/sofa-sleeper/", "/robots.txt", "/sellers/"]
)
def test_the_middleware_sets_no_policy_outside_seller(path):
    """ADR-005 holds on every other path: a policy would stop the beacon for buyers."""
    assert middleware_policy(path) is None


def test_the_one_exception_is_seller_and_it_does_block_the_beacon():
    """ADR-007: the page that holds decrypted floors takes no third-party script, so the
    beacon is deliberately blocked there. This pins the exception to /seller/*."""
    policy = middleware_policy("/seller/")
    assert policy
    assert csp_blocks_beacon(policy) == [
        f"script-src needs {BEACON_SCRIPT_HOST}",
        f"connect-src needs {BEACON_REPORT_HOST}",
    ]


def test_the_repo_ships_no_analytics_beacon():
    """The beacon is switched on in the Pages dashboard (ADR-005). A copy in a template
    would double-count every visit and survive turning the setting off."""
    for template in TEMPLATES.rglob("*.html"):
        assert "cloudflareinsights" not in template.read_text(encoding="utf-8"), template.name


@pytest.mark.parametrize("runbook", RUNBOOKS, ids=lambda p: p.name)
def test_adrs_named_in_a_runbook_exist(runbook):
    for number in referenced(r"ADR-(\d{3})", runbook.read_text(encoding="utf-8")):
        assert list((ROOT / "docs/adr").glob(f"adr-{number}-*.md")), f"ADR-{number}"
