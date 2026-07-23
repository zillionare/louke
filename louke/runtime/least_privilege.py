"""NFR-0200: Least privilege & secret protection.

Agent manifest/tool scopes must match role contracts; GitHub/registry
credentials only available in Runtime operation boundary; CI uses minimal
permissions.  Injecting test secrets into prompt/diff/commit/fixture/log/
evidence payload must be blocked by the gate and the report must be
redacted; Agents cannot read unauthorised credentials (AC-NFR0200-01).
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

ERROR_CODES = (
    "SCOPE_DENIED",
    "TOOL_DENIED",
    "CI_PERMISSION_EXCESS",
    "CREDENTIAL_ACCESS_DENIED",
    "SECRET_DETECTED",
)

_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)(password|secret|token)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{8,}['\"]?"),
)

_CI_FORBIDDEN_PERMISSIONS: frozenset[str] = frozenset(
    {
        "pull-requests: write",
        "checks: write",
        "id-token: write",
        "packages: write",
        "contents: write",
    }
)

_RUNTIME_PROVIDER_ROLES: frozenset[str] = frozenset(
    {
        "runtime:publish-adapter",
        "runtime:ci-adapter",
        "runtime:release-adapter",
        "runtime:program",
    }
)

_PROVIDER_CREDENTIAL_VARS: frozenset[str] = frozenset(
    {
        "GITHUB_TOKEN",
        "PYPI_API_TOKEN",
        "NPM_TOKEN",
        "DOCKER_PASSWORD",
        "AWS_ACCESS_KEY_ID",
    }
)


class LeastPrivilegeError(Exception):
    """A fail-closed least-privilege rejection carrying a stable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass(frozen=True)
class ToolScopeManifest:
    """An Agent's tool/scope manifest (AC-NFR0200-01).

    Attributes:
        role: Agent role (``devon|shield|archer|...``).
        allowed_tools: Tuple of allowed tool names.
        allowed_paths: Tuple of allowed path globs.
        forbidden_paths: Tuple of forbidden path globs.
    """

    role: str
    allowed_tools: tuple[str, ...]
    allowed_paths: tuple[str, ...]
    forbidden_paths: tuple[str, ...]


@dataclass(frozen=True)
class ToolAuthorization:
    """Result of :func:`authorize_agent_tool` (AC-NFR0200-01).

    Attributes:
        allowed: ``True`` if the tool+path is authorised.
        reason: Optional reason for denial.
    """

    allowed: bool
    reason: str = ""


def _path_in_globs(path: str, globs: tuple[str, ...]) -> bool:
    for g in globs:
        if path == g or path.startswith(g.rstrip("*")):
            return True
    return False


def authorize_agent_tool(
    manifest: ToolScopeManifest, *, tool: str, path: str
) -> ToolAuthorization:
    """Authorise an Agent's tool use on a path (AC-NFR0200-01).

    Args:
        manifest: :class:`ToolScopeManifest` for the Agent's role.
        tool: Tool name being requested.
        path: Path the tool would touch.

    Returns:
        A :class:`ToolAuthorization` with ``allowed=True`` if the tool is in
        ``allowed_tools`` AND path is in ``allowed_paths`` AND NOT in
        ``forbidden_paths``.

    Raises:
        LeastPrivilegeError: With ``TOOL_DENIED`` if the tool is not allowed;
            ``SCOPE_DENIED`` if the path is forbidden or outside allowed scope.
    """
    if tool not in manifest.allowed_tools:
        raise LeastPrivilegeError(
            "TOOL_DENIED",
            f"role {manifest.role!r} cannot use tool {tool!r}",
        )
    if _path_in_globs(path, manifest.forbidden_paths):
        raise LeastPrivilegeError(
            "SCOPE_DENIED",
            f"path {path!r} is in forbidden scopes",
        )
    if not _path_in_globs(path, manifest.allowed_paths):
        raise LeastPrivilegeError(
            "SCOPE_DENIED",
            f"path {path!r} is outside allowed scopes",
        )
    return ToolAuthorization(allowed=True)


