"""The Cloudflare configuration as Terraform (OPS-014, ADR-012).

Nothing here talks to Cloudflare. What these tests pin is what the owner relies on when running
`make infra-*` from a terminal: the owner's email and the token never land in a tracked file or
on a command line, the state that holds them stays out of git, every managed resource is also
adopted by an import block (a missing one would plan a duplicate), and `make check` fails on
Terraform that does not format or validate and only skips when Terraform is not installed.
"""

import json
import os
import re
import shutil
import stat
import subprocess
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TF_DIR = ROOT / "infra/terraform/cloudflare"
SOPS_FILE = "data/private.sops.yaml"

EMAIL = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+")
# Cloudflare API tokens are 40 characters of [A-Za-z0-9_-], mixed case with digits. A 32-hex
# account id is not one, and neither is a long snake_case resource name.
TOKEN = re.compile(
    r"(?<![\w-])(?=[\w-]*\d)(?=[\w-]*[A-Z])(?=[\w-]*[a-z])[A-Za-z0-9_-]{40}(?![\w-])"
)

needs_bash_tools = pytest.mark.skipif(
    not (shutil.which("bash") and shutil.which("make")), reason="needs bash and make"
)


def terraform_files() -> list[Path]:
    """Every .tf and tfvars file under the repo, never the provider cache or dependencies."""
    skipped = {".terraform", ".venv", "node_modules", ".git", "build"}
    return sorted(
        path
        for pattern in ("*.tf", "*.tfvars", "*.tfvars.example", "*.tfvars.json")
        for path in ROOT.rglob(pattern)
        if not skipped & set(path.relative_to(ROOT).parts)
    )


def secrets_in(text: str) -> list[str]:
    return [m.group(0) for m in EMAIL.finditer(text)] + [m.group(0) for m in TOKEN.finditer(text)]


def tf_text() -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in sorted(TF_DIR.glob("*.tf")))


# --- nothing private is ever tracked ---------------------------------------------------------


def test_the_scanner_catches_what_it_is_there_for(tmp_path):
    """A scan that finds nothing in a clean tree is only worth anything if it finds something
    in a dirty one."""
    assert secrets_in('owner = "someone@example.com"')
    assert secrets_in('token = "' + "aB3_-" * 8 + '"')
    assert not secrets_in('account_id = "76967f5ede1ce50efce34d90b7e94958"')
    assert not secrets_in('id = "00000000-0000-0000-0000-000000000000"')
    assert not secrets_in("cloudflare_zero_trust_access_application")


def test_no_terraform_file_holds_an_email_or_a_token():
    files = terraform_files()
    assert TF_DIR / "main.tf" in files, "the scan must see the module it guards"
    for path in files:
        assert not secrets_in(path.read_text(encoding="utf-8")), (
            f"{path.relative_to(ROOT)} holds an email or a token-looking string"
        )


@pytest.mark.parametrize(
    "path",
    [
        "infra/terraform/cloudflare/terraform.tfstate",
        "infra/terraform/cloudflare/terraform.tfstate.backup",
        "infra/terraform/cloudflare/.terraform/providers/x",
        "infra/terraform/cloudflare/plan.tfplan",
        "infra/terraform/cloudflare/ids.auto.tfvars",
        "infra/terraform/cloudflare/secret.tfvars",
        "infra/terraform/cloudflare/secret.tfvars.json",
        "infra/terraform/cloudflare/crash.log",
        "infra/terraform/cloudflare/override.tf",
    ],
)
def test_state_plans_variables_and_crash_logs_are_ignored(path):
    ignored = subprocess.run(["git", "check-ignore", "-q", path], cwd=ROOT).returncode == 0
    assert ignored, f"{path} must be ignored: it can hold the owner's email"


@pytest.mark.parametrize(
    "path",
    [
        "infra/terraform/cloudflare/main.tf",
        "infra/terraform/cloudflare/.terraform.lock.hcl",
        "infra/terraform/cloudflare/ids.auto.tfvars.example",
    ],
)
def test_the_configuration_the_lock_and_the_example_are_tracked(path):
    ignored = subprocess.run(["git", "check-ignore", "-q", path], cwd=ROOT).returncode == 0
    assert not ignored, f"{path} is part of the change and must not be ignored"
    assert (ROOT / path).exists()


