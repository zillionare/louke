"""AC-NFR0200-01: Least privilege & secret protection.

Agent manifest/tool scopes must match role contracts; GitHub/registry
credentials only available in Runtime operation boundary; CI uses minimal
permissions.  Injecting test secrets into prompt/diff/commit/fixture/log/
evidence payload must be blocked by the gate and the report must be
redacted; Agents cannot read unauthorised credentials.
"""

from __future__ import annotations


import pytest

from louke.v014.nfr0200_least_privilege import (
    LeastPrivilegeError,
    SecretScanReport,
    ToolScopeManifest,
    authorize_agent_tool,
    scan_for_secrets,
    validate_ci_permissions,
    validate_credential_boundary,
)

_SECRET_PATTERNS = (
    "AKIA" + "A" * 16,
    "-----BEGIN RSA PRIVATE KEY-----",
    "password: supersecretvalue123",
    "token: sk-1234567890abcdef",
)


def test_authorize_agent_tool_grants_in_scope() -> None:
    """AC-NFR0200-01: Agent may use a tool within its declared scope."""
    manifest = ToolScopeManifest(
        role="devon",
        allowed_tools=("edit", "test"),
        allowed_paths=("louke/v014/x.py",),
        forbidden_paths=("louke/_tools/secret.py",),
    )
    decision = authorize_agent_tool(manifest, tool="edit", path="louke/v014/x.py")
    assert decision.allowed is True


def test_authorize_agent_tool_rejects_out_of_scope_path() -> None:
    """AC-NFR0200-01: Agent may not access paths outside declared scope."""
    manifest = ToolScopeManifest(
        role="devon",
        allowed_tools=("edit",),
        allowed_paths=("louke/v014/x.py",),
        forbidden_paths=("louke/_tools/secret.py",),
    )
    with pytest.raises(LeastPrivilegeError) as exc:
        authorize_agent_tool(manifest, tool="edit", path="louke/_tools/secret.py")
    assert exc.value.code == "SCOPE_DENIED"


def test_authorize_agent_tool_rejects_unauthorized_tool() -> None:
    """AC-NFR0200-01: Agent may not use tools not in its manifest."""
    manifest = ToolScopeManifest(
        role="devon",
        allowed_tools=("edit",),
        allowed_paths=("louke/v014/x.py",),
        forbidden_paths=(),
    )
    with pytest.raises(LeastPrivilegeError) as exc:
        authorize_agent_tool(manifest, tool="git-push", path="louke/v014/x.py")
    assert exc.value.code == "TOOL_DENIED"


def test_validate_ci_permissions_requires_minimal() -> None:
    """AC-NFR0200-01: CI uses minimal permissions; no forbidden scopes."""
    validate_ci_permissions(permissions={"contents": "read"})  # does not raise
    with pytest.raises(LeastPrivilegeError) as exc:
        validate_ci_permissions(
            permissions={
                "contents": "write",
                "pull-requests": "write",
            }
        )
    assert exc.value.code == "CI_PERMISSION_EXCESS"


def test_validate_ci_permissions_rejects_id_token_write() -> None:
    """AC-NFR0200-01: id-token:write and packages:write are forbidden."""
    with pytest.raises(LeastPrivilegeError) as exc:
        validate_ci_permissions(
            permissions={
                "contents": "read",
                "id-token": "write",
            }
        )
    assert exc.value.code == "CI_PERMISSION_EXCESS"


def test_validate_credential_boundary_blocks_agent_access_to_credentials() -> None:
    """AC-NFR0200-01: Agents cannot read unauthorised credentials."""
    with pytest.raises(LeastPrivilegeError) as exc:
        validate_credential_boundary(
            actor_role="devon",
            requested_env_vars=("GITHUB_TOKEN", "PYPI_API_TOKEN"),
        )
    assert exc.value.code == "CREDENTIAL_ACCESS_DENIED"


def test_validate_credential_boundary_allows_runtime_provider_access() -> None:
    """AC-NFR0200-01: Runtime adapter may access provider credentials."""
    validate_credential_boundary(
        actor_role="runtime:publish-adapter",
        requested_env_vars=("PYPI_API_TOKEN",),
    )  # does not raise


@pytest.mark.parametrize("payload", _SECRET_PATTERNS)
def test_scan_for_secrets_blocks_injected_secrets(payload: str) -> None:
    """AC-NFR0200-01: secret scan blocks secrets in prompt/diff/commit/fixture/log/evidence."""
    report = scan_for_secrets(payload)
    assert isinstance(report, SecretScanReport)
    assert report.blocked is True
    assert report.redacted_report != payload  # must be redacted
    assert report.findings  # at least one finding recorded


def test_scan_for_secrets_passes_clean_payload() -> None:
    """AC-NFR0200-01: clean payload passes the gate."""
    report = scan_for_secrets("def add(a, b): return a + b")
    assert report.blocked is False
    assert len(report.findings) == 0
