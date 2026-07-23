"""Integration tests for NFR-0200: Least privilege & secret protection.

AC-NFR0200-01: Agent manifest/tool scopes must match role contracts;
GitHub/registry credentials only available at the Runtime operation
boundary; CI uses minimal permissions. Injecting test secrets into
prompt/diff/commit/fixture/log/evidence payload must be blocked by the
gate and reported in redacted form; Agents cannot read unauthorised
credentials.

Interfaces covered (per interfaces.md):
- IF-PROMPT-02 (role capability, ARC-01)
- IF-TASK-01 (tool scopes, ARC-03/ARC-04)
- IF-CI-02 (CI permissions, ARC-11)
- IF-SEC-01 (secret scan, ARC-13)
"""
# AC-NFR0200-01

from __future__ import annotations

import pytest

from louke.runtime.least_privilege import (
    ERROR_CODES,
    LeastPrivilegeError,
    SecretScanReport,
    ToolAuthorization,
    ToolScopeManifest,
    authorize_agent_tool,
    scan_for_secrets,
    validate_ci_permissions,
    validate_credential_boundary,
)


def _valid_manifest() -> ToolScopeManifest:
    return ToolScopeManifest(
        role="devon",
        allowed_tools=("edit-file", "run-tests"),
        allowed_paths=("louke/v014/",),
        forbidden_paths=("tests/", ".github/"),
    )


# ---------------------------------------------------------------------------
# authorize_agent_tool
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_authorize_agent_tool_allows_in_scope_path():
    """AC-NFR0200-01: tool+path within manifest -> authorized."""
    manifest = _valid_manifest()
    result = authorize_agent_tool(
        manifest,
        tool="edit-file",
        path="louke/v014/fr0100.py",
    )
    assert isinstance(result, ToolAuthorization)
    assert result.allowed is True


@pytest.mark.real_module
def test_authorize_agent_tool_rejects_forbidden_path():
    """AC-NFR0200-01: forbidden path -> SCOPE_DENIED."""
    manifest = _valid_manifest()
    with pytest.raises(LeastPrivilegeError) as exc:
        authorize_agent_tool(
            manifest,
            tool="edit-file",
            path="tests/integration/x.py",
        )
    assert exc.value.code == "SCOPE_DENIED"


@pytest.mark.real_module
def test_authorize_agent_tool_rejects_unauthorized_tool():
    """AC-NFR0200-01: tool not in allowed_tools -> TOOL_DENIED."""
    manifest = _valid_manifest()
    with pytest.raises(LeastPrivilegeError) as exc:
        authorize_agent_tool(
            manifest,
            tool="commit",  # not in allowed_tools
            path="louke/v014/fr0100.py",
        )
    assert exc.value.code == "TOOL_DENIED"


# ---------------------------------------------------------------------------
# validate_ci_permissions
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_validate_ci_permissions_accepts_minimal_read_only():
    """AC-NFR0200-01: contents:read is minimal; allowed."""
    validate_ci_permissions(permissions={"contents": "read"})  # no raise


@pytest.mark.real_module
def test_validate_ci_permissions_rejects_write_contents():
    """AC-NFR0200-01: contents:write is forbidden in CI."""
    with pytest.raises(LeastPrivilegeError) as exc:
        validate_ci_permissions(permissions={"contents": "write"})
    assert exc.value.code == "CI_PERMISSION_EXCESS"


@pytest.mark.real_module
def test_validate_ci_permissions_rejects_packages_write():
    """AC-NFR0200-01: packages:write is forbidden in default CI."""
    with pytest.raises(LeastPrivilegeError) as exc:
        validate_ci_permissions(permissions={"packages": "write"})
    assert exc.value.code == "CI_PERMISSION_EXCESS"


# ---------------------------------------------------------------------------
# validate_credential_boundary
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_validate_credential_boundary_allows_runtime_role():
    """AC-NFR0200-01: runtime:* roles can access provider credentials."""
    validate_credential_boundary(
        actor_role="runtime:publish-adapter",
        requested_env_vars=("GITHUB_TOKEN", "PYPI_API_TOKEN"),
    )  # no raise


@pytest.mark.real_module
def test_validate_credential_boundary_rejects_agent_accessing_credentials():
    """AC-NFR0200-01: devon cannot read GITHUB_TOKEN."""
    with pytest.raises(LeastPrivilegeError) as exc:
        validate_credential_boundary(
            actor_role="devon",
            requested_env_vars=("GITHUB_TOKEN",),
        )
    assert exc.value.code == "CREDENTIAL_ACCESS_DENIED"


@pytest.mark.real_module
def test_validate_credential_boundary_rejects_shield_accessing_pypi_token():
    """AC-NFR0200-01: shield cannot read PYPI_API_TOKEN."""
    with pytest.raises(LeastPrivilegeError) as exc:
        validate_credential_boundary(
            actor_role="shield",
            requested_env_vars=("PYPI_API_TOKEN",),
        )
    assert exc.value.code == "CREDENTIAL_ACCESS_DENIED"


# ---------------------------------------------------------------------------
# scan_for_secrets
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_scan_for_secrets_detects_aws_access_key():
    """AC-NFR0200-01: AWS access key pattern -> SECRET_DETECTED."""
    payload = "config with AKIAIOSFODNN7EXAMPLE token"
    report = scan_for_secrets(payload)
    assert isinstance(report, SecretScanReport)
    assert report.blocked is True
    assert len(report.findings) >= 1
    # Original secret must NOT appear in redacted report.
    assert "AKIAIOSFODNN7EXAMPLE" not in report.redacted_report


@pytest.mark.real_module
def test_scan_for_secrets_detects_private_key():
    """AC-NFR0200-01: private key block -> SECRET_DETECTED."""
    payload = "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA..."
    report = scan_for_secrets(payload)
    assert report.blocked is True
    assert "PRIVATE KEY" not in report.redacted_report


@pytest.mark.real_module
def test_scan_for_secrets_detects_password_assignment():
    """AC-NFR0200-01: password=... -> SECRET_DETECTED."""
    payload = 'password = "supersecretpassword123"'
    report = scan_for_secrets(payload)
    assert report.blocked is True
    assert "supersecretpassword123" not in report.redacted_report


@pytest.mark.real_module
def test_scan_for_secrets_passes_on_clean_payload():
    """AC-NFR0200-01: clean payload -> no secrets detected."""
    payload = "this is a normal config without secrets"
    report = scan_for_secrets(payload)
    assert report.blocked is False
    assert report.findings == ()


@pytest.mark.real_module
def test_error_codes_set_covers_all_documented_codes():
    """AC-NFR0200-01: ERROR_CODES includes all codes from interfaces.md."""
    expected = {
        "SCOPE_DENIED",
        "TOOL_DENIED",
        "CI_PERMISSION_EXCESS",
        "CREDENTIAL_ACCESS_DENIED",
        "SECRET_DETECTED",
    }
    actual = set(ERROR_CODES)
    missing = expected - actual
    assert not missing, f"ERROR_CODES missing: {missing}"