# --- the module -----------------------------------------------------------------------------


def declared(kind: str) -> set[tuple[str, str]]:
    return set(re.findall(rf'^{kind} "([\w]+)" "([\w]+)"', tf_text(), flags=re.MULTILINE))


def test_every_managed_resource_is_adopted_by_an_import_block():
    """Without one, the first apply would try to create what already exists."""
    managed = {f"{kind}.{name}" for kind, name in declared("resource")}
    imported = set(re.findall(r"^\s*to\s*=\s*([\w.]+)", tf_text(), flags=re.MULTILINE))
    assert managed
    assert managed == imported


def test_the_owner_email_is_a_sensitive_variable_with_no_value_in_the_repo():
    block = re.search(r'variable "owner_email" \{(.*?)\n\}', tf_text(), flags=re.DOTALL).group(1)
    assert "sensitive   = true" in block
    assert "default" not in block, "a default would be a value in a public repository"


def test_the_pages_project_is_not_fought_over_with_wrangler_or_destroyed():
    """wrangler.toml owns the deployment and ADR-008 keeps the name: Terraform manages neither."""
    block = re.search(
        r'resource "cloudflare_pages_project" "site" \{(.*?)\n\}', tf_text(), flags=re.DOTALL
    ).group(1)
    assert "prevent_destroy = true" in block
    ignored = re.search(r"ignore_changes\s*=\s*\[(.*?)\]", block, flags=re.DOTALL).group(1)
    assert {"deployment_configs", "build_config"} <= {i.strip() for i in ignored.split(",")}
    assert "deployment_configs =" not in block.split("lifecycle")[0]


def test_access_allows_the_owner_address_alone():
    text = tf_text()
    policy = re.search(
        r'resource "cloudflare_zero_trust_access_policy" "owner_only" \{(.*?)\n\}',
        text,
        flags=re.DOTALL,
    ).group(1)
    assert 'decision   = "allow"' in policy
    assert "email = { email = var.owner_email }" in policy
    # An email domain or "everyone" would let in more than one address.
    for wider in ("email_domain", "everyone", "any_valid_service_token"):
        assert wider not in policy


def resource_block(kind: str, name: str) -> str:
    return re.search(
        rf'resource "{kind}" "{name}" \{{(.*?)\n\}}', tf_text(), flags=re.DOTALL
    ).group(1)


def test_every_resource_that_closes_or_opens_seller_cannot_be_destroyed():
    """The Pages project (ADR-008) and the three Access objects: destroying or replacing any of
    them closes /seller/, or changes the audience the middleware checks."""
    resources = declared("resource")
    assert len(resources) == 4
    for kind, name in resources:
        assert "prevent_destroy = true" in resource_block(kind, name), f"{kind}.{name}"


def test_the_policy_has_one_include_entry_an_email_and_no_require_or_exclude():
    """`require` narrows and `exclude` carves out, but either one is a second rule to read.
    Exactly one address is the whole policy."""
    policy = resource_block("cloudflare_zero_trust_access_policy", "owner_only")
    flat = " ".join(policy.split())
    assert "include = [{ email = { email = var.owner_email } }]" in flat
    assert not re.search(r"^\s*(require|exclude)\s*=", policy, flags=re.MULTILINE)


def test_the_application_only_ever_allows_the_one_time_pin_provider():
    """Absent is the dashboard's "all providers"; present must be the one provider this module
    manages, never an id typed in or a provider added by hand."""
    app = resource_block("cloudflare_zero_trust_access_application", "seller")
    found = re.search(r"allowed_idps\s*=\s*\[(.*?)\]", app, flags=re.DOTALL)
    if found:
        assert (
            found.group(1).strip()
            == "cloudflare_zero_trust_access_identity_provider.one_time_pin.id"
        )