def validate_ci_permissions(*, permissions: dict[str, str]) -> None:
    """Validate CI permissions are minimal (AC-NFR0200-01).

    Args:
        permissions: Mapping of permission scope -> level.

    Raises:
        LeastPrivilegeError: With ``CI_PERMISSION_EXCESS`` if any forbidden
            scope is present or if ``contents`` is not ``read``.
    """
    for scope, level in permissions.items():
        key = f"{scope}: {level}"
        if key in _CI_FORBIDDEN_PERMISSIONS:
            raise LeastPrivilegeError(
                "CI_PERMISSION_EXCESS",
                f"CI permission {key!r} exceeds minimal allowed",
            )
    if permissions.get("contents", "read") != "read":
        raise LeastPrivilegeError(
            "CI_PERMISSION_EXCESS",
            f"contents permission must be 'read', got {permissions.get('contents')!r}",
        )


def validate_credential_boundary(
    *, actor_role: str, requested_env_vars: tuple[str, ...]
) -> None:
    """Validate that the actor may access the requested credential env vars.

    Args:
        actor_role: Actor role identity.
        requested_env_vars: Tuple of env var names the actor wants to read.

    Raises:
        LeastPrivilegeError: With ``CREDENTIAL_ACCESS_DENIED`` if a non-Runtime
            actor attempts to access provider credential env vars.
    """
    if actor_role in _RUNTIME_PROVIDER_ROLES:
        return  # Runtime adapters may access provider credentials.
    for var in requested_env_vars:
        if var in _PROVIDER_CREDENTIAL_VARS:
            raise LeastPrivilegeError(
                "CREDENTIAL_ACCESS_DENIED",
                f"role {actor_role!r} cannot access credential env var {var!r}",
            )


@dataclass(frozen=True)
class SecretFinding:
    """A single secret scan finding (AC-NFR0200-01).

    Attributes:
        rule_id: Stable rule id (e.g. ``aws-access-key``).
        location_hash: ``sha256:<hex>`` of the matched location (no raw value).
        redacted_fingerprint: Redacted fingerprint for triage.
    """

    rule_id: str
    location_hash: str
    redacted_fingerprint: str


@dataclass(frozen=True)
class SecretScanReport:
    """Result of :func:`scan_for_secrets` (AC-NFR0200-01).

    Attributes:
        blocked: ``True`` if any secret was detected.
        findings: Tuple of :class:`SecretFinding`.
        redacted_report: Redacted payload (raw secret removed).
    """

    blocked: bool
    findings: tuple[SecretFinding, ...]
    redacted_report: str


def _redact(text: str, pattern: re.Pattern[str]) -> str:
    return pattern.sub("[REDACTED]", text)


def scan_for_secrets(payload: str) -> SecretScanReport:
    """Scan a payload for secrets and return a redacted report (AC-NFR0200-01).

    Args:
        payload: Raw payload string from prompt/diff/commit/fixture/log/evidence.

    Returns:
        A :class:`SecretScanReport` with ``blocked=True`` if any pattern
        matched.  The ``redacted_report`` replaces each match with
        ``[REDACTED]`` and never includes the raw secret value.
    """
    findings: list[SecretFinding] = []
    redacted = payload
    for pattern in _SECRET_PATTERNS:
        for match in pattern.finditer(payload):
            rule_id = f"secret-pattern:{pattern.pattern[:24]}"
            location_hash = (
                "sha256:"
                + hashlib.sha256(f"{match.start()}:{match.end()}".encode()).hexdigest()[
                    :16
                ]
            )
            fingerprint = "***REDACTED***"
            findings.append(
                SecretFinding(
                    rule_id=rule_id,
                    location_hash=location_hash,
                    redacted_fingerprint=fingerprint,
                )
            )
        redacted = _redact(redacted, pattern)
    return SecretScanReport(
        blocked=bool(findings),
        findings=tuple(findings),
        redacted_report=redacted,
    )
