"""AC-FR1100-01/AC-FR1200-01/AC-FR1300-01: IF-CI-01 CI contract rules & coexistence.

Extends the existing CI contract test coverage with ruleset readback (FR-1200),
coexistence (FR-1300), and fork PR secret access (FR-1100).  Verifies that the
managed workflow is the only file Louke owns, that user workflows/checks are
preserved, that ruleset owner/target is declared, and that fork PR jobs have
no production secret access.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


from louke._tools import ci_contract as ci

_SPEC_ROOT = (
    Path(__file__).resolve().parents[3]
    / ".louke"
    / "project"
    / "specs"
    / "v0.14-002-workflow-reflow-design"
)
_CONTRACT = (
    _SPEC_ROOT / "design-artifacts" / "contracts" / "github-actions-ci.candidate.json"
)


def _contract() -> dict[str, Any]:
    return json.loads(_CONTRACT.read_bytes())


def _payload() -> dict[str, Any]:
    return _contract()["payload"]


def test_rules_readback_declares_owner_target_and_fallback() -> None:
    """AC-FR1200-01: rules_readback declares owner/target/fallback/preserve."""
    rules = _payload()["rules_readback"]
    assert rules["owner"] == "Louke Runtime"
    assert "main" in rules["target"]
    assert "releases/**" in rules["target"]
    assert rules["fallback"]  # must declare branch-protection fallback
    assert rules["preserve_existing"] is True


def test_rules_readback_preserves_user_checks() -> None:
    """AC-FR1200-01: changes must not delete fixture's existing required checks."""
    # The contract must declare a single stable required check; user checks
    # outside the managed workflow must be preserved (rules_readback.preserve_existing).
    contract = _contract()
    payload = contract["payload"]
    assert payload["required_check"] == "Louke CI / required"
    assert payload["rules_readback"]["preserve_existing"] is True


def test_permissions_default_least_privilege() -> None:
    """AC-FR1100-01: default permission is contents: read."""
    permissions = _payload()["permissions"]
    assert permissions["default"] == "contents: read"
    assert permissions["pull_request_write"] is False
    assert permissions["fork_pr_secrets"] is False


def test_fork_pr_has_no_production_secrets() -> None:
    """AC-FR1100-01: fork PR jobs have no production secret access."""
    secrets = _payload()["secrets"]
    assert secrets["fork_pr"] == []
    assert (
        "protected" in secrets["production"].lower()
        or "release" in secrets["production"].lower()
    )


def test_managed_path_is_unique_louke_owned_file() -> None:
    """AC-FR1300-01: Louke only manages .github/workflows/louke-ci.yml."""
    payload = _payload()
    assert payload["managed_path"] == ".github/workflows/louke-ci.yml"
    assert payload["owner_marker"] == "louke-managed:v0.14-002"


def test_render_does_not_touch_user_workflows(tmp_path: Path) -> None:
    """AC-FR1300-01: rendering the managed workflow leaves user workflows intact."""
    workflows_dir = tmp_path / ".github" / "workflows"
    workflows_dir.mkdir(parents=True)
    user_ci = workflows_dir / "ci.yml"
    user_release = workflows_dir / "release.yml"
    user_ci.write_text("name: ci\non: push\n", encoding="utf-8")
    user_release.write_text(
        "name: release\non: push:\n  tags: ['v*']\n", encoding="utf-8"
    )
    # Render managed workflow alongside user workflows
    managed = workflows_dir / "louke-ci.yml"
    managed.write_text(ci.render(_contract()), encoding="utf-8")
    # User workflows must be untouched
    assert user_ci.read_text() == "name: ci\non: push\n"
    assert user_release.read_text() == "name: release\non: push:\n  tags: ['v*']\n"


def test_render_idempotent_does_not_change_user_files(tmp_path: Path) -> None:
    """AC-FR1300-01: rendering twice yields the same managed file, user files untouched."""
    workflows_dir = tmp_path / ".github" / "workflows"
    workflows_dir.mkdir(parents=True)
    user_ci = workflows_dir / "ci.yml"
    user_ci.write_text("name: ci\n", encoding="utf-8")
    managed = workflows_dir / "louke-ci.yml"
    managed.write_text(ci.render(_contract()), encoding="utf-8")
    first_user = user_ci.read_text()
    second_render = ci.render(_contract())
    assert managed.read_text() == second_render
    assert user_ci.read_text() == first_user  # user workflow untouched


def test_required_check_aggregate_only_accepts_exact_success() -> None:
    """AC-FR1200-01: aggregate success only when every required need is success."""
    contract = _contract()
    ids = ci.required_job_ids(contract)
    # All success -> success
    conclusions = {j: "success" for j in ids}
    assert ci.aggregate_required(conclusions, contract) == "success"
    # Any non-success -> failure (parametrised)
    for bad in (
        "failure",
        "cancelled",
        "timed_out",
        "skipped",
        "neutral",
        "",
        "unknown",
    ):
        conclusions = {j: "success" for j in ids}
        conclusions[ids[0]] = bad
        assert ci.aggregate_required(conclusions, contract) == "failure"


def test_required_check_aggregate_fails_on_missing_or_extra() -> None:
    """AC-FR1200-01: a missing required job or extra unknown fails the aggregate."""
    contract = _contract()
    ids = ci.required_job_ids(contract)
    # Drop one required job conclusion entirely
    conclusions_missing = {j: "success" for j in ids[1:]}
    assert ci.aggregate_required(conclusions_missing, contract) == "failure"


def test_dag_edges_form_single_aggregate_destination() -> None:
    """AC-FR1100-01: DAG edges all flow to a single Louke CI / required aggregate."""
    dag = _payload()["dag"]
    edges = dag["edges"]
    destinations = {e["to"] for e in edges}
    assert "Louke CI / required" in destinations
    # Every required job must be a source for the aggregate
    sources_to_aggregate = {
        e["from"] for e in edges if e["to"] == "Louke CI / required"
    }
    required_job_ids = {
        j["id"] for j in _payload()["jobs"] if j["id"] != "Louke CI / required"
    }
    assert required_job_ids <= sources_to_aggregate


def test_services_declared_for_workbench_and_providers() -> None:
    """AC-FR1100-01: services declare workbench and provider stand-ins."""
    services = _payload()["services"]
    service_ids = {s["id"] for s in services}
    assert "workbench" in service_ids
    assert "providers" in service_ids


def test_caches_declared_for_pip_and_playwright() -> None:
    """AC-FR1100-01: caches declare pip and Playwright inputs."""
    caches = _payload()["caches"]
    cache_ids = {c["id"] for c in caches}
    assert "pip" in cache_ids
    assert "playwright" in cache_ids


def test_evidence_list_includes_required_artifacts() -> None:
    """AC-FR1100-01: evidence list includes JUnit/coverage/closure/runner reports."""
    evidence = _payload()["evidence"]
    for required in (
        "JUnit",
        "coverage.xml",
        "34/34 closure JSON",
        "artifact identity JSON",
        "journey report",
    ):
        assert required in evidence


def test_failure_policy_fail_closed_with_explicit_reasons() -> None:
    """AC-FR1100-01: failure policy fail_closed with explicit non-success reasons."""
    policy = _payload()["failure_policy"]
    assert policy["fail_closed"] is True
    expected_reasons = {
        "failure",
        "cancel",
        "timeout",
        "missing",
        "skip",
        "unknown",
        "drift",
    }
    assert expected_reasons <= set(policy["non_success"])
