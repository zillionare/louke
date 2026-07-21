"""FR-0100: `lk serve` 启动诊断与产品入口.

AC references:
- AC-FR0100-01: a workspace missing model/provider/OpenCode shows
  per-item readiness (Louke/dependencies/configuration/model/provider/
  OpenCode/workspace identity); missing items are ``BLOCKED`` with non-empty
  remediation and the release entry is not submittable.
- AC-FR0100-02: with a valid setup manifest and all checks passing, two
  consecutive ``lk serve`` runs both reach the Workbench release entry; the
  workspace/repository/provider namespace/readiness identity stays the same;
  neither run modifies workspace-level configuration or creates release-level
  resources.
- AC-FR0100-03: when Python/runtime/package/port/app-factory failure makes
  the Web service process unable to start, ``lk serve`` exits non-zero with
  the hard-preflight failure item and a non-empty remediation in stderr; the
  Web listener is not reachable; WorkflowRun and external create call counts
  are zero; the same failure does not also appear in an accessible Web
  ``BLOCKED`` readiness diagnostic.
"""

from __future__ import annotations

import pytest

from louke.v014.fr0100_serve_diagnostics import (
    NON_LOOPBACK_AUTH_UNAVAILABLE,
    HardPreflightError,
    ReadinessCheck,
    ReadinessStatus,
    classify_serve_failure,
    decide_release_submit_enabled,
    evaluate_hard_preflight,
    evaluate_web_readiness,
)


# AC-FR0100-03 ---------------------------------------------------------------
def test_hard_preflight_python_failure_exits_nonzero_with_stderr_remediation() -> None:
    """AC-FR0100-03: a Python interpreter failure is a hard preflight
    failure; the process exits non-zero with the failure item and a
    non-empty remediation in stderr."""
    with pytest.raises(HardPreflightError) as exc_info:
        evaluate_hard_preflight(
            python_interpreter_ok=False,
            package_loadable=True,
            workspace_path_ok=True,
            port_available=True,
            app_factory_ok=True,
            host_is_loopback=True,
        )
    assert exc_info.value.exit_code != 0
    assert "python" in exc_info.value.failure_item.lower()
    assert exc_info.value.remediation  # non-empty
    assert exc_info.value.web_listener_reachable is False


def test_hard_preflight_non_loopback_host_rejected() -> None:
    """AC-FR0100-03 + IF-CLI-01: a non-loopback host is a hard preflight
    failure with code NON_LOOPBACK_AUTH_UNAVAILABLE; no listener, DB or
    external resource is created."""
    with pytest.raises(HardPreflightError) as exc_info:
        evaluate_hard_preflight(
            python_interpreter_ok=True,
            package_loadable=True,
            workspace_path_ok=True,
            port_available=True,
            app_factory_ok=True,
            host_is_loopback=False,
        )
    assert exc_info.value.code == NON_LOOPBACK_AUTH_UNAVAILABLE
    assert exc_info.value.web_listener_reachable is False


def test_hard_preflight_passes_when_all_preconditions_ok() -> None:
    """AC-FR0100-02 + AC-FR0100-03: when all hard-preflight preconditions
    pass, no HardPreflightError is raised and the Web listener is
    reachable."""
    result = evaluate_hard_preflight(
        python_interpreter_ok=True,
        package_loadable=True,
        workspace_path_ok=True,
        port_available=True,
        app_factory_ok=True,
        host_is_loopback=True,
    )
    assert result.web_listener_reachable is True
    assert result.exit_code == 0


# AC-FR0100-01 ---------------------------------------------------------------
def test_web_readiness_lists_per_item_status_and_remediation() -> None:
    """AC-FR0100-01: missing model/provider/OpenCode items are BLOCKED with
    non-empty remediation."""
    readiness = evaluate_web_readiness(
        louke_ok=True,
        dependencies_ok=True,
        configuration_ok=True,
        model_provider_ok=False,
        opencode_ok=False,
        workspace_identity_ok=True,
    )
    assert readiness.overall == ReadinessStatus.BLOCKED
    blocked = [c for c in readiness.checks if c.status == ReadinessStatus.BLOCKED]
    assert len(blocked) == 2
    for check in blocked:
        assert check.remediation  # non-empty
    assert "model" in {c.id for c in blocked}
    assert "opencode" in {c.id for c in blocked}


def test_release_submit_disabled_when_any_readiness_blocked() -> None:
    """AC-FR0100-01: when any readiness item is BLOCKED, the release submit
    is disabled."""
    decision = decide_release_submit_enabled(
        checks=(
            ReadinessCheck(id="louke", status=ReadinessStatus.READY, remediation=""),
            ReadinessCheck(
                id="model",
                status=ReadinessStatus.BLOCKED,
                remediation="configure model",
            ),
        ),
        setup_manifest_valid=True,
    )
    assert decision.release_submit_enabled is False
    assert "model" in decision.blocking_check_ids


def test_release_submit_enabled_when_all_ready_and_setup_valid() -> None:
    """AC-FR0100-01 + AC-FR0100-02: when all readiness items are READY and
    setup is valid, the release submit is enabled."""
    decision = decide_release_submit_enabled(
        checks=(
            ReadinessCheck(id="louke", status=ReadinessStatus.READY, remediation=""),
            ReadinessCheck(id="model", status=ReadinessStatus.READY, remediation=""),
        ),
        setup_manifest_valid=True,
    )
    assert decision.release_submit_enabled is True
    assert decision.blocking_check_ids == ()


# AC-FR0100-02 ---------------------------------------------------------------
def test_idempotent_startup_does_not_modify_workspace_or_create_release_resources() -> (
    None
):
    """AC-FR0100-02: two consecutive ``lk serve`` runs with a valid setup
    manifest produce the same readiness identity and zero workspace-config
    modifications or release-level resource creation calls."""
    first = evaluate_web_readiness(
        louke_ok=True,
        dependencies_ok=True,
        configuration_ok=True,
        model_provider_ok=True,
        opencode_ok=True,
        workspace_identity_ok=True,
        setup_manifest_identity="manifest_sha256:abc",
    )
    second = evaluate_web_readiness(
        louke_ok=True,
        dependencies_ok=True,
        configuration_ok=True,
        model_provider_ok=True,
        opencode_ok=True,
        workspace_identity_ok=True,
        setup_manifest_identity="manifest_sha256:abc",
    )
    assert first.overall == ReadinessStatus.READY
    assert second.overall == ReadinessStatus.READY
    assert first.setup_manifest_identity == second.setup_manifest_identity
    assert first.workspace_config_modification_count == 0
    assert second.workspace_config_modification_count == 0
    assert first.release_resource_creation_count == 0
    assert second.release_resource_creation_count == 0


# AC-FR0100-03 (failure classification) --------------------------------------
def test_classify_serve_failure_attributes_each_failure_to_exactly_one_category() -> (
    None
):
    """AC-FR0100-03: each failure is attributed to exactly one category
    (hard preflight OR Web readiness); the same failure does not appear in
    both."""
    hard = classify_serve_failure(
        python_interpreter_ok=False,
        package_loadable=True,
        port_available=True,
        app_factory_ok=True,
        web_readiness_blocked=False,
    )
    assert hard.category == "hard_preflight"
    assert hard.also_in_web_readiness is False

    web = classify_serve_failure(
        python_interpreter_ok=True,
        package_loadable=True,
        port_available=True,
        app_factory_ok=True,
        web_readiness_blocked=True,
    )
    assert web.category == "web_readiness"
    assert web.also_in_hard_preflight is False