def test_access_covers_the_seller_paths_on_production_and_preview_hostnames():
    """A path ending /* does not cover its parent, and a preview is another hostname."""
    app = re.search(
        r'resource "cloudflare_zero_trust_access_application" "seller" \{(.*?)\n\}',
        tf_text(),
        flags=re.DOTALL,
    ).group(1)
    uris = set(re.findall(r'uri\s*=\s*"([^"]+)"', app))
    assert uris == {
        "leaving-denver.pages.dev/seller",
        "leaving-denver.pages.dev/seller/*",
        "*.leaving-denver.pages.dev/seller",
        "*.leaving-denver.pages.dev/seller/*",
    }


def test_the_audience_the_middleware_checks_is_exposed_but_never_written():
    """ACCESS_AUD is a Pages variable. Terraform reads the audience; writing it would put the
    secret binding in the project's deployment_configs, which wrangler owns."""
    assert 'output "access_aud"' in tf_text()
    assert "env_vars" not in tf_text() and "deployment_configs =" not in tf_text()


# --- the Makefile ---------------------------------------------------------------------------

TOKEN_VALUE = "tok-" + "x" * 36
EMAIL_VALUE = "owner@example.test"


def stub(directory: Path, name: str, script: str) -> None:
    path = directory / name
    path.write_text("#!/bin/bash\n" + textwrap.dedent(script), encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


@pytest.fixture
def toolbox(tmp_path):
    """sops and terraform stubs first on PATH. The first holds a token and an email unless
    told otherwise, the second records how it was called and with what environment."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "terraform.log"
    stub(
        bin_dir,
        "sops",
        f"""\
        # sops -d --extract '["<key>"]' <file>
        case "$3" in
          *cloudflare_terraform_token*|*cloudflare_pages_token*) echo "{TOKEN_VALUE}" ;;
          *owner_email*) [ -n "$NO_EMAIL" ] && exit 1; echo "{EMAIL_VALUE}" ;;
          *) exit 1 ;;
        esac
        """,
    )
    stub(
        bin_dir,
        "terraform",
        f"""\
        printf 'argv: %s\\n' "$*" >> "{log}"
        printf 'token_in_env: %s\\n' "${{CLOUDFLARE_API_TOKEN:-unset}}" >> "{log}"
        printf 'email_in_env: %s\\n' "${{TF_VAR_owner_email:-unset}}" >> "{log}"
        printf 'account_in_env: %s\\n' "${{TF_VAR_account_id:-unset}}" >> "{log}"
        [ -n "$TF_FAIL" ] && exit 1
        case " $* " in
          *" show "*) if [ -n "$PLAN_JSON" ]; then cat "$PLAN_JSON"; else echo '{{"resource_changes": []}}'; fi ;;
        esac
        exit 0
        """,
    )
    return bin_dir, log


def make(args, toolbox, **env):
    bin_dir, _ = toolbox
    full = {
        **os.environ,
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "CI": "",
        **env,
    }
    return subprocess.run(
        ["make", "--no-print-directory", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=full,
    )


@needs_bash_tools
@pytest.mark.parametrize("target", ["infra-init", "infra-plan"])
def test_terraform_gets_the_token_and_email_in_its_environment_never_on_argv(target, toolbox):
    done = make([target], toolbox)
    assert done.returncode == 0, done.stderr
    log = toolbox[1].read_text(encoding="utf-8")
    assert f"token_in_env: {TOKEN_VALUE}" in log
    assert f"email_in_env: {EMAIL_VALUE}" in log
    assert "account_in_env: 76967f5ede1ce50efce34d90b7e94958" in log
    argv = re.search(r"^argv: (.*)$", log, flags=re.MULTILINE).group(1)
    assert TOKEN_VALUE not in argv and EMAIL_VALUE not in argv
    assert "-input=false" in argv, "a prompt in a script is a hang"
    assert TOKEN_VALUE not in done.stdout + done.stderr
    assert EMAIL_VALUE not in done.stdout + done.stderr


@needs_bash_tools
def test_a_missing_owner_email_stops_before_terraform_runs(toolbox):
    """Planning without the email would plan to change the allow policy to nobody."""
    done = make(["infra-plan"], toolbox, NO_EMAIL="1")
    assert done.returncode != 0
    assert "owner_email" in done.stderr and "make secrets" in done.stderr
    assert not toolbox[1].exists(), "terraform must not have been started"


@needs_bash_tools
def test_the_wider_token_can_be_swapped_for_the_deploy_one_for_a_pages_only_plan(toolbox):
    done = make(["infra-plan", "TF_TOKEN_KEY=cloudflare_pages_token"], toolbox)
    assert done.returncode == 0, done.stderr


def saved_plan(tmp_path, *changes):
    """A saved plan in a scratch TF_DIR (the owner's own saved plan in the real directory must
    neither fail a test nor be deleted by it) and the `terraform show -json` the stub gives for
    it. A change is (address, actions[, importing[, extra keys of `change`]])."""
    (tmp_path / "plan.tfplan").write_text("saved by the stub", encoding="utf-8")
    resource_changes = []
    for address, actions, *rest in changes:
        change = {"actions": actions}
        if rest and rest[0]:
            change["importing"] = {"id": "x"}
        if len(rest) > 1:
            change.update(rest[1])
        resource_changes.append({"address": address, "change": change})
    shown = tmp_path / "plan.json"
    shown.write_text(json.dumps({"resource_changes": resource_changes}), encoding="utf-8")
    return {"PLAN_JSON": str(shown)}


@needs_bash_tools
def test_apply_applies_only_a_saved_plan_and_never_in_ci(toolbox, tmp_path):
    tf_dir = f"TF_DIR={tmp_path}"
    plan = tmp_path / "plan.tfplan"
    refused = make(["infra-apply", tf_dir], toolbox)
    assert refused.returncode != 0 and "make infra-plan" in refused.stderr
    assert not toolbox[1].exists()

    env = saved_plan(tmp_path, ("cloudflare_pages_project.site", ["no-op"], True))
    in_ci = make(["infra-apply", tf_dir], toolbox, CI="true", **env)
    assert in_ci.returncode != 0 and "never by CI" in in_ci.stderr
    assert not toolbox[1].exists()

    applied = make(["infra-apply", tf_dir], toolbox, **env)
    assert applied.returncode == 0, applied.stderr
    assert re.search(r"^argv: .*apply .*plan\.tfplan$", toolbox[1].read_text(), re.MULTILINE)
    assert "-auto-approve" not in toolbox[1].read_text()
    assert not plan.exists(), "a plan is applied once"


def applied(toolbox) -> bool:
    return toolbox[1].exists() and "apply " in toolbox[1].read_text(encoding="utf-8")


@needs_bash_tools
def test_an_import_only_plan_applies_without_an_override(toolbox, tmp_path):
    env = saved_plan(
        tmp_path,
        ("cloudflare_pages_project.site", ["no-op"], True),
        ("cloudflare_zero_trust_access_application.seller", ["no-op"], True),
    )
    done = make(["infra-apply", f"TF_DIR={tmp_path}"], toolbox, **env)
    assert done.returncode == 0, done.stderr
    assert applied(toolbox)


@needs_bash_tools
def test_a_plan_that_changes_something_is_refused_until_the_override_and_says_what(
    toolbox, tmp_path
):
    """The first apply is meant to adopt, so an update in it is the owner's cue to stop: the
    audience check and the reconcile loop come first. Routine changes say so with CHANGES=1."""
    env = saved_plan(
        tmp_path,
        ("cloudflare_pages_project.site", ["no-op"], True),
        ("cloudflare_zero_trust_access_application.seller", ["update"]),
    )
    plan = tmp_path / "plan.tfplan"
    refused = make(["infra-apply", f"TF_DIR={tmp_path}"], toolbox, **env)
    assert refused.returncode != 0
    assert "cloudflare_zero_trust_access_application.seller" in refused.stderr
    assert "update" in refused.stderr and "CHANGES=1" in refused.stderr
    assert not applied(toolbox), "refused means terraform apply never ran"
    assert plan.exists(), "a refused plan is kept to be read again"

    allowed = make(["infra-apply", f"TF_DIR={tmp_path}", "CHANGES=1"], toolbox, **env)
    assert allowed.returncode == 0, allowed.stderr
    assert applied(toolbox)


POLICY_ADDRESS = "cloudflare_zero_trust_access_policy.owner_only"
VALUES = {"decision": "allow", "include": [{"email": {"email": "owner@example.test"}}]}


@needs_bash_tools
def test_an_update_that_only_changes_the_sensitivity_marking_is_not_a_change(toolbox, tmp_path):
    """The owner's first real plan showed "1 to change" on the policy: before and after are
    identical and only `*_sensitive` differs, because the sensitive owner_email marks the whole
    include list. That is the import, not a change, and it must not need the override."""
    same = {
        "before": VALUES,
        "after": VALUES,
        "after_unknown": {},
        "before_sensitive": {"include": [{"email": {}}]},
        "after_sensitive": {"include": True},
    }
    env = saved_plan(tmp_path, (POLICY_ADDRESS, ["update"], True, same))
    done = make(["infra-apply", f"TF_DIR={tmp_path}"], toolbox, **env)
    assert done.returncode == 0, done.stderr
    assert applied(toolbox)


@needs_bash_tools
@pytest.mark.parametrize(
    "change",
    [
        {"before": VALUES, "after": {**VALUES, "decision": "deny"}, "after_unknown": {}},
        {
            "before": VALUES,
            "after": {**VALUES, "include": [{"email": {"email": "other@example.test"}}]},
            "after_unknown": {},
        },
        {"before": VALUES, "after": VALUES, "after_unknown": {"id": True}},
    ],
    ids=["a value", "the address", "something unknown until apply"],
)
def test_an_update_with_a_real_difference_still_needs_the_override(toolbox, tmp_path, change):
    env = saved_plan(tmp_path, (POLICY_ADDRESS, ["update"], True, change))
    refused = make(["infra-apply", f"TF_DIR={tmp_path}"], toolbox, **env)
    assert refused.returncode != 0 and "CHANGES=1" in refused.stderr
    assert "example.test" not in refused.stderr, "the plan's values never reach the output"
    assert not applied(toolbox)
    assert make(["infra-apply", f"TF_DIR={tmp_path}", "CHANGES=1"], toolbox, **env).returncode == 0


@needs_bash_tools
def test_a_destroy_goes_through_only_with_its_own_explicit_switch(toolbox, tmp_path):
    """Decommission (runbook) removes the Access objects through the same guarded command, with
    DESTROY=1 and nothing else in the plan. CHANGES=1 does not stand in for it."""
    env = saved_plan(tmp_path, ("cloudflare_zero_trust_access_application.seller", ["delete"]))
    plan = [f"TF_DIR={tmp_path}"]
    assert make(["infra-apply", *plan, "CHANGES=1"], toolbox, **env).returncode != 0
    assert not applied(toolbox)
    done = make(["infra-apply", *plan, "DESTROY=1"], toolbox, **env)
    assert done.returncode == 0, done.stderr
    assert applied(toolbox)


@needs_bash_tools
def test_the_destroy_switch_does_not_wave_through_a_change_or_a_replacement(toolbox, tmp_path):
    for changes in (
        [("cloudflare_pages_project.site", ["update"], False, {"before": {}, "after": {"a": 1}})],
        [("cloudflare_zero_trust_access_application.seller", ["delete", "create"])],
    ):
        env = saved_plan(tmp_path, *changes)
        done = make(["infra-apply", f"TF_DIR={tmp_path}", "DESTROY=1"], toolbox, **env)
        assert done.returncode != 0
        assert not applied(toolbox)


@needs_bash_tools
@pytest.mark.parametrize("actions", [["delete"], ["delete", "create"], ["create", "delete"]])
def test_a_destroy_or_a_replacement_is_refused_even_with_the_override(toolbox, tmp_path, actions):
    """A replaced Access application has a new audience and closes /seller/ until ACCESS_AUD
    is set again, and `prevent_destroy` already refuses the rest. Removing a resource on purpose
    is the decommission runbook's step, with its own switch (DESTROY=1)."""
    env = saved_plan(tmp_path, ("cloudflare_zero_trust_access_application.seller", actions))
    done = make(["infra-apply", f"TF_DIR={tmp_path}", "CHANGES=1"], toolbox, **env)
    assert done.returncode != 0
    assert "cloudflare_zero_trust_access_application.seller" in done.stderr
    assert "destroy" in done.stderr
    assert not applied(toolbox)


@needs_bash_tools
def test_a_plan_terraform_cannot_show_is_not_applied(toolbox, tmp_path):
    saved_plan(tmp_path)
    done = make(["infra-apply", f"TF_DIR={tmp_path}"], toolbox, TF_FAIL="1")
    assert done.returncode != 0
    assert not applied(toolbox)


@needs_bash_tools
def test_check_runs_terraform_fmt_and_validate_and_fails_when_they_do(toolbox):
    passed = make(["infra-check"], toolbox, CLOUDFLARE_API_TOKEN="")
    assert passed.returncode == 0, passed.stderr
    log = toolbox[1].read_text(encoding="utf-8")
    assert "fmt -check" in log and "init -backend=false" in log and "validate" in log
    # No credential is read for a check that anyone, CI included, runs.
    assert set(re.findall(r"^token_in_env: (.*)$", log, flags=re.MULTILINE)) == {"unset"}
    assert set(re.findall(r"^email_in_env: (.*)$", log, flags=re.MULTILINE)) == {"unset"}
    failed = make(["infra-check"], toolbox, TF_FAIL="1")
    assert failed.returncode != 0, "a malformed module must fail make check, not be skipped"


@needs_bash_tools
def test_check_skips_with_a_notice_when_terraform_is_not_installed(tmp_path):
    bare = tmp_path / "bare"
    bare.mkdir()
    for tool in ("make", "bash", "sh"):
        (bare / tool).symlink_to(shutil.which(tool))
    done = subprocess.run(
        ["make", "--no-print-directory", "infra-check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env={"PATH": str(bare), "HOME": str(tmp_path)},
    )
    assert done.returncode == 0, done.stderr
    assert "terraform is not installed" in done.stdout


@needs_bash_tools
def test_make_check_includes_the_terraform_check():
    plan = subprocess.run(
        ["make", "-n", "check"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout
    assert "terraform -chdir=infra/terraform/cloudflare validate" in plan


# --- scripts/infra-ids.sh -------------------------------------------------------------------

APP = "11111111-1111-1111-1111-111111111111"
POLICY = "22222222-2222-2222-2222-222222222222"
IDP = "33333333-3333-3333-3333-333333333333"


def access_state(**over):
    state = {
        "organizations": 200,
        "apps": [
            {
                "id": APP,
                "domain": "leaving-denver.pages.dev/seller",
                "destinations": [{"uri": "leaving-denver.pages.dev/seller/*"}],
                "policies": [{"id": POLICY, "include": [{"email": {"email": EMAIL_VALUE}}]}],
            },
            {"id": "44444444-4444-4444-4444-444444444444", "domain": "kuma.example.test"},
        ],
        "idps": [{"id": IDP, "type": "onetimepin"}, {"id": "x", "type": "github"}],
        "policies": [{"id": POLICY}],
    }
    state.update(over)
    return state


def run_ids(tmp_path, state):
    """The script against a stubbed curl that answers like the Cloudflare API and records the
    argv and stdin it was given."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    (tmp_path / "state.json").write_text(json.dumps(state), encoding="utf-8")
    seen = tmp_path / "curl.log"
    stub(
        bin_dir,
        "curl",
        f"""\
        printf 'argv: %s\\n' "$*" >> "{seen}"
        cat >> "{seen}"
        python3 - "$@" <<'PY'
        import json, sys
        state = json.load(open("{tmp_path / "state.json"}"))
        url = [a for a in sys.argv[1:] if a.startswith("http")][0]
        name = url.rsplit("/", 1)[1]
        if name == "organizations":
            code = state["organizations"]
            if code != 200:
                sys.exit(22)
            print(json.dumps({{"success": True, "result": {{"name": "team"}}}}))
        else:
            key = {{"apps": "apps", "identity_providers": "idps", "policies": "policies"}}[name]
            print(json.dumps({{"success": True, "result": state[key]}}))
        PY
        """,
    )
    return subprocess.run(
        ["bash", str(ROOT / "scripts/infra-ids.sh")],
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
            "CLOUDFLARE_API_TOKEN": TOKEN_VALUE,
            "CF_ACCOUNT_ID": "acct",
        },
    ), seen


needs_jq = pytest.mark.skipif(
    not (shutil.which("bash") and shutil.which("jq")), reason="needs bash and jq"
)


@needs_jq
def test_ids_finds_the_application_its_policy_and_the_one_time_pin(tmp_path):
    done, seen = run_ids(tmp_path, access_state())
    assert done.returncode == 0, done.stderr
    assert done.stdout.splitlines() == [
        f'access_idp_id    = "{IDP}"',
        f'access_app_id    = "{APP}"',
        f'access_policy_id = "{POLICY}"',
    ]
    # Ids only: neither the policy body (the email) nor the token is printed.
    assert EMAIL_VALUE not in done.stdout + done.stderr
    assert TOKEN_VALUE not in done.stdout + done.stderr
    # The token travelled on curl's stdin, not on a command line `ps` can read.
    log = seen.read_text(encoding="utf-8")
    assert not any(TOKEN_VALUE in line for line in log.splitlines() if line.startswith("argv:"))
    assert TOKEN_VALUE in log


@needs_jq
def test_ids_refuses_a_token_that_cannot_read_access(tmp_path):
    """The lists come back empty for such a token. Reading that as "nothing is configured"
    would send the owner to recreate an application that is protecting /seller/ right now."""
    done, _ = run_ids(tmp_path, access_state(organizations=403, apps=[], idps=[]))
    assert done.returncode != 0
    assert done.stdout == ""
    assert "cannot read Zero Trust Access" in done.stderr


@needs_jq
@pytest.mark.parametrize(
    "change",
    [
        {"apps": []},
        {"apps": access_state()["apps"][:1] * 2},
        {"idps": []},
    ],
    ids=["no application", "two applications", "no one-time PIN"],
)
def test_ids_stops_unless_each_object_is_found_exactly_once(tmp_path, change):
    done, _ = run_ids(tmp_path, access_state(**change))
    assert done.returncode != 0
    assert done.stdout == ""
    assert "expected exactly one" in done.stderr


@needs_jq
def test_ids_warns_when_the_policy_is_not_a_reusable_one(tmp_path):
    """The import block adopts a reusable policy. An application-scoped one would only fail at
    the import, so the owner is told here and the ids still come out."""
    done, _ = run_ids(tmp_path, access_state(policies=[]))
    assert done.returncode == 0, done.stderr
    assert f'access_policy_id = "{POLICY}"' in done.stdout
    assert "not a reusable policy" in done.stderr
    quiet, _ = run_ids(tmp_path, access_state())
    assert "warning" not in quiet.stderr


GUARD = ROOT / "scripts/infra-plan-guard.py"


def guard(stdin: str, *flags: str):
    return subprocess.run(
        [shutil.which("python3") or "python3", str(GUARD), *flags],
        input=stdin,
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize(
    "stdin",
    ["", "not json", "{}", '{"format_version": "1.2"}', '{"resource_changes": null}'],
    ids=["empty", "malformed", "empty object", "no resource_changes", "null resource_changes"],
)
def test_the_guard_does_not_read_a_plan_without_resource_changes_as_an_empty_one(stdin):
    """A show that failed or printed something else must not look like "nothing to change"."""
    done = guard(stdin, "--allow-changes", "--allow-destroy")
    assert done.returncode == 2
    assert "could not read the saved plan" in done.stderr


def test_the_guard_passes_a_plan_that_lists_no_changes():
    assert guard('{"resource_changes": []}').returncode == 0


@pytest.mark.parametrize(
    "address", ["cloudflare_pages_project.site", "module.x.cloudflare_pages_project.site"]
)
def test_the_guard_never_lets_the_pages_project_be_deleted(address):
    """ADR-008 keeps the project: a deleted pages.dev name can be claimed by anyone. That must
    not rest on `prevent_destroy` alone, which an edit of the .tf file removes."""
    plan = json.dumps(
        {"resource_changes": [{"address": address, "change": {"actions": ["delete"]}}]}
    )
    done = guard(plan, "--allow-changes", "--allow-destroy")
    assert done.returncode == 1
    assert "ADR-008" in done.stderr and address in done.stderr
    both = json.dumps(
        {
            "resource_changes": [
                {"address": address, "change": {"actions": ["delete"]}},
                {
                    "address": "cloudflare_zero_trust_access_application.seller",
                    "change": {"actions": ["delete"]},
                },
            ]
        }
    )
    assert guard(both, "--allow-destroy").returncode == 1, "not even among other deletes"
    only_access = json.dumps(
        {
            "resource_changes": [
                {
                    "address": "cloudflare_zero_trust_access_application.seller",
                    "change": {"actions": ["delete"]},
                }
            ]
        }
    )
    assert guard(only_access, "--allow-destroy").returncode == 0


# --- BusyBox make (lesson-035) ----------------------------------------------------------------

# What a POSIX make (BusyBox's, on the Windows machine) cannot parse or expand. GNU make accepts
# all of them, so CI stays green while `make` on that machine dies with "expected separator".
GNU_ONLY = re.compile(
    r"^ *(define|endef|ifeq|ifneq|ifdef|ifndef|else|endif)\b"
    r"|\$\((call|eval|if|foreach|shell|MAKEFILE_LIST)\b"
    r"|^\.(ONESHELL|SECONDEXPANSION)\b"
)


def test_the_makefile_uses_only_what_a_posix_make_can_parse():
    """The recipe that runs Terraform is scripts/tf-run.sh, not a `define` block: BusyBox make
    rejects `define` at parse time, so every `make` target failed there, not just infra-*."""
    for number, line in enumerate((ROOT / "Makefile").read_text(encoding="utf-8").splitlines(), 1):
        if line.lstrip().startswith("#"):
            continue
        assert not GNU_ONLY.search(line), f"Makefile:{number} is GNU make only: {line}"


def run_tf_script(shell, toolbox, **env):
    return subprocess.run(
        [shell, "scripts/tf-run.sh", "plan", "-input=false"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "PATH": f"{toolbox[0]}{os.pathsep}{os.environ['PATH']}",
            **env,
        },
    )


@pytest.mark.skipif(not shutil.which("dash"), reason="needs dash, the strictest common sh")
@pytest.mark.parametrize("shell", ["dash", "bash"])
def test_the_terraform_script_is_posix_sh_and_hands_over_its_secrets_in_the_environment(
    shell, toolbox
):
    done = run_tf_script(
        shell,
        toolbox,
        TF_DIR="somewhere",
        TF_TOKEN_KEY="cloudflare_terraform_token",
        SOPS_FILE=SOPS_FILE,
        CF_ACCOUNT_ID="acct-id",
    )
    assert done.returncode == 0, done.stderr
    recorded = toolbox[1].read_text(encoding="utf-8")
    assert "argv: -chdir=somewhere plan -input=false" in recorded
    assert f"token_in_env: {TOKEN_VALUE}" in recorded
    assert f"email_in_env: {EMAIL_VALUE}" in recorded
    assert "account_in_env: acct-id" in recorded
    assert TOKEN_VALUE not in done.stdout + done.stderr


@pytest.mark.skipif(not shutil.which("dash"), reason="needs dash")
def test_the_terraform_script_refuses_to_run_without_what_make_passes_it(toolbox):
    done = run_tf_script("dash", toolbox, TF_DIR="x")
    assert done.returncode != 0
    assert "TF_TOKEN_KEY" in done.stderr
    assert not toolbox[1].exists(), "terraform must not have been started"
